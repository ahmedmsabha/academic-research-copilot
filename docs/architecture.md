# Architecture (Task 5 — Complete assistant)

Academic Research Copilot is a monorepo with a Next.js frontend and a FastAPI AI service. Task 5 unifies chat, RAG, tools, and Prompt Lab behind a workspace UI and a Dockerized local stack.

## System overview

```text
┌────────────────────┐       HTTP /api/v1        ┌──────────────────────────────┐
│  apps/web          │ ─────────────────────────▶│  apps/ai-service             │
│  Next.js + TS      │◀───────────────────────── │  FastAPI + Pydantic          │
│  Workspace / Chat  │                           │  Chat + RAG + Agent + Lab    │
│  RAG / Agent / Lab │                           │                              │
└────────────────────┘                           └──────────────┬───────────────┘
                                                                │
        ┌───────────────────────────────────────────────────────┼─────────────────┐
        │                                                       ▼                 │
        │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
        │  │ Gemini LLM   │  │ Gemini embed │  │ Open-Meteo  │  │ DuckDuckGo   │  │
        │  │ + JSON router│  │ + pgvector   │  │ weather     │  │ HTML / Tavily│  │
        │  └──────────────┘  └──────────────┘  └─────────────┘  └──────────────┘  │
        │         ▲                  ▲                                            │
        │         │                  │                                            │
        │  ┌──────┴──────┐   ┌───────┴────────┐  ┌────────────┐                   │
        │  │ Prompt Lab  │   │ Postgres       │  │ Local PDF  │                   │
        │  │ templates   │   │ + pgvector     │  │ storage    │                   │
        │  └─────────────┘   └────────────────┘  └────────────┘                   │
        └─────────────────────────────────────────────────────────────────────────┘
```

Docker Compose runs `web`, `ai-service`, and `postgres` (pgvector image), with a one-shot `migrate` service. Tool routing is in [`architecture-diagram.svg`](architecture-diagram.svg). Task 2 RAG overview remains [`architecture-diagram.png`](architecture-diagram.png).

## Workspace data flow

1. Validate user, project, conversation, and message text.
2. List or create conversations for the active project (`GET/POST .../conversations`).
3. On the first user message, retitle a default conversation from the question text.
4. If `mode` is pinned, use that route; otherwise deterministic rules plus constrained JSON classification.
5. Emit a user-safe status only. Never expose chain-of-thought.
6. Execute one selected tool/service with validated arguments and timeouts.
7. Persist user and assistant messages. Document citations come from retrieval metadata; web/weather answers are labeled external.

## Prompt Lab data flow

1. Validate user, project, and non-blank input.
2. Load versioned templates (`prompt-lab-v1`) for the requested strategies (default: all five).
3. Run each strategy independently against the same model settings (`asyncio.gather`).
4. For `structured`, parse JSON and return formatted fields only. Invalid JSON becomes a safe parse-failure message — raw model text is not shown.
5. Persist successful results with template version, elapsed time, and usage tokens when the provider returns them. `cost_usd` stays unavailable.
6. Ratings (accuracy / clarity / research usefulness, 1–5) are stored on the experiment row, still scoped to the owner and project.

## Upload / RAG

1. Upload PDF → validate → store object → index (`queued → … → ready`).
2. Grounded answers retrieve project-scoped chunks and attach citations from retrieval metadata.
3. Insufficient evidence is returned honestly when scores are weak.

## Project isolation

Every document, chunk, conversation, retrieval query, tool-backed chat, and prompt experiment is scoped by owner (`X-User-Id` in development) and `project_id`.

## Production notes

- `APP_ENV=production` requires `GEMINI_API_KEY` and `DATABASE_URL` and rejects fake providers.
- `/docs` is disabled in production.
- Deploy steps: [`deploy.md`](deploy.md).
