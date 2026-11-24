# Awais Labs AI YouTube Studio

Free-first, open-source-first YouTube creator workspace.

## Current MVP

- FastAPI backend and responsive web dashboard
- Script generation through a locally hosted Ollama model
- Basic 1080p text-scene MP4 rendering through FFmpeg
- Job listing endpoint and downloadable rendered MP4s
- Docker Compose setup for the app, Ollama, and automatic model download

This is a working starter MVP, **not yet a fully autonomous YouTube publishing platform**. It does not yet generate cinematic footage, speech narration, Shorts automatically, schedule uploads, or publish to YouTube. Those require additional integrations and testing.

## Run with Docker (recommended)

Requirements: Docker Desktop (Windows/macOS) or Docker Engine plus the Docker Compose plugin (Linux).

1. Clone this repository and open a terminal in its folder.
2. Optional: copy `.env.example` to `.env` and change `OLLAMA_MODEL` if desired. The default is `llama3.2`.
3. Build and start everything:

```bash
docker compose up --build -d
```

4. Open **http://localhost:8000**.

On the first run, Compose starts the Ollama service and automatically downloads the configured model. This can take several minutes and several GB of disk space. Check progress with:

```bash
docker compose logs -f ollama-model-pull
```

Useful commands:

```bash
# View service status
docker compose ps

# View app logs
docker compose logs -f app

# Stop containers (keeps downloaded model and rendered videos)
docker compose down

# Rebuild the app after code changes
docker compose up --build -d

# Stop and DELETE saved model + rendered-video volumes
docker compose down -v
```

The app is available on port 8000. Ollama is bound to localhost port 11434 for local troubleshooting; the app talks to it over the private Compose network. Do not expose Ollama directly to the public internet.

## Run locally without Docker

Requirements: Python 3.11+, FFmpeg, and Ollama.

```bash
ollama pull llama3.2
ollama serve
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Configuration

For Docker, Compose reads `OLLAMA_MODEL` from your shell or a local `.env` file; it defaults to `llama3.2`. The Ollama endpoint inside Docker is set to `http://ollama:11434` automatically.

For a non-Docker run, set `OLLAMA_URL`, `OLLAMA_MODEL`, and `OUTPUT_DIR` in your environment. Never commit real credentials or a populated `.env` file.

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
- YouTube OAuth and publishing are not implemented in this MVP. Public uploads need a properly configured Google Cloud project, OAuth consent, and YouTube Data API review/quotas.

## Roadmap

1. Narration via a local TTS engine.
2. Licensed stock footage and image retrieval per scene.
3. Shorts extraction, captions, and vertical rendering.
4. Persistent projects, background queue, retries, and progress.
5. YouTube OAuth, upload review, scheduling, and analytics.
6. Authentication, rate limits, deployment hardening, and tests.
