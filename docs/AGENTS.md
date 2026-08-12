# AGENTS.md — `docs/`

Documentation for Academic Research Copilot. Follow the root [`AGENTS.md`](../AGENTS.md); this file scopes doc ownership.

## Purpose

Keep architecture, API contracts, demo guidance, prompt comparison reports, and screenshots accurate with the running product.

## Layout

```text
docs/
├── architecture.md
├── architecture-diagram.png
├── api.md
├── demo-script.md
├── prompt-comparison-report.md
├── screenshots/
└── AGENTS.md
```

## Rules

1. Update docs in the same change that alters behavior, contracts, or setup—not afterward.
2. Use synthetic examples only; never put secrets, private PDFs, or real credentials in docs or screenshots.
3. `architecture.md` must describe frontend, AI service, PostgreSQL/pgvector, storage, LLM/embeddings, and tools, plus upload/RAG/tool data flows.
4. `api.md` must document auth assumptions, endpoint contracts, error shapes, upload limits, and streaming if present.
5. Screenshots should cover chat, PDF upload/indexing, RAG citations, tool-calling status, Prompt Lab, and project/document library when those features exist.
6. Prompt comparison content must not present hidden chain-of-thought as a deliverable; show structured final outputs only.
