# Project presentation — Academic Research Copilot

Use this outline for a 5–7 minute walkthrough (slides or live demo).

## 1. Problem (30s)

Students and researchers need help with papers, but generic chatbots invent citations, mix private documents, and hide how they used tools. The product is an assistant for understanding — not a replacement for reading sources.

## 2. Solution (45s)

Academic Research Copilot is one web app with:

- Persistent chat
- Project-scoped PDF RAG with filename/page citations
- An agent that can use a calculator, weather, or web search
- Prompt Lab for comparing prompting strategies
- A unified workspace that combines those capabilities

## 3. Architecture (60s)

Show [`architecture-diagram.svg`](architecture-diagram.svg).

- Next.js frontend never calls Gemini, embeddings, search, or storage directly
- FastAPI owns routing, tools, retrieval, and provider adapters
- Prisma Postgres + pgvector stores chats, documents, chunks, and experiments
- Docker Compose runs the same three-process shape locally

## 4. Live demo (3 min)

Follow [`demo-script.md`](demo-script.md): workspace → PDF citation → calculator → weather or search → Prompt Lab.

## 5. Engineering choices (60s)

- Citations come from retrieval metadata, not free-form model text
- Insufficient evidence is an honest outcome
- Tools are validated; the calculator never uses `eval`
- External answers are labeled; document citations are not web sources
- Prompt Lab CoT is student-facing numbered working, not a hidden scratchpad

## 6. Close (30s)

GitHub, live URL, and the lesson: production AI is product rules (isolation, citations, safe errors) as much as model calls.
