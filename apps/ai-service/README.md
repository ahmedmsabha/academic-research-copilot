---
title: Academic Research Copilot AI
emoji: 📚
colorFrom: green
colorTo: gray
sdk: gradio
app_file: app.py
pinned: false
short_description: FastAPI research assistant API (chat, RAG, tools, Prompt Lab)
---

# AI Service

FastAPI backend for Academic Research Copilot. Hugging Face **Docker** Spaces are paid; this README uses the free **Gradio** SDK. `app.py` serves the same FastAPI app (`/health`, `/api/v1`) on the Space.

## Task 4 (includes Tasks 1–3)

- Versioned Prompt Lab templates (`zero_shot`, `one_shot`, `few_shot`, `chain_of_thought`, `structured`)
- Project-scoped prompt experiments with ratings, timing, and usage when the provider returns it
- Gemini LLM + constrained JSON route classification
- Safe AST calculator (no `eval`)
- Open-Meteo weather + DuckDuckGo HTML / Tavily / Gemini search behind provider adapters
- Gemini `gemini-embedding-001` embeddings and project-scoped RAG
- PDF upload, PyMuPDF extraction, chunking, pgvector storage
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
