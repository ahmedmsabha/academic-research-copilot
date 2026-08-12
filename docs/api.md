# API (Task 1)

Base URL: `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`)

Auth (dev): send `X-User-Id: <stable-dev-id>` on every project/conversation request.

## Health

`GET /health` → `{ "status": "ok" }`

## Projects

`GET /api/v1/projects`  
`POST /api/v1/projects` body `{ "name": "My Research Project" }`  
Returns the caller's default project when the default name is used and one already exists.

`POST /api/v1/projects/{project_id}/conversations` body `{ "title": "New chat" }`

## Messages

`GET /api/v1/conversations/{conversation_id}/messages`

`POST /api/v1/conversations/{conversation_id}/messages` body `{ "content": "..." }`

Success response includes:

```json
{
  "user_message": { "...": "..." },
  "assistant_message": { "...": "..." },
  "route": "llm",
  "status": "Generating response"
}
```

## Errors

Problem-detail shape:

```json
{
  "error": {
    "code": "PROVIDER_UNAVAILABLE",
    "message": "The AI provider is temporarily unavailable. Please try again.",
    "request_id": "..."
  }
}
```

Stack traces and secrets are never returned.
