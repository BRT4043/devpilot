# DevPilot AI — backend

## First run
1. `cp .env.example .env` and fill in the GitHub OAuth + key values
2. `docker compose up --build`
3. API docs: http://localhost:8000/docs  ·  Health: http://localhost:8000/health

## Layout
- `app/routers/`  — HTTP layer only
- `app/services/` — business logic
- `app/rag/`      — ingestion, chunking, embeddings, Qdrant, retrieval
- `app/workers/`  — ARQ background jobs (repo indexing)

## Rules the team agreed on
- Routers never touch the DB or LLM directly
- All LLM calls go through services/llm_service.py
- Migrations via Alembic from the first table
- Tests run in CI on every push

## Testing
`pytest -q` runs the fast unit suite — no external services needed; LLM
calls and RAG retrieval are faked.

Anything that needs real SQL (persistence, cascades, ownership queries
across tables) lives in `tests/integration/` and needs a live Postgres:

```
docker compose -f docker-compose.test.yml up -d
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/devpilot_test
pytest -m integration
docker compose -f docker-compose.test.yml down -v
```

Without `TEST_DATABASE_URL` set, `tests/integration/` isn't even collected,
so the plain `pytest -q` job stays fast and DB-free. CI runs both jobs —
see `.github/workflows/ci.yml`.
