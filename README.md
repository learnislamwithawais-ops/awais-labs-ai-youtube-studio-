# Awais Labs AI YouTube Studio

Free-first, open-source-first YouTube production workspace.

## Project status

This repository is the starting point for the Awais Labs AI YouTube Studio MVP. The planned workflow is:

1. Research and select a video topic.
2. Generate a script and scene outline with an open-source/local language model.
3. Create narration and assemble a video with FFmpeg.
4. Prepare title, description, tags, and thumbnail assets.
5. Review the result and publish through the YouTube Data API.

## Development principles

- Prefer free and open-source software.
- Keep provider credentials in environment variables; never commit secrets.
- Make publishing opt-in until the owner configures and tests YouTube OAuth.
- Clearly label generated assets and keep a human review step before public publishing.

## Planned stack

- Python + FastAPI backend
- Ollama-compatible local LLM integration
- FFmpeg media rendering
- YouTube Data API OAuth for uploads
- Web dashboard

## Important

This is an early MVP project, not a fully automated production service yet. YouTube uploads require the owner's own Google Cloud OAuth credentials. Local generation also requires the relevant models and media tools to be installed.

See `.env.example` once configuration files are added. Never commit API keys, OAuth client secrets, refresh tokens, or other credentials.
