# GitHub Dev Card Generator

Generate stylish developer profile cards from a GitHub username using a FastAPI backend, MCP tools, and an AI analysis pipeline.

## Project Structure

- `backend/`: FastAPI API, ADK agent setup, MCP tool server, static card output
- `frontend/`: Static UI served from Nginx
- `docker-compose.yml`: Local multi-service setup

## Features

- Fetches GitHub profile + top repositories
- Infers developer vibe, top skills, and fun fact
- Generates self-contained HTML developer card
- Saves cards under `backend/static/cards/`
- Includes fallback generation pipeline when agent orchestration fails

## Live Demo

The application is deployed on Google Cloud Run:
- **Frontend App**: https://github-dev-card-frontend-mxyatg35fa-uc.a.run.app
- **Backend API**: https://github-dev-card-backend-mxyatg35fa-uc.a.run.app

## Prerequisites

- Python 3.12+
- `uv` package manager
- Docker + Docker Compose (optional)
- API keys:
  - `GITHUB_TOKEN`
  - `GEMINI_API_KEY`
  - `OPENAI_API_KEY` (recommended fallback)

## Environment Variables

Create `backend/.env`:

```env
GITHUB_TOKEN=your_github_token_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
PORT=8080
```

## Run Locally (Backend only)

```bash
cd backend
uv sync
uv run python main.py
```

Backend runs on `http://localhost:8080`.

## Run with Docker Compose

From repo root:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8080`

## API Usage

### Health Check

```bash
curl http://localhost:8080/health
```

### Generate Card

```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"username":"torvalds"}'
```

### Open Saved Card

`http://localhost:8080/card/<username>`

Example:

`http://localhost:8080/card/torvalds`

## Output

Generated files are written to:

- `backend/static/cards/<username>.html`

## Notes

- If AI provider quota is exhausted for one path, the backend attempts a fallback pipeline.
- Keep `.env` files out of version control.
