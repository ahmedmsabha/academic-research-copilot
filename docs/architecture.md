# Architecture (Task 2 — RAG)

Academic Research Copilot is a monorepo with a Next.js frontend and a FastAPI AI service. Task 2 adds project-scoped PDF upload, indexing, pgvector retrieval, and grounded chat citations.

## System overview

```text
┌────────────────────┐       HTTP /api/v1        ┌──────────────────────────┐
│  apps/web          │ ─────────────────────────▶│  apps/ai-service         │
│  Next.js + TS      │◀───────────────────────── │  FastAPI + Pydantic      │
│  Chat + Documents  │                           │  RAG + Chat services     │
└────────────────────┘                           └────────────┬─────────────┘
                                                              │
                 ┌────────────────────────────────────────────┼────────────────┐
                 │                                            ▼                │
                 │  ┌──────────────┐   ┌────────────────┐  ┌────────────────┐ │
                 │  │ Gemini LLM   │   │ Gemini embed   │  │ Local PDF      │ │
                 │  │ generate     │   │ text-embedding │  │ storage (.data)│ │
                 │  └──────────────┘   │ -004           │  └────────────────┘ │
                 │                     └────────────────┘                      │
                 │                            ▲                                │
                 │                            │                                │
                 │                   ┌────────┴────────┐                       │
                 │                   │ Prisma Postgres │                       │
                 │                   │ + pgvector      │                       │
                 │                   └─────────────────┘                       │
                 └─────────────────────────────────────────────────────────────┘
```

## Upload and indexing flow

1. Authenticated user uploads a PDF to `POST /api/v1/projects/{project_id}/documents`.
2. AI service validates PDF signature/size, stores bytes via `ObjectStorage` (local filesystem for Task 2), and creates a `documents` row (`status=queued`).
3. Background indexing runs the state machine:
   `queued → extracting → chunking → embedding → indexing → ready` (or `failed`).
4. PyMuPDF extracts page-aware text; chunker splits ~800 chars with ~150 overlap.
5. Gemini `gemini-embedding-001` embeds each chunk (768-dim via `output_dimensionality`); vectors are stored in `document_chunks.embedding` (`vector(768)`).

## Grounded question answering

1. User sends a chat message for a project conversation.
2. If the project has any `ready` documents, ChatService uses the `rag` route:
   - Embed the question
   - Retrieve top-k chunks by cosine distance, filtered by `project_id`, `status=ready`, and embedding model/dimension
   - If no chunk is under the distance threshold, return an honest insufficient-evidence answer (no fabricated citations)
   - Otherwise prompt Gemini with delimited document excerpts only
3. Citations are built in application code from retrieval metadata (`Filename.pdf, p. N`) and returned/persisted with the assistant message.
4. If no ready documents exist, ChatService keeps the Task 1 `llm` route.

## Project isolation

Every document, chunk, conversation, and retrieval query is scoped by owner (`X-User-Id` in development) and `project_id`. Deleting a document removes chunks and the storage object so it cannot be retrieved again.

## Future (later tasks)

- Agent router + calculator / weather / web search (Task 3)
- Prompt Lab (Task 4)
- Dockerized stack, production object storage, and full auth (Task 5)
