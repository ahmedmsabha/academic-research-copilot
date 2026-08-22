# API (Task 5)

Base URL: the AI service origin (`API_BASE_URL` / `NEXT_PUBLIC_API_BASE_URL`, default `http://localhost:8000`). The web app proxies browser calls through same-origin `/api/v1`.

Auth (dev): send `X-User-Id: <stable-dev-id>` on every project/conversation/document/prompt-lab request.

## Health

`GET /health` (also `/api/health`) → `{ "status": "ok", "service": "ai-service" }`

`GET /` and `GET /api` return `{ "service": "ai-service", "health": "/health", "api": "/api/v1" }`. App routes live under `/api/v1`, not `/api`.

## Projects

`GET /api/v1/projects`  
`POST /api/v1/projects` body `{ "name": "My Research Project" }`  
Returns the caller's default project when the default name is used and one already exists.

`GET /api/v1/projects/{project_id}/conversations` → owner-scoped list, newest first  

`POST /api/v1/projects/{project_id}/conversations` body `{ "title": "New chat" }`

The first user message retitles a default conversation (`New chat`, `Research chat`, and similar) from the question text.

## Documents

`GET /api/v1/projects/{project_id}/documents` → list of document records

`POST /api/v1/projects/{project_id}/documents`  
Multipart form field: `file` (PDF only).  
Returns the document promptly (`queued` in normal runs). Indexing continues in the background until `ready` or `failed`. Native PyMuPDF text is used first. If the PDF has no text layer, Tesseract OCR runs when `ENABLE_OCR=true` and `tesseract` is installed (the AI service Docker image includes English Tesseract).

`GET /api/v1/projects/{project_id}/documents/{document_id}`

`POST /api/v1/projects/{project_id}/documents/{document_id}/retry`  
Re-runs indexing from a safe state (idempotent for already-`ready` documents). Also restarts jobs left on `extracting` / `chunking` / `embedding` / `indexing` after a process restart. PDFs that produce more than `MAX_INDEX_CHUNKS` (default 400) fail with a user-safe message — upload a shorter paper or a single chapter.

`DELETE /api/v1/projects/{project_id}/documents/{document_id}` → `204`  
Removes DB rows/chunks and deletes the stored PDF object.

Document statuses:

```text
uploaded → queued → extracting → chunking → embedding → indexing → ready
 ↘ failed
```

Upload limits (configurable):

- PDF only (extension + `%PDF-` signature)
- `MAX_UPLOAD_BYTES` (default 20 MiB)
- `MAX_DOCUMENTS_PER_PROJECT` (default 20)

## Messages

`GET /api/v1/conversations/{conversation_id}/messages`

`POST /api/v1/conversations/{conversation_id}/messages`

```json
{
  "content": "What is 12 * (3 + 4)?",
  "mode": "auto"
}
```

`mode` (optional, default `auto`):

| Value | Behavior |
|---|---|
| `auto` | Agent router selects calculator, weather, web search, rag, or llm |
| `llm` | Direct Gemini chat (Task 1 `/chat`) |
| `rag` | Grounded document answers only (Task 2 `/rag`) |
| `calculator` / `weather` / `web_search` | Force that tool |

Routes and user-visible `status` values:

| `route` | `status` |
|---|---|
| `calculator` | Using calculator |
| `weather` | Checking weather |
| `web_search` | Searching the web |
| `rag` | Searching uploaded documents |
| `llm` | Generating response |

Web-search replies include `web_sources` (title, URL, snippet, provider). Those are **not** document citations. RAG replies include `citations` with filename and page; those are **not** web sources.

When the conversation's project has ready documents and the router selects `rag`, citations may be attached. If retrieval finds no strong evidence, the assistant states that the uploaded documents do not contain enough information, `route` remains `rag`, and `citations` is empty.

## Prompt Lab

`GET /api/v1/prompt-library` → versioned templates and “when it performs better” copy.

`POST /api/v1/projects/{project_id}/prompt-experiments`

```json
{
  "input": "Why do researchers use retrieval-augmented generation?",
  "strategies": ["zero_shot", "one_shot", "few_shot", "chain_of_thought", "structured"]
}
```

`strategies` is optional. The default is all five. Blank/whitespace input is rejected (`422`).

Each strategy runs independently with the same model settings. `chain_of_thought` asks for numbered student-facing working (not hidden scratchpad). `structured` is parsed into answer / key points / confidence / limitations; invalid JSON becomes a safe parse-failure message — the raw model text is not returned.

`GET /api/v1/projects/{project_id}/prompt-experiments` → `{ "runs": [ ... ] }` grouped by `run_id`, owner-scoped.

`PATCH /api/v1/prompt-experiments/{experiment_id}`

```json
{
  "rating_accuracy": 5,
  "rating_clarity": 4,
  "rating_research_usefulness": 5
}
```

Ratings are 1–5. Omitted fields are left unchanged. Provide at least one rating.

Example comparison result (synthetic):

```json
{
  "run_id": "…",
  "project_id": "…",
  "input": "Why do researchers use retrieval-augmented generation?",
  "results": [
    {
      "id": "…",
      "strategy": "structured",
      "template_version": "prompt-lab-v1",
      "output": "RAG retrieves evidence before answering.\n\nKey points:\n- Uses documents\n- Reduces unsupported claims\n\nConfidence: high\nLimitations: Depends on retrieval quality.",
      "elapsed_ms": 842,
      "total_tokens": 180,
      "cost_usd": null,
      "rating_accuracy": null
    }
  ]
}
```

`cost_usd` is always `null` until a documented pricing formula exists. Token fields are `null` when the provider does not return usage metadata.

## Errors

Problem-detail shape:

```json
{
  "error": {
    "code": "UNSUPPORTED_DOCUMENT",
    "message": "Only PDF documents are supported.",
    "request_id": "..."
  }
}
```

Common document/RAG/tool codes: `UNSUPPORTED_DOCUMENT` (415), `DOCUMENT_TOO_LARGE` (413), `DOCUMENT_PROCESSING_ERROR` (422), `DOCUMENT_LIMIT` (409), `NOT_FOUND` (404), `PROVIDER_UNAVAILABLE` (503), `PROVIDER_TIMEOUT` (504), `TOOL_VALIDATION_ERROR` (400).

Prompt Lab uses `VALIDATION_ERROR` (422) for blank input and `NOT_FOUND` (404) when the project or experiment is not in the caller's scope.

Stack traces and secrets are never returned.
