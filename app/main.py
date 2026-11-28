import json, os, subprocess, textwrap, uuid
from pathlib import Path
from shutil import which
from typing import Literal
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / os.getenv("OUTPUT_DIR", "outputs")
OUT.mkdir(parents=True, exist_ok=True)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

app = FastAPI(title="Awais Labs AI YouTube Studio", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ScriptRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    duration_minutes: int = Field(default=5, ge=1, le=30)
    language: str = "English"
    style: str = "engaging documentary"

class ShortsRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    count: int = Field(default=3, ge=1, le=5)
    language: str = "English"
    style: str = "high-retention cinematic"

class RenderRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    script: str = Field(min_length=30, max_length=30000)
    format: Literal["landscape", "shorts"] = "landscape"

def ollama_generate(prompt: str, timeout: int = 300) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        if not result:
            raise HTTPException(502, "The local AI model returned an empty response.")
        return result
    except requests.RequestException as exc:
        raise HTTPException(503, f"Could not reach Ollama. Start Ollama and pull {OLLAMA_MODEL}. Details: {exc}")

@app.get("/api/health")
def health():
    return {"status": "ok", "product": "Awais Labs AI YouTube Studio", "version": "0.2.0"}

@app.get("/api/config")
def config():
    return {
        "ollama_model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
        "formats": ["landscape", "shorts"],
        "daily_shorts_target": 3,
        "youtube_upload": "Not enabled: Google OAuth setup and approval required",
    }

@app.post("/api/script")
def generate_script(req: ScriptRequest):
    prompt = f"""Write a {req.duration_minutes}-minute YouTube video script in {req.language}.
Topic: {req.topic}
Style: {req.style}
Include a compelling 15-second hook, clear sections, narration-ready paragraphs,
visual/B-roll suggestions in [VISUAL: ...] lines, and a concise call to action.
Return plain text with a strong title."""
    return {"script": ollama_generate(prompt), "model": OLLAMA_MODEL}

@app.post("/api/shorts")
def generate_shorts(req: ShortsRequest):
    prompt = f"""Create exactly {req.count} distinct YouTube Shorts scripts in {req.language}.
Topic: {req.topic}. Style: {req.style}.
Each must be 25-45 seconds, open with a strong 1-2 second hook, use short spoken sentences,
include visual directions in [VISUAL: ...] lines, and end with a natural engagement prompt.
Avoid repeating angles. Return ONLY valid JSON in this exact shape:
{{"shorts":[{{"title":"...","hook":"...","script":"..."}}]}}"""
    raw = ollama_generate(prompt)
    try:
        data = json.loads(raw)
        shorts = data.get("shorts", [])
        if not isinstance(shorts, list) or not shorts:
            raise ValueError("Missing shorts array")
        return {"shorts": shorts[:req.count], "model": OLLAMA_MODEL}
    except (ValueError, TypeError, json.JSONDecodeError):
        raise HTTPException(502, "The AI response was not valid Shorts JSON. Please retry.")

@app.post("/api/render")
def render_video(req: RenderRequest):
    if not which("ffmpeg"):
        raise HTTPException(503, "FFmpeg is required to render videos.")
    job = uuid.uuid4().hex[:10]
    work = OUT / job
    work.mkdir(parents=True)
    paragraphs = [p.strip() for p in req.script.splitlines() if p.strip() and not p.strip().startswith("[VISUAL:")]
    scenes = (paragraphs or [req.script])[:30]
    width, height = (1080, 1920) if req.format == "shorts" else (1920, 1080)
    concat = work / "scenes.txt"
    lines = []
    for i, paragraph in enumerate(scenes):
        img = work / f"scene_{i:03}.png"
        safe = paragraph.replace("\\", " ").replace("'", "’").replace(":", " - ").replace("%", " percent")
        wrapped = textwrap.fill(safe, width=25 if req.format == "shorts" else 48)
        font_size = 54 if req.format == "shorts" else 46
        duration = 4 if req.format == "shorts" else 5
        vf = (
            f"drawtext=text='{wrapped[:600]}':fontcolor=white:fontsize={font_size}:"
            "line_spacing=18:x=(w-text_w)/2:y=(h-text_h)/2:"
            "box=1:boxcolor=0x202e45@0.7:boxborderw=40"
        )
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=0x101827:s={width}x{height}:d={duration}",
                 "-vf", vf, "-frames:v", "1", str(img)],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise HTTPException(500, f"FFmpeg scene rendering failed: {exc.stderr[-1200:]}")
        lines.append(f"file '{img.as_posix()}'\nduration {duration}")
    lines.append(f"file '{(work / f'scene_{len(scenes)-1:03}.png').as_posix()}'")
    concat.write_text("\n".join(lines), encoding="utf-8")
    target = work / "video.mp4"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-vf", "format=yuv420p", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(target)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise HTTPException(500, f"FFmpeg video encoding failed: {exc.stderr[-1200:]}")
    return {
        "job_id": job,
        "video": f"/outputs/{job}/video.mp4",
        "format": req.format,
        "note": "Rendered draft. This MVP uses designed text scenes; cinematic footage, narration and publishing are still integration steps.",
    }

@app.get("/api/jobs")
def jobs():
    return [
        {"id": p.name, "video": f"/outputs/{p.name}/video.mp4"}
        for p in sorted(OUT.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
        if p.is_dir() and (p / "video.mp4").exists()
    ]

app.mount("/outputs", StaticFiles(directory=str(OUT)), name="outputs")
app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")
