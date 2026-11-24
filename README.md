# Awais Labs AI YouTube Studio

Free-first, open-source-first YouTube creator workspace.

## Current MVP

- FastAPI backend and responsive web dashboard
- Script generation through a locally hosted Ollama model
- Basic 1080p text-scene MP4 rendering through FFmpeg
- Job listing endpoint and downloadable rendered MP4s
- Dockerfile and environment template

This is a working starter MVP, **not yet a fully autonomous YouTube publishing platform**. It does not yet generate cinematic footage, speech narration, Shorts automatically, schedule uploads, or publish to YouTube. Those require additional integrations and testing.

## Run locally

Requirements: Python 3.11+, FFmpeg, and Ollama.

```bash
ollama pull llama3.2
ollama serve
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Configuration

Copy `.env.example` to `.env` and adjust `OLLAMA_URL`, `OLLAMA_MODEL`, and `OUTPUT_DIR` as needed. Load environment variables in your shell or use a local dotenv runner.

## API

- `GET /api/health` — service health
- `GET /api/config` — runtime configuration
- `POST /api/script` — generate a script using Ollama
- `POST /api/render` — render a simple title/paragraph-scene video
- `GET /api/jobs` — list rendered jobs

Example script request:

```json
{"topic":"The science of black holes","duration_minutes":5,"language":"English","style":"engaging documentary"}
```

## Security and deployment

- Never commit API keys, OAuth client secrets, refresh tokens, or `.env` files.
- The current CORS policy is permissive for local development; restrict origins before public deployment.
- The current render endpoint is synchronous and intended for small MVP jobs; add a persistent queue, limits, and authentication before public multi-user hosting.
- Do not expose a local Ollama instance directly to the public internet.
- YouTube OAuth and publishing are not implemented in this MVP. Public uploads need a properly configured Google Cloud project, OAuth consent, and YouTube Data API review/quotas.

## Roadmap

1. Narration via a local TTS engine.
2. Licensed stock footage and image retrieval per scene.
3. Shorts extraction, captions, and vertical rendering.
4. Persistent projects, background queue, retries, and progress.
5. YouTube OAuth, upload review, scheduling, and analytics.
6. Authentication, rate limits, deployment hardening, and tests.
