# API (Task 2)

Base URL: `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)

Auth (dev): send `X-User-Id: <stable-dev-id>` on every project/conversation/document request.

## Health

`GET /health` → `{ "status": "ok" }`

## Projects

`GET /api/v1/projects`  
`POST /api/v1/projects` body `{ "name": "My Research Project" }`  
Returns the caller's default project when the default name is used and one already exists.

`POST /api/v1/projects/{project_id}/conversations` body `{ "title": "New chat" }`

## Documents

`GET /api/v1/projects/{project_id}/documents` → list of document records

`POST /api/v1/projects/{project_id}/documents`  
Multipart form field: `file` (PDF only).  
Returns the document promptly (`queued` in normal runs). Indexing continues in the background until `ready` or `failed`.

`GET /api/v1/projects/{project_id}/documents/{document_id}`

`POST /api/v1/projects/{project_id}/documents/{document_id}/retry`  
Re-runs indexing from a safe state (idempotent for already-`ready` documents).

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

`POST /api/v1/conversations/{conversation_id}/messages` body `{ "content": "..." }`

When the conversation's project has ready documents, the service uses route `rag` and may attach citations. Otherwise it uses route `llm`.

Success response:

```json
{
  "user_message": { "...": "..." },
  "assistant_message": {
    "role": "assistant",
    "content": "...",
    "route": "rag",
    "status": "Searching uploaded documents",
    "citations": [
      {
        "document_id": "...",
        "chunk_id": "...",
        "filename": "notes.pdf",
        "page_start": 1,
        "page_end": 1,
        "label": "notes.pdf, p. 1"
      }
    ]
  },
  "route": "rag",
  "status": "Searching uploaded documents",
  "citations": []
}
```

If retrieval finds no strong evidence, the assistant content states that the uploaded documents do not contain enough information, `route` remains `rag`, and `citations` is empty.

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

Common document/RAG codes: `UNSUPPORTED_DOCUMENT` (415), `DOCUMENT_TOO_LARGE` (413), `DOCUMENT_PROCESSING_ERROR` (422), `DOCUMENT_LIMIT` (409), `NOT_FOUND` (404), `PROVIDER_UNAVAILABLE` (503).

Stack traces and secrets are never returned.
