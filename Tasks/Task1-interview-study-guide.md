# Task 1 interview study guide

Academic Research Copilot — first AI chatbot. Memorize the pitch, then the request path, then the “why” behind each decision. Later tasks (RAG, tools, Prompt Lab) sit on this same chat pipeline; they are not Task 1.

## 30-second pitch — say this first

I built a research chatbot where the browser never talks to Gemini. Next.js renders the chat UI; FastAPI owns the Gemini call, conversation persistence in Postgres, and user-safe errors. Secrets stay on the server. Tests use a fake LLM so CI never hits a paid API.


|                  |                           |
| ---------------- | ------------------------- |
| Task 1 demo page | `/chat`                   |
| Pinned route     | `mode=llm`                |
| LLM              | Gemini via `google-genai` |
| Durable history  | Postgres                  |




## What Task 1 is (and is not)


| Requirement          | What this app does                                            | Do not claim in Task 1                                 |
| -------------------- | ------------------------------------------------------------- | ------------------------------------------------------ |
| Integrate an LLM API | `GeminiLLMProvider` in `apps/ai-service/app/providers/llm.py` | Browser fetch to Google; OpenAI/Claude SDKs            |
| Simple chat UI       | `ChatPanel` + `ChatComposer` + `MessageList` on `/chat`       | Workspace sidebar, PDF panel, Prompt Lab               |
| Conversation history | GET/POST messages; last 40 turns sent to Gemini               | Token-budget summarization or streaming replay         |
| Loading indicator    | `sending` + “Generating response…” bubble                     | SSE token streaming (not implemented)                  |
| Graceful API errors  | RFC 7807-style `{ error: { code, message, request_id } }`     | Stack traces, raw Gemini exceptions                    |
| Project structure    | Monorepo: `apps/web` (Next.js) + `apps/ai-service` (FastAPI)  | A single Next.js API route that holds `GEMINI_API_KEY` |




## Request path you must be able to draw

Browser `ChatPanel` → typed client `lib/api.ts` → same-origin Next.js proxy `app/api/v1/[...path]` → FastAPI `POST /api/v1/conversations/{id}/messages` → `ChatService.send_message` → `select_route(preferred=llm)` returns immediately → `_answer_with_llm` → `GeminiLLMProvider.generate` → persist assistant message → JSON back to the UI.


| Step | Layer         | File                            | What happens                                                                     |
| ---- | ------------- | ------------------------------- | -------------------------------------------------------------------------------- |
| 1    | UI            | `ChatComposer.tsx`              | Trim text. Block blank. Enter sends, Shift+Enter newline. Disable while sending. |
| 2    | UI state      | `ChatPanel.tsx`                 | Optimistic user bubble. `loadingStatus` = Generating response…                   |
| 3    | Client        | `lib/api.ts`                    | POST JSON `{ content, mode: "llm" }` with `X-User-Id` from localStorage.         |
| 4    | Proxy         | `app/api/v1/[...path]/route.ts` | Forwards to FastAPI. `API_BASE_URL` is server-only. 60s `maxDuration`.           |
| 5    | Auth          | `core/security.py`              | `require_user_id`. Missing/invalid header → `401 UNAUTHORIZED`.                  |
| 6    | Validate      | `schemas.py` + `ChatService`    | Pydantic `min_length` + strip. Max 8000 chars. Blank → `422`.                    |
| 7    | Persist user  | `postgres_store.py`             | `append_message` user row first. Optional retitle from first question.           |
| 8    | Route         | `agent/router.py`               | `preferred=llm` is pinned. No calculator, weather, search, or RAG.               |
| 9    | LLM           | `providers/llm.py`              | Map history to Gemini contents. `system_instruction` separate. Timeout 30s.      |
| 10   | Persist reply | `ChatService._answer_with_llm`  | Save assistant text, `route=llm`, `status=Generating response`, provider, model. |




## Architecture decisions — say the “why”



### Why Gemini is never called from the browser

`GEMINI_API_KEY` would leak in `NEXT_PUBLIC_*` / Network tab. The backend also enforces length limits, owner-scoped history, and maps provider failures to safe codes. The frontend only calls `/api/v1`.

### Why `LLMProvider` is a Protocol

`GeminiLLMProvider` wraps `google-genai`. `FakeLLMProvider` records calls and returns a fixed string. Pytest never spends quota. Same `ChatService` in prod and tests — only the adapter changes.

### Why Prisma and SQLAlchemy both exist

Prisma in `apps/web` owns schema and migrations. FastAPI SQLAlchemy (`ProjectRow`, `ConversationRow`, `MessageRow`) owns runtime chat writes. One Postgres, two clients. Do not say “Prisma Client generates the replies.”

### Why `/chat` pins `mode=llm`

