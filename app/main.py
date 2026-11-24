import os, json, subprocess, textwrap, uuid
from pathlib import Path
from typing import Optional
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / os.getenv("OUTPUT_DIR", "outputs")
OUT.mkdir(exist_ok=True)
app = FastAPI(title="Awais Labs AI YouTube Studio", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ScriptRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    duration_minutes: int = Field(default=5, ge=1, le=30)
    language: str = "English"
    style: str = "engaging documentary"

class RenderRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    script: str = Field(min_length=30, max_length=30000)

@app.get("/api/health")
def health():
    return {"status":"ok","product":"Awais Labs AI YouTube Studio","version":"0.1.0"}

@app.get("/api/config")
def config():
    return {"ollama_model":os.getenv("OLLAMA_MODEL","llama3.2"),"ollama_url":os.getenv("OLLAMA_URL","http://localhost:11434"),"youtube_upload":"OAuth credentials required"}

@app.post("/api/script")
def generate_script(req: ScriptRequest):
    prompt = f"""Write a {req.duration_minutes}-minute YouTube video script in {req.language}.
Topic: {req.topic}
Style: {req.style}
Include: compelling 15-second hook, clear sections, narration-ready paragraphs,
visual/B-roll suggestions in [VISUAL: ...] lines, and a concise call to action.
Return plain text with a strong title."""
    try:
        r = requests.post(os.getenv("OLLAMA_URL","http://localhost:11434") + "/api/generate",
            json={"model":os.getenv("OLLAMA_MODEL","llama3.2"),"prompt":prompt,"stream":False},timeout=240)
        r.raise_for_status()
        return {"script":r.json().get("response","").strip(),"model":os.getenv("OLLAMA_MODEL","llama3.2")}
    except requests.RequestException as e:
        raise HTTPException(503, f"Could not reach Ollama. Install/start Ollama and pull the configured model. Details: {e}")

@app.post("/api/render")
def render_video(req: RenderRequest):
    if not shutil_which("ffmpeg"):
        raise HTTPException(503,"FFmpeg is required to render videos.")
    job = uuid.uuid4().hex[:10]
    work = OUT / job
    work.mkdir()
    # Build a clean title-card video from script paragraphs; this is a basic renderer, not generated footage.
    paragraphs = [p.strip() for p in req.script.splitlines() if p.strip() and not p.strip().startswith("[VISUAL:")]
    if not paragraphs: paragraphs = [req.script]
    scenes = paragraphs[:30]
    concat = work / "scenes.txt"
    lines=[]
    for i, paragraph in enumerate(scenes):
        img = work / f"scene_{i:03}.png"
        safe = paragraph.replace("\\"," ").replace("'","’").replace(":"," - ")
        text = textwrap.fill(safe, width=48)
        subprocess.run(["ffmpeg","-y","-f","lavfi","-i","color=c=0x101827:s=1920x1080:d=5",
          "-vf",f"drawtext=text='{text[:600]}':fontcolor=white:fontsize=46:line_spacing=18:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=0x202e45@0.7:boxborderw=40",
          "-frames:v","1",str(img)],check=True,capture_output=True)
        lines.append(f"file '{img.as_posix()}'\nduration 5")
    lines.append(f"file '{(work / f'scene_{len(scenes)-1:03}.png').as_posix()}'")
    concat.write_text("\n".join(lines))
    target = work / "video.mp4"
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-vf","format=yuv420p","-r","30","-c:v","libx264","-pix_fmt","yuv420p",str(target)],check=True,capture_output=True)
    return {"job_id":job,"video":f"/outputs/{job}/video.mp4","note":"Basic text-scene render. Add licensed footage and narration for a production-ready video."}

def shutil_which(name):
    from shutil import which
    return which(name)

@app.get("/api/jobs")
def jobs():
    return [{"id":p.name,"video":f"/outputs/{p.name}/video.mp4"} for p in OUT.iterdir() if p.is_dir() and (p/"video.mp4").exists()]

app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")
app.mount("/", StaticFiles(directory=str(ROOT/"web"),html=True), name="web")
