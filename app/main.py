import os,json,uuid,sqlite3,requests
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,HTTPException,BackgroundTasks,UploadFile,File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from app.media import render,extract
from app.publishing import upload
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/os.getenv("OUTPUT_DIR","outputs");OUT.mkdir(exist_ok=True)
DB=ROOT/os.getenv("DATABASE_PATH","studio.sqlite3");OLLAMA=os.getenv("OLLAMA_URL","http://ollama:11434").rstrip("/");MODEL=os.getenv("OLLAMA_MODEL","llama3.2")
app=FastAPI(title="Awais Labs AI YouTube Studio",version="0.3.0")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("CORS_ORIGINS","*").split(","),allow_methods=["*"],allow_headers=["*"])
class Script(BaseModel):
 topic:str=Field(min_length=3,max_length=300);duration_minutes:int=Field(default=5,ge=1,le=30);language:str="English";style:str="cinematic documentary"
class Shorts(BaseModel):
 topic:str=Field(min_length=3,max_length=300);count:int=Field(default=3,ge=1,le=5);language:str="English"
class Render(BaseModel):
 title:str=Field(min_length=2,max_length=120);script:str=Field(min_length=30,max_length=30000);format:Literal["landscape","shorts"]="landscape"
class Produce(BaseModel):
 topic:str=Field(min_length=3,max_length=300);format:Literal["landscape","shorts"]="shorts";language:str="English";duration_minutes:int=Field(default=1,ge=1,le=20);auto_publish:bool=False
class Publish(BaseModel):
 title:str=Field(min_length=2,max_length=100);description:str="";tags:list[str]=[];privacy:Literal["private","unlisted","public"]="private"
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;c.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,kind TEXT,status TEXT,topic TEXT,title TEXT,script TEXT,format TEXT,video TEXT,checks TEXT,error TEXT,published_url TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP)");c.commit();return c
def update(j,**kw):
 c=conn()
 for k,v in kw.items():c.execute(f"UPDATE jobs SET {k}=? WHERE id=?",(json.dumps(v) if k=="checks" else v,j))
 c.commit();c.close()
def get(j):
 c=conn();r=c.execute("SELECT * FROM jobs WHERE id=?",(j,)).fetchone();c.close()
 if not r:raise HTTPException(404,"Job not found")
 d=dict(r)
 if d["checks"]:d["checks"]=json.loads(d["checks"])
 return d
def ai(prompt):
 try:
  r=requests.post(OLLAMA+"/api/generate",json={"model":MODEL,"prompt":prompt,"stream":False},timeout=300);r.raise_for_status();return r.json()["response"].strip()
 except Exception as e:raise HTTPException(503,f"Local Ollama unavailable: {e}")
def make_script(topic,minutes,lang):
 return ai(f"Write a {minutes}-minute narration-ready YouTube script in {lang} about {topic}. Add a powerful hook, story arc, spoken paragraphs, [VISUAL: ...] directions and CTA.")
def worker(j,topic,fmt,lang,mins,auto):
 try:
  update(j,status="generating");script=make_script(topic,mins,lang);title=next((x.lstrip("# ").strip() for x in script.splitlines() if x.strip()),topic)[:100]
  update(j,status="rendering",title=title,script=script)
  video,checks=render(script,title,OUT/j,fmt);update(j,status="quality_passed" if checks["passed"] else "quality_failed",video=f"/outputs/{j}/video.mp4",checks=checks)
  if auto and checks["passed"] and os.getenv("AUTO_PUBLISH","false").lower()=="true":
   result=upload(video,title,script[:4000],privacy=os.getenv("YOUTUBE_DEFAULT_PRIVACY","private"));update(j,status="published",published_url=result["url"])
 except Exception as e:update(j,status="failed",error=str(e))
