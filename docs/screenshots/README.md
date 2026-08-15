# Screenshots

## Task 1 — Chat

- `task1-chat-empty.png`
- `task1-chat-reply.png`
- `task1-chat-error.png`

## Task 2 — RAG

- `task2-documents-empty.png` — documents panel empty state
- `task2-document-ready.png` — uploaded PDF marked Ready for search (with upload date/size/pages)
- `task2-rag-citation.png` — grounded answer with Sources (filename + page)
- `fixtures/task2-demo-notes.pdf` — tiny synthetic PDF for local demos

Prefer synthetic or public PDFs in screenshots. Never include secrets or private documents.

## Task 3 — Agent tools

Capture from `/agent` (wide viewport so status labels are readable):

- `task3-agent-empty.png` — empty agent chat with example prompts
- `task3-calculator.png` — “Using calculator” status and a numeric result
- `task3-weather.png` — “Checking weather · External tool” and a labeled weather answer
- `task3-web-search.png` — “Searching the web · External tool” plus Web sources (external)

Architecture:

- `../architecture-diagram.svg` — Task 3 system + tool diagram
- `../architecture-diagram.png` — Task 2 overview (still valid as the RAG slice)

## Task 4 — Prompt Lab

Capture from `/prompt-lab` (wide viewport so two result cards are visible):

- `task4-lab-empty.png` — comparison table + empty state
- `task4-comparison.png` — five strategy results for the same question
- `task4-structured.png` — structured card with key points (no hidden CoT)
- `task4-library.png` — Prompt library details open (`prompt-lab-v1`)

Prefer synthetic questions in screenshots. Never include secrets or private documents.

## Task 5 — Complete assistant

Capture from `/workspace` (wide viewport so history, chat, and documents are visible):

- `task5-workspace-empty.png` — history sidebar, empty chat, documents panel
- `task5-workspace-rag.png` — grounded answer with filename/page citation
- `task5-workspace-tools.png` — calculator or weather/search with a labeled external status
- `task5-landing.png` — product overview with Open workspace

Architecture:

- `../architecture-diagram.svg` — agent + RAG + tools
- `../architecture-diagram.png` — Task 2 RAG slice

