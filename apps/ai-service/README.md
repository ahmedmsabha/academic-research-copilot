# AI Service

FastAPI backend for Academic Research Copilot.

## Task 1

- Gemini LLM provider (`google-genai`)
- Project / conversation / message APIs
- Postgres persistence via SQLAlchemy against Prisma-managed tables
- Dev auth via `X-User-Id`

## Run

```bash
cd apps/ai-service
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp ../../.env.example ../../.env   # set GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

## Test

```bash
pytest
ruff check .
ruff format --check .
```
