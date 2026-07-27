# DevPilot 

An AI workspace for chatting with a GitHub repository. Connect a repo, DevPilot
indexes it (clone → chunk → embed → Qdrant), then every answer is grounded in
the actual code, with citations linking to exact files and lines at the
commit that was indexed.

## Structure

- [`devpilot-backend/`](devpilot-backend) — FastAPI + Postgres + Redis + Qdrant. GitHub OAuth, RAG
  pipeline, streaming chat, AI Tech Lead mode, debug assistant, interview
  question generation, commit-message generation.
- [`devpilot-frontend/`](devpilot-frontend) — Next.js (App Router) UI: login, repo picker, streamed
  chat with source citations and Mermaid diagrams, session history.

## Running locally

**Backend**
```bash
cd devpilot-backend
cp .env.example .env   # fill in GitHub OAuth + LLM API key
docker compose up --build
```
API docs at `http://localhost:8000/docs`.

**Frontend**
```bash
cd devpilot-frontend
npm install
npm run dev
```
Runs at `http://localhost:3000`, talking to the backend on `:8000`.

## Features

- Repo-grounded, streamed chat with clickable source citations
- AI Tech Lead mode — asks clarifying questions before proposing a plan on
  build/implement requests
- Debug assistant — paste a stack trace, get root-cause analysis grounded in
  the exact files it mentions
- Interview question generator — repo-specific technical questions
- Live Mermaid diagram rendering when a diagram helps explain an answer
- AI commit-message generation from a diff

See each app's own README for architecture details and design decisions.