`ChatService` later grew RAG and tools. Task 1’s page still sends `mode=llm` so the interviewer sees a plain chatbot. `select_route` short-circuits on pinned routes (`source=preferred`) and never classifies the question.

## History, identity, and isolation

Two kinds of “history” exist. Do not mix them in the interview.


| Kind                 | Where                                                    | Purpose                                                                                |
| -------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Durable messages     | Postgres `messages` table                                | Survive refresh. `GET /conversations/{id}/messages`. Ordered by `created_at`, then id. |
| Session pointers     | localStorage `arc.projectId` + `arc.conversationId.chat` | Reopen the same project/conversation in this browser. Not the transcript.              |
| Model context window | `Settings.max_history_messages = 40`                     | Only the last 40 user/assistant turns are sent to Gemini. Older rows stay in DB.       |
| Dev identity         | `X-User-Id` header; localStorage `arc.userId`            | Until real auth. Owner-scoped queries. Other user’s conversation → 404, not 403.       |


**404 not 403.** If Bob asks for Alice’s conversation, the API returns Conversation not found (`NOT_FOUND`). That avoids leaking that the id exists. Isolation is tested in `test_project_isolation` and `test_list_conversations_is_owner_scoped`.

## Gemini mapping details interviewers love


| App concept              | Gemini API fact                                                |
| ------------------------ | -------------------------------------------------------------- |
| `role: assistant`        | Mapped to `role: model` in `history_to_gemini_contents`        |
| System prompt            | `GenerateContentConfig.system_instruction` — not a chat turn   |
| Empty / whitespace turns | Skipped so Gemini does not get blank parts                     |
| Empty model text         | `ProviderUnavailableError` — do not persist an empty assistant |
| Timeout / 429 / bad key  | Mapped to 504 / 503 with user-safe messages                    |
| Default model            | `gemini-flash-lite-latest` via `LLM_MODEL`                     |
| Timeout                  | `LLM_TIMEOUT_MS = 30000`, passed as `HttpOptions.timeout`      |


System instruction: Academic Research Copilot for students/researchers. Be clear. Do not invent citations or claim private documents unless they are in the conversation. (RAG has a stricter prompt — that is Task 2.)

## Error handling — codes to recite


| HTTP | code                    | When                                              |
| ---- | ----------------------- | ------------------------------------------------- |
| 401  | `UNAUTHORIZED`          | Missing or invalid `X-User-Id`                    |
| 404  | `NOT_FOUND`             | Conversation not owned / missing                  |
| 422  | `VALIDATION_ERROR`      | Blank message or Pydantic schema failure          |
| 503  | `PROVIDER_UNAVAILABLE`  | Gemini down, empty reply, rate limit              |
| 503  | `PROVIDER_CONFIG_ERROR` | Missing key, rejected credentials, bad model name |
| 504  | `PROVIDER_TIMEOUT`      | Deadline / timed out in SDK error text            |
| 500  | `INTERNAL_ERROR`        | Unhandled — generic message, no traceback         |


UI: `ChatPanel` shows `role=alert` with `ApiError.message`. Optimistic user bubble is removed on failure. Network failure from the proxy is `502 NETWORK_ERROR`: unable to reach the AI service.

**Known gap — own it if asked.** The user message is committed before Gemini runs. If `generate()` fails, that user row stays in the DB with no assistant reply. Tests cover the safe error body, not a transactional rollback.

## UI behavior to demo live


| State         | What the interviewer should see                                        |
| ------------- | ---------------------------------------------------------------------- |
| Empty         | “Ask a research question” + history-in-database copy                   |
| Bootstrapping | “Preparing your workspace…” (creates project + conversation)           |
| Sending       | Composer disabled; pulse + Generating response…                        |
| Success       | User bubble right, assistant left; Markdown via `react-markdown` + GFM |
| Error         | Danger alert; composer re-enabled; optimistic message gone             |
| Reload        | Same conversation loads from GET messages (localStorage ids)           |




## Drill these questions



### Walk me through sending a message

User types in `ChatComposer`. Client validates non-blank, POSTs through the Next proxy with `X-User-Id`. FastAPI validates, stores the user message, pins route `llm`, loads last 40 turns, calls `GeminiLLMProvider`, stores the assistant message, returns both. UI replaces the optimistic bubble with the server records.

### Why not put the API key in Next.js?

Anything in `NEXT_PUBLIC_*` or a client bundle is visible. Even a Next server action that only proxies Gemini would skip conversation ownership, history capping, and centralized error mapping. The AI service is the only process allowed to talk to providers.

### How do you test without paying Google?

`conftest` injects `FakeLLMProvider` (and `APP_ENV=test`). `test_send_message_and_list_history` asserts 201, `route=llm`, two messages in GET history. `test_provider_failure_is_user_safe` swaps a BoomLLM that raises `ProviderUnavailableError` and asserts 503 with no Traceback. Unit test `history_to_gemini_contents` maps assistant → model.

