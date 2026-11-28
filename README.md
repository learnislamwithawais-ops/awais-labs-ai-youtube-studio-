# Awais Labs AI YouTube Studio

Free-first, self-hosted AI creator workspace.

## v0.3 features

- Ollama-based long-form script and multiple Shorts script generation.
- Background production jobs and SQLite job history.
- FFmpeg landscape (16:9) and Shorts (9:16) rendering.
- Optional Edge TTS narration and embedded timed captions.
- Optional Pexels stock video retrieval; text-scene fallback when no API key is configured.
- Uploaded long-video scene-change candidate extraction and vertical clip export.
- Output checks for dimensions, duration, file size and audio presence.
- YouTube Data API upload endpoint gated by OAuth token and explicit server flags.
- Docker Compose stack with FFmpeg and local Ollama.

## Important limitations

This release does not provide guaranteed viral prediction, trend research, original AI text-to-video generation, or fully unattended daily scheduling. Clip extraction is a scene-change heuristic only. ComfyUI endpoint detection is included, but a workflow-specific generation adapter is not implemented. Pexels requires an API key. Edge TTS requires network access. Review generated media and confirm licensing before publishing.

YouTube upload requires a Google Cloud project, enabled YouTube Data API, OAuth consent and a valid authorized-user token at secrets/youtube-token.json. Upload and auto-publish are disabled by default. Set ENABLE_YOUTUBE_UPLOAD=true only after OAuth setup. Auto-publishing additionally requires AUTO_PUBLISH=true and a passed quality check. Default privacy is private.

## Run

Copy .env.example to .env, then run:

    docker compose up --build -d

Open http://localhost:8000. The first launch downloads the Ollama model and may consume several GB.

Useful commands:

    docker compose ps
    docker compose logs -f app
    docker compose logs -f ollama-model-pull
    docker compose down

Never commit .env, API keys or the secrets directory. Do not expose Ollama publicly.

## API

- GET /api/health, /api/config, /api/providers
- POST /api/script and POST /api/shorts
- POST /api/produce for background production
- POST /api/render for manual rendering
- GET /api/jobs and GET /api/jobs/{id}
- POST /api/clips for uploaded source-video clip candidates
- POST /api/publish/{id} for quality-passed jobs

Before public hosting add authentication, rate limits, strict CORS, upload quotas, malware scanning and a durable worker queue. Current background jobs run in the web process and are intended for a private single-instance deployment.
