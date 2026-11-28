# Awais Labs AI YouTube Studio

Free-first, open-source-first YouTube creator workspace.

## Current MVP (v0.2)

- FastAPI backend and responsive web dashboard
- Long-form script generation through a locally hosted Ollama model
- Generate up to five distinct Shorts scripts per request (default target: three daily)
- FFmpeg draft rendering in landscape (16:9) and vertical Shorts (9:16)
- Job listing endpoint and downloadable MP4 drafts
- Docker Compose setup for the app, Ollama, and automatic model download

**Important:** This is still an MVP, not a fully autonomous publishing platform. The renderer currently creates designed text-scene drafts; cinematic footage, narration, automated clip extraction, persistent background jobs, YouTube OAuth/upload, scheduling, and analytics are not yet implemented. Do not treat generated drafts as production-ready cinematic videos.

## Run with Docker

Requirements: Docker Desktop or Docker Engine with Docker Compose.

```bash
git clone https://github.com/learnislamwithawais-ops/awais-labs-ai-youtube-studio-.git
cd awais-labs-ai-youtube-studio-
docker compose up --build -d
```

Open http://localhost:8000. First startup downloads the configured Ollama model (default `llama3.2`), which can take several minutes and several GB of disk space.

Useful commands:

```bash
docker compose ps
docker compose logs -f app
docker compose logs -f ollama-model-pull
docker compose down
```

## Local run

Requirements: Python 3.11+, FFmpeg, and Ollama.

```bash
ollama pull llama3.2
ollama serve
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

- `GET /api/health` — health and version
- `GET /api/config` — runtime settings and supported formats
- `POST /api/script` — long-form script
- `POST /api/shorts` — generate 1–5 distinct Shorts scripts
- `POST /api/render` — render a draft; set `format` to `landscape` or `shorts`
- `GET /api/jobs` — rendered drafts

Example Shorts request:

```json
{"topic":"Hidden facts about space","count":3,"language":"English"}
```

## Configuration and security

Set `OLLAMA_MODEL`, `OLLAMA_URL`, and `OUTPUT_DIR` as needed. Never commit API keys, OAuth secrets, refresh tokens, or a populated `.env` file. The current CORS policy is permissive for local development; restrict origins, add authentication, limits, and a persistent queue before public hosting.

YouTube publishing is intentionally not enabled until Google Cloud OAuth credentials, channel authorization, and upload review controls are implemented.
