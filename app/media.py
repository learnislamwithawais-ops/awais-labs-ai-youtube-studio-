import asyncio, os, re, subprocess, textwrap, json
from pathlib import Path
import requests
def run(args): return subprocess.run(args,check=True,capture_output=True,text=True)
def duration(path):
 r=run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(path)])
 return max(1,float(r.stdout.strip()))
def voice(text,path):
 try:
  import edge_tts
  asyncio.run(edge_tts.Communicate(text,os.getenv("TTS_VOICE","en-US-GuyNeural")).save(str(path)))
  return Path(path).stat().st_size>1000
 except Exception: return False
def stock(query,path):
 key=os.getenv("PEXELS_API_KEY")
 if not key:return False
 try:
  r=requests.get("https://api.pexels.com/videos/search",headers={"Authorization":key},params={"query":query,"per_page":3},timeout=20);r.raise_for_status()
  vids=r.json().get("videos",[])
  if not vids:return False
  files=sorted(vids[0].get("video_files",[]),key=lambda f:f.get("width",0)*f.get("height",0),reverse=True)
  url=next((f["link"] for f in files if f.get("file_type")=="video/mp4"),None)
  if not url:return False
  with requests.get(url,stream=True,timeout=60) as x:
   x.raise_for_status()
   with open(path,"wb") as out:
    for chunk in x.iter_content(1024*1024):
     if chunk:out.write(chunk)
  return Path(path).stat().st_size>10000
 except Exception:return False
def srt(text,seconds,path):
 words=text.split(); chunks=[" ".join(words[i:i+9]) for i in range(0,len(words),9)] or [" "]
 def ts(v):
  ms=int(v*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
  return f"{h:02}:{m:02}:{s:02},{ms:03}"
 step=seconds/len(chunks); rows=[]
 for i,c in enumerate(chunks):rows += [str(i+1),f"{ts(i*step)} --> {ts(min(seconds,(i+1)*step))}",c,""]
 Path(path).write_text("\n".join(rows),encoding="utf-8")
def render(script,title,work,fmt):
 work=Path(work);work.mkdir(parents=True,exist_ok=True)
 vertical=fmt=="shorts";w,h=(1080,1920) if vertical else (1920,1080)
 scenes=[x.strip() for x in script.splitlines() if x.strip() and not x.strip().startswith("[VISUAL:")][:20] or [script]
 narration=" ".join(scenes); audio=work/"voice.mp3"; has_audio=voice(narration,audio)
 secs=max(20,len(narration.split())/2.2)
 if has_audio:
  try:secs=max(secs,duration(audio))
  except Exception:pass
 each=secs/len(scenes); concat=work/"scenes.txt";entries=[]
 visual=re.search(r"\[VISUAL:\s*(.*?)\]",script,re.I);query=visual.group(1) if visual else title
 for i,line in enumerate(scenes):
  txt=work/f"text{i}.txt";txt.write_text(textwrap.fill(line,width=24 if vertical else 46)[:500],encoding="utf-8")
  clip=work/f"scene{i}.mp4";bg=work/f"stock{i}.mp4";has_stock=stock(query,bg)
  if has_stock:
   inp=["-stream_loop","-1","-i",str(bg)]
   vf=f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},drawbox=x=0:y=ih*0.62:w=iw:h=ih*0.38:color=black@0.45:t=fill,drawtext=textfile='{txt}':fontcolor=white:fontsize={52 if vertical else 44}:x=(w-text_w)/2:y=h*0.7"
  else:
   inp=["-f","lavfi","-i",f"color=c=0x101827:s={w}x{h}:d={each:.2f}"]
   vf=f"drawtext=textfile='{txt}':fontcolor=white:fontsize={52 if vertical else 44}:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x202e45@0.7:boxborderw=40"
  run(["ffmpeg","-y",*inp,"-t",str(each),"-vf",vf,"-an","-r","30","-c:v","libx264","-pix_fmt","yuv420p",str(clip)])
  entries.append(f"file '{clip.as_posix()}'")
 concat.write_text("\n".join(entries)); silent=work/"silent.mp4";out=work/"video.mp4"
 run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
 captions=work/"captions.srt";srt(narration,secs,captions)
 vf=f"subtitles={captions}:force_style='FontSize={22 if vertical else 18},Outline=2,Alignment=2'"
 if has_audio:run(["ffmpeg","-y","-i",str(silent),"-i",str(audio),"-vf",vf,"-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast","-c:a","aac","-shortest","-movflags","+faststart",str(out)])
 else:run(["ffmpeg","-y","-i",str(silent),"-vf",vf,"-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p","-movflags","+faststart",str(out)])
 meta=json.loads(run(["ffprobe","-v","error","-show_entries","stream=codec_type,width,height","-show_entries","format=duration,size","-of","json",str(out)]).stdout)
 vs=next((x for x in meta["streams"] if x.get("codec_type")=="video"),{})
 checks={"passed":out.exists() and int(meta["format"]["size"])>50000 and vs.get("width")==w and vs.get("height")==h,"resolution":f"{vs.get('width')}x{vs.get('height')}","duration_seconds":round(float(meta["format"]["duration"]),1),"has_audio":any(x.get("codec_type")=="audio" for x in meta["streams"]),"voice_generated":has_audio,"stock_footage_used":has_stock}
 return out,checks
def extract(source,outdir,limit=8):
 outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);length=duration(source)
 d=run(["ffmpeg","-hide_banner","-i",str(source),"-vf","select='gt(scene,0.32)',showinfo","-an","-f","null","-"])
 times=[float(x) for x in re.findall(r"pts_time:([0-9.]+)",d.stderr)]
 starts=[]
 for t in times:
  s=max(0,min(length-35,t-12))
  if all(abs(s,x)>24 for x in starts):starts.append(s)
  if len(starts)>=limit:break
 if not starts:starts=[max(0,(length-35)/2)]
 result=[]
 for i,s in enumerate(starts):
  p=outdir/f"candidate_{i+1}.mp4"
  run(["ffmpeg","-y","-ss",str(s),"-i",str(source),"-t",str(min(35,length-s)),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920","-c:v","libx264","-preset","veryfast","-c:a","aac",str(p)])
  result.append({"file":p.name,"start_seconds":round(s,1),"video":f"/outputs/{outdir.name}/{p.name}"})
 return result
