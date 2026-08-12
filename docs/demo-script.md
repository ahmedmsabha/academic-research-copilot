# Task 1 demo script (2–3 minutes)

Use this while screen-recording. Speak naturally; do not show `.env` or API keys.

## Prep (before recording)

1. Terminal A — AI service:

```bash
cd apps/ai-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

2. Terminal B — web:

```bash
cd apps/web
npm run dev
```

3. Browser: open `http://localhost:3000` in a clean window (optional: DevTools closed for cleaner video).

## Script

### 0:00–0:20 — Intro

> “This is Academic Research Copilot, Task 1: a Gemini-powered research chatbot. Frontend is Next.js; backend is FastAPI; history is stored in Prisma Postgres.”

Show the empty chat state briefly.

### 0:20–1:10 — Happy path

1. Type: `Explain retrieval-augmented generation in two sentences for a student.`
2. Press Enter.
3. Point at the **Generating response…** loading state.
4. When the answer appears, scroll if needed and say: “Reply comes from Gemini through the AI service — the browser never holds the API key.”

### 1:10–1:40 — History

1. Refresh the page.
2. Confirm the same messages reload.
3. Say: “History is persisted in Postgres, so it survives refresh and AI-service restarts.”

### 1:40–2:20 — Error handling

1. Stop the AI service (Ctrl+C in Terminal A).
2. Send another short message.
3. Show the red error banner — user-safe message, no stack trace.
4. Restart the AI service and optionally send one more message to recover.

### 2:20–2:45 — Close

> “Next milestones: PDF RAG with citations, tool-calling agent, Prompt Lab, then deploy. Thanks for watching.”

## Optional talking points

- Architecture: `apps/web` → `POST /api/v1/conversations/{id}/messages` → Gemini
- Blank messages are blocked in the UI and validated on the API
- Tests use a fake LLM so CI never calls Gemini
