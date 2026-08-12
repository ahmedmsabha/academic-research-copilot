# AI Service

FastAPI backend for Academic Research Copilot.

## Task 2 (includes Task 1)

- Gemini LLM + `gemini-embedding-001` embeddings
- PDF upload, PyMuPDF extraction, chunking, pgvector storage
- Project-scoped RAG chat with citation metadata
- Local filesystem object storage (`STORAGE_LOCAL_ROOT`)
- Dev auth via `X-User-Id`

## Run

```bash
cd apps/ai-service
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
# Root .env: GEMINI_API_KEY, DATABASE_URL, EMBEDDING_MODEL=gemini-embedding-001
uvicorn app.main:app --reload --port 8000
```

Apply the Prisma migration from `apps/web` first (`npx prisma migrate deploy`).

## Test

```bash
pytest
ruff check .
ruff format --check .
```