@app.on_event("startup")
def start():conn().close()
@app.get("/api/health")
def health():return {"status":"ok","version":"0.3.0","product":"Awais Labs AI YouTube Studio"}
@app.get("/api/config")
def config():return {"model":MODEL,"daily_shorts_target":3,"formats":["landscape","shorts"],"youtube_upload_enabled":os.getenv("ENABLE_YOUTUBE_UPLOAD","false").lower()=="true","auto_publish_enabled":os.getenv("AUTO_PUBLISH","false").lower()=="true"}
@app.get("/api/providers")
def providers():return {"ollama":True,"ffmpeg":bool(__import__("shutil").which("ffmpeg")),"pexels":bool(os.getenv("PEXELS_API_KEY")),"tts":"edge-tts optional","comfyui":{"configured":bool(os.getenv("COMFYUI_URL")),"note":"Workflow-specific adapter not included yet"},"youtube_oauth":os.path.exists(os.getenv("YOUTUBE_TOKEN_FILE","/app/secrets/youtube-token.json"))}
@app.post("/api/script")
def script(r:Script):return {"script":make_script(r.topic,r.duration_minutes,r.language),"model":MODEL}
@app.post("/api/shorts")
def shorts(r:Shorts):
 raw=ai(f'Create {r.count} different 25-45 second YouTube Shorts scripts in {r.language} about {r.topic}. Each needs hook and [VISUAL] cue. Return only JSON: {{"shorts":[{{"title":"...","script":"..."}}]}}')
 try:return {"shorts":json.loads(raw)["shorts"][:r.count]}
 except Exception:raise HTTPException(502,"AI did not return valid Shorts JSON; retry.")
@app.post("/api/produce")
def produce(r:Produce,bg:BackgroundTasks):
 j=uuid.uuid4().hex[:12];c=conn();c.execute("INSERT INTO jobs(id,kind,status,topic,format) VALUES(?,?,?,?,?)",(j,"automated","queued",r.topic,r.format));c.commit();c.close()
 bg.add_task(worker,j,r.topic,r.format,r.language,r.duration_minutes,r.auto_publish)
 return {"job_id":j,"status":"queued"}
@app.post("/api/render")
def render_route(r:Render):
 j=uuid.uuid4().hex[:12]
 try:
  p,checks=render(r.script,r.title,OUT/j,r.format);c=conn();c.execute("INSERT INTO jobs(id,kind,status,topic,title,script,format,video,checks) VALUES(?,?,?,?,?,?,?,?,?)",(j,"manual","quality_passed" if checks["passed"] else "quality_failed",r.title,r.title,r.script,r.format,f"/outputs/{j}/video.mp4",json.dumps(checks)));c.commit();c.close()
  return {"job_id":j,"video":f"/outputs/{j}/video.mp4","checks":checks}
 except Exception as e:raise HTTPException(500,str(e))
@app.get("/api/jobs")
def jobs():
 c=conn();rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100").fetchall();c.close();out=[]
 for x in rows:
  d=dict(x)
  if d["checks"]:d["checks"]=json.loads(d["checks"])
  out.append(d)
 return out
@app.get("/api/jobs/{j}")
def job(j):return get(j)
@app.post("/api/clips")
async def clips(file:UploadFile=File(...),max_clips:int=8):
 ext=Path(file.filename or "").suffix.lower()
 if ext not in {".mp4",".mov",".mkv",".webm"}:raise HTTPException(400,"Upload MP4, MOV, MKV or WebM.")
 j=uuid.uuid4().hex[:10];work=OUT/j;work.mkdir();src=work/("source"+ext);size=0
 with src.open("wb") as f:
  while chunk:=await file.read(1024*1024):
   size+=len(chunk)
   if size>2_000_000_000:raise HTTPException(413,"Maximum upload size is 2 GB.")
   f.write(chunk)
 try:return {"job_id":j,"warning":"Scene-change heuristic only; these are candidate moments, not guaranteed viral clips.","clips":extract(src,work/"clips",min(12,max(1,max_clips)))}
 except Exception as e:raise HTTPException(500,str(e))
@app.post("/api/publish/{j}")
def publish(j:str,r:Publish):
 d=get(j)
 if d["status"] not in {"quality_passed","published"} or not d["video"]:raise HTTPException(409,"Only quality-passed jobs can be uploaded.")
 try:
  result=upload(ROOT/d["video"].lstrip("/"),r.title,r.description,r.tags,r.privacy);update(j,status="published",published_url=result["url"]);return result
 except Exception as e:raise HTTPException(503,str(e))
app.mount("/outputs",StaticFiles(directory=str(OUT)),name="outputs")
app.mount("/",StaticFiles(directory=str(ROOT/"web"),html=True),name="web")