### How is conversation history maintained?

Postgres messages, listed oldest-first. Frontend reloads them on bootstrap. For the model, `ChatService` slices `history[-40:]` and only includes user/assistant roles. Gemini contents use user/model. localStorage only stores which conversation id to reopen — not the text.

### What happens if Gemini is down?

SDK exceptions are classified in `_map_provider_exception`. The API returns a problem-detail JSON. The UI shows the message in an alert and rolls back the optimistic user bubble. We do not retry `generate` automatically — that would duplicate assistant messages.

### Is this streaming?

No. One JSON response after generation. Loading is a status bubble, not tokens. `AGENTS.md` allows SSE later; Task 1 did not require it. If asked “what would you add,” say: SSE with user-safe status then tokens, cancel on browser abort, persist only the final assembled assistant text.

### How does this relate to Task 2–5?

Same `ChatService.send_message`. `/chat` keeps `mode=llm`. `/rag` pins `rag`. `/agent` and `/workspace` use `auto` so the router can pick calculator, weather, search, or RAG. Task 1 is the spine: UI, typed client, persistence, provider adapter, safe errors.

### Why FastAPI instead of only Next.js?

PDF indexing, embeddings, and tools are Python-heavy (PyMuPDF, pgvector). A typed FastAPI service with Pydantic schemas, pytest fakes, and a clean router → service → repository/provider split matches how we later added RAG without rewriting the chat UI.

## If they ask “was this AI-generated?”

Do not deny it. Own the architecture.

I used AI to move faster on boilerplate, but I can defend every boundary: secrets stay server-side, the frontend never calls Gemini, tests use a fake provider, errors never leak stack traces, and Task 1 pins `llm` so later tools cannot hijack the demo. Then immediately walk the request path from `ChatComposer` to `GeminiLLMProvider`. That is what they are testing — comprehension, not typing speed.

### Phrases that sound like you built it


| Say                                                                | Avoid                                                            |
| ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| The browser only talks to `/api/v1`; FastAPI owns Gemini.          | The chatbot uses Gemini. (too vague)                             |
| I pin `mode=llm` on `/chat` so the agent router cannot pick tools. | It automatically figures out what to do. (that is Task 3/5)      |
| `FakeLLMProvider` keeps pytest deterministic and free.             | I tested it by chatting. (they want automated tests)             |
| Owner-scoped `get_conversation` returns 404 for other users.       | We have authentication. (`X-User-Id` is a dev header, not OAuth) |
| Prisma migrates; SQLAlchemy writes messages at runtime.            | Prisma is the backend. (wrong)                                   |




## Honest limitations (better than getting caught)


| Limitation       | Accurate sentence                                                                                      |
| ---------------- | ------------------------------------------------------------------------------------------------------ |
| Auth             | Development identity via `X-User-Id`, not Clerk/OAuth yet.                                             |
| Streaming        | Request/response chat; loading indicator only.                                                         |
| History window   | Last 40 messages to the model; no conversation summarization.                                          |
| Failed generate  | User row can remain without an assistant if Gemini fails after persist.                                |
| Markdown         | `react-markdown` without `rehype-raw`; not a full HTML sanitizer pipeline.                             |
| Schema leftovers | Prisma still has unused User/Post starter models; chat uses Project/Conversation/Message.              |
| Frontend tests   | Composer trim is a small unit test; chat e2e is thin. Backend integration tests are the real coverage. |




## Live demo (about 90 seconds)

Open `/chat`. Show empty state. Ask “Explain embeddings in one paragraph.” Point at the loading bubble. When the reply lands, mention Markdown and that the message is now in Postgres. Refresh — history returns. Optionally stop the AI service and send again to show the safe error. Do not upload a PDF or ask for weather on this page if you are presenting Task 1.

## Re-read the night before



### Must-read files

- `apps/web/app/chat/page.tsx` — `mode=llm`
- `apps/web/features/chat/ChatPanel.tsx`
- `apps/web/lib/api.ts`
- `apps/ai-service/app/services/chat.py` — `_answer_with_llm`
- `apps/ai-service/app/providers/llm.py`
- `apps/ai-service/app/core/errors.py`
- `apps/ai-service/tests/integration/test_chat_api.py`



### Numbers to remember

- Max message: 8,000 characters
- History sent to Gemini: last 40 messages
- LLM timeout: 30,000 ms
- Send message HTTP: 201
- Model default: `gemini-flash-lite-latest`
- Status string: Generating response

---

Source: this repository’s Task 1 path as it exists after Tasks 2–5 were added. `/chat` still pins `llm`. `ChatService` also contains RAG and tools — skip those unless asked how the chatbot grew.
