# Task 5 interview study guide

Academic Research Copilot — complete AI assistant. Memorize the pitch, then the unification story, then Docker/deploy and how errors stay user-safe. Tasks 1–4 already built chat, RAG, tools, and Prompt Lab. This page is how they become **one product** you can run, demo, and ship.

| | |
|---|---|
| Demo page | `/workspace` |
| Mode | `auto` (same router as `/agent`) |
| Layout | History + chat + documents |
| Deploy | Two Dokploy apps + Prisma Postgres |

Deep dives live in the earlier guides. Use this page to talk about **integration, production, and honesty**.

- Chat spine → `Task1-interview-study-guide.md`
- RAG / citations → `Task2-interview-study-guide.md`
- Tools / router → `Task3-interview-study-guide.md`
- Prompt Lab → `Task4-interview-study-guide.md`

## 30-second pitch — say this first

I shipped a complete research assistant that combines persistent chat, project-scoped PDF RAG with filename/page citations, a constrained tool router, and a Prompt Lab. The new surface is `/workspace`: conversation history, document panel, and auto routing in one UI. The browser never talks to Gemini. Next.js proxies `/api/v1` to FastAPI. Docker Compose runs the same three-process shape locally. Production is two Dokploy apps plus Prisma Postgres. Failures return RFC 7807-style `{ error: { code, message, request_id } }` — never stack traces. Auth is still a development `X-User-Id` header, not OAuth.

## What Task 5 is (and is not)

Task 5’s brief is: chat, history, tools, PDF upload, RAG, error handling, modern UI, **deploy**. It is an integration and production task, not a new model capability.

| Requirement | What this app does | Do not claim in Task 5 |
|---|---|---|
| Chat interface | Shared `ChatPanel` + composer on `/workspace` | A new chat stack separate from Task 1 |
| Conversation history | Sidebar lists project chats; first message retitles; last 40 turns go to Gemini | Token-budget summarization, streaming replay, or deleting chats |
| Tool calling | Same `select_route` as Task 3, `mode=auto` | Native Gemini/OpenAI function calling, ReAct, or multi-hop |
| PDF upload | Same `DocumentPanel` as Task 2, shown on the right | OCR, R2/Supabase storage, or scanning image-only PDFs |
| RAG | Same grounded pipeline; citations from retrieval metadata | The model invents `Filename.pdf, p. 4` |
| Error handling | Domain `AppError` → problem details; proxy maps network failures | Dumping Gemini/SQL exceptions to the UI |
| Modern UI | Home + AppNav + three-column workspace | A design system library or mobile native app |
| Deploy online | Compose locally; Dokploy web + AI + Prisma Postgres | Kubernetes, serverless LLM on the client, or that a live URL exists if README still says “add after deploy” |

**Name the architecture honestly.** Task 5 did not rewrite Tasks 1–4. It composed them: one `ChatService`, one router, one Prisma schema, one proxy. Focused demo pages still exist so you can pin `mode=llm` / `rag` / `auto` without breaking earlier walkthroughs. Claiming “I built five separate apps and glued them at deploy time” is wrong. Claiming “this is production multi-tenant SaaS” is also wrong.

## Five pages, one backend

Every chat page is `ChatPanel` with different props. FastAPI does not know which page you opened — it only sees `mode` and `X-User-Id`.

| Page | Mode | History | Documents | Session key | Why it still exists |
|---|---|---|---|---|---|
| `/` | — | — | — | — | Product overview; links into each capability |
| `/workspace` | `auto` | yes | yes | `arc.conversationId.workspace` | Task 5 complete assistant |
| `/chat` | `llm` | no | no | `arc.conversationId.chat` | Task 1: “what is 2+2?” must not hit the calculator |
| `/rag` | `rag` | no | yes | `arc.conversationId.rag` | Task 2: tools skipped; documents always in view |
| `/agent` | `auto` | no | no | `arc.conversationId.agent` | Task 3: tools without a PDF panel |
| `/prompt-lab` | n/a | n/a | n/a | Prompt Lab session | Task 4: **not** `ChatService` |

Project id is shared (`arc.projectId`). Conversation ids are **not**. Opening `/chat` then `/workspace` does not dump Task 1 turns into the workspace thread. Vitest covers that in `tests/conversation-title.test.ts`.

**The coexistence sentence.** One `ChatService.send_message`. Pages pin `mode` so a Task 1 demo cannot search the web, and a Task 2 demo cannot use the calculator. Workspace and Agent leave mode `auto`. Prompt Lab is a different use case (`PromptLabService`) — no history, no RAG chunks, no tools.

## Draw this request path

Browser never talks to Gemini, pgvector, Open-Meteo, or DuckDuckGo.

```text
Browser  →  Next.js (apps/web)
                │  same-origin /api/v1
                │  server-only API_BASE_URL
                ▼
         FastAPI (apps/ai-service)
                │
                ├─ Prisma Postgres + pgvector
                ├─ local PDF files
                └─ Gemini / Open-Meteo / search providers
```

### Workspace send path

| Step | Layer | File | What happens |
|---|---|---|---|
| 1 | UI | `app/workspace/page.tsx` | `ChatPanel` with `mode=auto`, `showHistory`, `showDocuments`, `sessionKind="workspace"`. |
| 2 | Bootstrap | `ChatPanel.tsx` | Load/create project. List conversations. Restore saved chat or create “New chat”. `GET` messages. |
| 3 | Client | `lib/api.ts` | POST `{ content, mode: "auto" }` with `X-User-Id` from localStorage. Browser origin is `""` (same-origin). |
| 4 | Proxy | `app/api/v1/[...path]/route.ts` | Forwards to FastAPI. 60s `maxDuration`. Reads **runtime** `API_BASE_URL` so Dokploy env works without a rebuild. |
| 5 | Auth | `core/security.py` | Missing/invalid header → `401 UNAUTHORIZED`. |
| 6 | Service | `services/chat.py` `send_message` | Persist user turn. Maybe retitle. `select_route`. Exactly one branch. |
| 7 | Persist | `postgres_store.py` | Assistant message stores `route`, `status`, provider, model, citations or `web_sources`. |
| 8 | UI | `MessageList.tsx` + sidebar | Status chip. Document vs web footers. Sidebar refresh so the new title appears. |

### Three-column layout

`ChatPanel` picks a grid only when history or documents are on:

```text
lg:grid-cols-[minmax(220px,260px)_minmax(0,1fr)_minmax(260px,320px)]
         Chats                          Chat                      Documents
```

Narrow viewports stack. `/chat` is a single column. `/rag` is chat + documents. `/agent` is chat only.

## Conversation history — what Task 5 actually added

Task 1 already persisted messages. Task 5 made history **visible and switchable**.

| Piece | Behavior |
|---|---|
| List | `GET /api/v1/projects/{id}/conversations` — owner-scoped, newest first |
| Create | `POST` `{ title: "New chat" }`. Sidebar button “New chat”, disabled while `creating`. |
| Switch | `GET /conversations/{id}/messages`. Optimistic UI is not used here — wait for history. |
| Retitle | First user message: if title is in `DEFAULT_CONVERSATION_TITLES` (`New chat`, `Research chat`, `General chat`, `Document chat`, `Agent chat`), replace with compacted question, max 72 chars + ellipsis. |
| Gemini window | Last **40** messages (`MAX_HISTORY_MESSAGES`). Not the whole project. |
| 404 conversation | Bootstrap creates a fresh chat instead of crashing the workspace. |

`should_retitle` is strict: after “What is 12 * (3 + 4)?” becomes the title, later messages do **not** rename it. `test_first_message_retitles_default_conversation` and `test_should_retitle_only_defaults` cover this.

## How Tasks 1–4 show up in the workspace

Do not recitation-dump every pipeline unless asked. Point at the workspace, then name the route.

| User does | Route | Status they should see | Evidence |
|---|---|---|---|
| Upload PDF, wait, ask about the paper | `rag` | Searching uploaded documents | `Filename.pdf, p. N` in Document sources |
| Ask something the PDF cannot answer | `rag` | Searching uploaded documents | Honest insufficient-evidence copy, empty citations |
| `What is 12 * (3 + 4)?` | `calculator` | Using calculator | **84**. No citations. Gemini not called. |
| `What's the weather in Paris?` | `weather` | Checking weather · External tool | Labeled prose. Not a PDF citation. |
| `Search the web for retrieval-augmented generation` | `web_search` | Searching the web · External tool | Web sources (external) |
| Vague general question, no docs | `llm` | Generating response (status chip hidden for `llm`) | Last 40 turns, no tools |
| Open `/prompt-lab` | n/a | Comparing prompting strategies | Five independent templates |

Router order (must still know): **preferred → deterministic → LLM JSON → fallback**. Workspace does not pin a preferred route. Calculator extraction still wins even if PDFs are ready. “What weather events does this paper describe?” stays `rag` because the document hint runs before the weather hint.

## Error handling — first-class Task 5 requirement

The brief lists error handling next to RAG and tools. Interviewers will ask where failures go. There are **three layers**.

### 1. Domain errors (`core/errors.py`)

`AppError` carries `code`, `message`, `status_code`. Handlers wrap every response as:

```json
{
  "error": {
    "code": "DOCUMENT_TOO_LARGE",
    "message": "The uploaded file exceeds the size limit.",
    "request_id": "…"
  }
}
```

Unhandled exceptions become `500 INTERNAL_ERROR` with a generic sentence. `_ = exc` — the traceback stays in logs, not the body. `/docs` is **disabled** when `APP_ENV=production`.

| Code | HTTP | Typical cause |
|---|---|---|
| `UNAUTHORIZED` | 401 | Missing `X-User-Id` |
| `FORBIDDEN` | 403 | `AuthorizationError` |
| `NOT_FOUND` | 404 | Other user’s project/conversation (isolation policy: 404, not 403) |
| `VALIDATION_ERROR` | 400 / 422 | Blank message, Pydantic |
| `UNSUPPORTED_DOCUMENT` | 415 | Not a PDF / bad magic bytes |
| `DOCUMENT_TOO_LARGE` | 413 | Over `MAX_UPLOAD_BYTES` (20 MiB) |
| `DOCUMENT_LIMIT` | 409 | 20 PDFs per project |
| `DOCUMENT_NOT_READY` | 409 | Used when a specific doc is still indexing |
| `DOCUMENT_PROCESSING_ERROR` | 422 | Extract/index failed (user can retry) |
| `PROVIDER_UNAVAILABLE` | 503 | Gemini / search / weather down |
| `PROVIDER_TIMEOUT` | 504 | Upstream exceeded timeout |
| `PROVIDER_CONFIG_ERROR` | 503 | Tool not wired |
| `INTERNAL_ERROR` | 500 | Unexpected — no exception text |

### 2. In-band tool failures vs HTTP failures

**Do not say every failure is a 4xx.** After the user message is stored, calculator/weather/search domain mistakes reply as an **assistant bubble** (HTTP 201): division by zero, missing city, empty search. Provider timeouts are **not** in-band — they use the global mapper (`504 PROVIDER_TIMEOUT`). Same distinction as Task 3.

RAG “no ready documents” and “insufficient evidence” are also 201 assistant messages with `route=rag`, not thrown `InsufficientEvidenceError` on the happy path (that class exists; the chat flow returns honest copy instead of failing the request).

### 3. Frontend + proxy

| Surface | Behavior |
|---|---|
| `ApiError` | Parses `{ error: { code, message, request_id } }`. Fallback copy if body is not JSON. |
| Network throw | `NETWORK_ERROR` — “Unable to reach the AI service…” |
| Composer | Trim. Block blank. Enter sends, Shift+Enter newline. Disabled while sending. |
| ChatPanel | `role="alert"` banner. Optimistic user bubble **removed** on failure. |
| Sidebar | Separate `historyError` so a list failure does not wipe the composer. |
| Documents | Upload type/size feedback; indexing `failed` + Retry; delete confirmation. |
| Proxy | AI unreachable → `502 NETWORK_ERROR`. Missing `API_BASE_URL` → `500 CONFIG_ERROR`. If `API_BASE_URL` points at the **web** host, reject — that would loop. |
| `normalizeApiBaseUrl` | Strips accidental `/api`, `/health`, `/api/v1` suffixes people paste from Dokploy. |

Loading copy on workspace: **Selecting a tool…** (`LOADING_STATUS.auto`) until the response returns. Then the real `status` from the API. Never stream hidden reasoning.

## Modern UI — what to point at

Not a component library pitch. Say what the UI **guarantees**.

| Rule | Where |
|---|---|
| Empty / loading / success / error / disabled-while-submit | Chat, history, documents, Prompt Lab |
| Status is operational, not CoT | `routeStatus.ts`: Searching uploaded documents, Using calculator, … |
| External vs document evidence | Two footers. `isExternalRoute` adds “ · External tool” |
| Citations only from API metadata | `MessageList` renders `citation.label` — it does not parse the prose |
| Keyboard | Enter send, Shift+Enter newline, labeled textarea (`sr-only` “Message”) |
| Nav | `AppNav` with `aria-current="page"` |
| Typography | Fraunces + Source Sans 3, Tailwind tokens (`ink`, `accent`, `line`) |

Home (`/`) is the portfolio landing: “Open workspace” + capability cards. Screenshot target: `docs/screenshots/task5-landing.png`.

## Docker Compose — local production shape

File: `docker-compose.yml`. This is the “how do you run it?” answer.

```text
postgres (pgvector/pgvector:pg16)
    → migrate (Dockerfile.migrate: prisma migrate deploy)
        → ai-service (FastAPI :8000, health /health)
            → web (Next.js :3000)
```

| Detail | Why it matters |
|---|---|
| Named volumes `postgres_data` and `uploads` | DB and PDFs survive `compose down` (not `--volumes`) |
| Compose **overrides** `DATABASE_URL` to `postgresql://copilot:copilot@postgres:5432/academic_copilot` | Do not bake secrets in the YAML |
| `web` `API_BASE_URL=http://ai-service:8000` | Container DNS. Browser still calls same-origin `/api/v1`. |
| `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` | Build-time fallback only; browser in Compose uses the proxy |
| `ai-service` waits for `migrate` `service_completed_successfully` | Schema exists before FastAPI talks to Postgres |
| Healthchecks | Postgres `pg_isready`; AI `curl /health`; web wget `/` |
| `APP_ENV=development` in Compose | Fake providers still allowed if you set them; production rejects them |

Web image: multi-stage Node 22 Alpine. `DOCKER_BUILD=1` enables Next `output: "standalone"`. Dummy `DATABASE_URL` at **generate** time — the build does not connect. AI image: Python 3.12-slim, uid 1000, `uvicorn --host 0.0.0.0`.

Commands to recite:

```bash
cp .env.example .env   # set GEMINI_API_KEY
docker compose up --build
# http://localhost:3000
```

CI (`.github/workflows/ci.yml`): on push/PR, `ruff` + `pytest` for the AI service; `lint` + `typecheck` + `vitest` for web. Default tests use fakes — no live Gemini.

## Production deploy — Dokploy, two apps

Source of truth: `docs/deploy.md`. Draw this, not “I put Compose on the VPS.”

```text
Browser  →  Dokploy “web” (apps/web :3000)
                │  API_BASE_URL = https://<ai-domain>
                ▼
         Dokploy “ai” (apps/ai-service :8000)
                └─ same Prisma Postgres (pgvector)
```

| Rule | Accurate sentence |
|---|---|
| Two Applications, not one Compose stack on the VPS | Avoid a second Postgres. Keep the existing Prisma `DATABASE_URL`. |
| Build type Dockerfile, path `apps/web` or `apps/ai-service` | Dockerfile field is `Dockerfile` relative to that path — do not double it. |
| AI env | `APP_ENV=production`, `GEMINI_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `STORAGE_LOCAL_ROOT=/data/uploads` |
| Volume `ai-uploads` → `/data/uploads` | PDFs survive redeploy. Root-owned mounts cause permission errors. |
| Web env | `API_BASE_URL=https://<ai-origin>` — **no** `/api`, `/health`, or trailing slash |
| Runtime vs build | Proxy reads env at runtime. Redeploy web after changing `API_BASE_URL`. Full rebuild only if proxy code changed. |
| Smoke | `curl /health` → `{"status":"ok","service":"ai-service"}`. `GET /api/v1/projects` without header → 401 means the API is up. |
| Migrations | `npx prisma migrate deploy` against **that** database from your laptop (or a one-shot job). Compose’s `migrate` service is local only. |

`Settings.validate_runtime()` when `APP_ENV=production`:

1. Reject `DEV_FAKE_LLM` / `DEV_FAKE_EMBEDDINGS`
2. Require `GEMINI_API_KEY` (or `LLM_API_KEY`)
3. Require `DATABASE_URL`

`test_production_settings_reject_fake_providers` and `test_production_settings_require_database` exist so you can name a test.

**Live URL.** README still says add after deploy. If you have not finished Dokploy, say so. Do not invent a production hostname in the interview.

## Secrets and identity

| Stay server-side | Never |
|---|---|
| `GEMINI_API_KEY`, `DATABASE_URL`, `WEB_SEARCH_API_KEY` | `NEXT_PUBLIC_*` for those values |
| `API_BASE_URL` on the web **container** | Putting the AI origin only in a public client bundle as the way secrets are “hidden” — the key still must not be public |
| Storage keys generated as `{userId}/{projectId}/{documentId}.pdf` | Unsanitized filename as object key |

Identity is `X-User-Id` from `localStorage` (`arc.userId`, created as `dev-user-` + 8 hex chars). Treat a public demo as **shared-device scoped**, not multi-tenant production auth. Isolation queries still filter `owner_user_id` + `project_id`. Another user’s id gets 404.

## Portfolio deliverables (the rest of the brief)

Task 5 is graded as a **shipped product**, not only code.

| Deliverable | Where it lives |
|---|---|
| GitHub | https://github.com/ahmedmsabha/academic-research-copilot |
| README | Overview, Task 5 objectives, Docker + separate-process setup, routes, tests, limitations |
| Architecture | `docs/architecture.md` + `docs/architecture-diagram.svg` |
| API | `docs/api.md` — modes, statuses, error shape, upload limits |
| Deploy | `docs/deploy.md` |
| Demo script | `docs/demo-script.md` — 2–3 minutes on `/workspace` |
| Presentation | `docs/presentation.md` — 5–7 minute outline |
| LinkedIn draft | `docs/linkedin-task5-draft.md` |
| Screenshots | `docs/screenshots/task5-*.png` (capture if missing) |
| CI | `.github/workflows/ci.yml` |

If screenshots or the live URL are not in the repo yet, say “the script and paths are ready; I still need to capture/host them” — that is better than pointing at files that do not exist.

## Drill these questions

### Is Task 5 just a new page?

No. `/workspace` is the product surface, but Task 5 also added visible history, Docker health/migrate, production startup checks, CI, deploy docs, and a landing page. The model call did not change. Integration did.

### Walk me through a workspace session

Bootstrap loads `arc.projectId` and `arc.conversationId.workspace`. Missing project → `POST /projects`. History `GET` conversations; if the saved id is gone, take the newest or create “New chat”. User asks about a ready PDF → `mode=auto` → document hint or LLM JSON → `rag` → retrieve → cite from metadata. User clicks New chat → empty thread, same project, documents still indexed. First calculator question retitles that thread to `What is 12 * (3 + 4)?`.

### Why not one Next.js app that calls Gemini?

`GEMINI_API_KEY` would leak. The backend also owns routing, retrieval filters, calculator AST, and error mapping. The frontend is rendering + a typed client. Same answer as Task 1; Task 5 did not reverse it.

### Why two Dokploy apps instead of Compose in production?

Compose is the local replica. Production already has Prisma Postgres. A second Postgres on the VPS would split migrations and embeddings. Two apps share one `DATABASE_URL`. The web container talks to the AI origin over `API_BASE_URL`; the browser never needs that origin if the proxy is working.

### Why is `API_BASE_URL` runtime, not a Docker build-arg?

Dokploy injects Environment after the image exists. `readUpstreamApiBaseUrl()` reads `process.env` on each proxy request. `NEXT_PUBLIC_*` is a fallback and can be baked; do not rely on it for the production AI origin. After changing the env, redeploy web.

### How do you keep Task 1–4 demos from breaking?

Pin `mode` on `/chat` and `/rag`. Separate `sessionKind` keys. Shared project so a PDF uploaded on `/rag` is searchable on `/workspace` (same `owner_user_id` + project). Prompt Lab stays off the chat router.

### What happens if Gemini is down during a calculator question?

Nothing Gemini-shaped. Deterministic calculator never calls the LLM. `fake_llm.calls` does not increase in `test_calculator_route`. If Gemini is down on a general `llm` or `web_search` summary, the user sees `PROVIDER_UNAVAILABLE` / timeout — not a Python traceback.

### How would you improve this with another week?

Honest next steps: Clerk or similar auth, object storage (R2) instead of a local volume, SSE streaming, native function calling for multi-hop, OCR, delete-conversation in the sidebar. Do not claim any of those are shipped.

## If they ask “was this AI-generated?”

**Do not deny it. Own the product contract.**

I used AI to move faster on boilerplate, but I can defend why the browser never holds the API key, why `/workspace` is composition not a rewrite, why history keys are split per page, why citations are built in Python, why the calculator is an AST, why production rejects fake providers, and why Dokploy is two apps on one Prisma database. Then walk workspace → proxy → `select_route` → one tool. That is what they are testing — comprehension, not who typed `ChatPanel.tsx`.

### Phrases that sound like you built it

| Say | Avoid |
|---|---|
| One FastAPI `ChatService`. Pages pin `mode`. Workspace is `auto` plus history and documents. | I connected five AI products with an orchestration framework. |
| Constrained single-route tool calling — not a tools array, not ReAct. | Function calling. (which API? parallel? loop?) |
| Citations come from retrieved chunk metadata. The model is not trusted to invent pages. | The LLM cites the PDF. |
| Calculator is `ast.parse` with a whitelist. Never `eval`. | The AI does the math. |
| Errors are `{ error: { code, message, request_id } }`. Tool mistakes can be HTTP 201. Timeouts are 504. | We have try/catch. |
| Compose is local. Production is Dokploy web + AI + existing Prisma Postgres. | We deployed Docker Compose to prod. / It’s on Vercel with the key in the browser. |
| Auth is `X-User-Id` for the demo. Isolation is still owner-scoped 404. | We have production auth. |
| Prompt Lab is a separate service and page. It is not the workspace router. | The agent picks the best prompt. |

## Honest limitations (better than getting caught)

| Limitation | Accurate sentence |
|---|---|
| Not multi-tenant auth | Development header. A public URL is shared-device scoped. |
| Local filesystem PDFs | `STORAGE_PROVIDER=local`. Volume on Dokploy. R2/Supabase is a later upgrade. |
| No OCR | Image-only PDFs fail indexing honestly. |
| No token streaming | Loading status, then full assistant message. |
| Single tool per turn | Cannot search then calculate in one request. |
| Search default is DuckDuckGo HTML | Fragile; Tavily if `WEB_SEARCH_API_KEY` is set. Gemini search is last because it shares chat quota. |
| Prompt Lab cost is always `null` | Tokens only when Gemini returns usage. No invented USD. |
| Starter Prisma `User`/`Post` models | Leftover from init; not used by the copilot domain. |
| Live URL | Only claim it if README/`docs/deploy.md` actually has the host. |
| Frontend e2e | Vitest covers composer, citations, session keys, Prompt Lab labels. Highest-value journeys are documented; Playwright may be thin. |

## Live demo (about 2–3 minutes)

Follow `docs/demo-script.md`. Wide viewport.

1. `/` — one product; click **Open workspace**.
2. Point at three columns: Chats, chat, Documents.
3. Upload a small synthetic PDF. Wait until **Ready for search**.
4. Ask a question the PDF can answer → Searching uploaded documents → `Filename.pdf, p. N`.
5. **New chat**. Ask `What is 12 * (3 + 4)?` → Using calculator → **84**. Sidebar title updates.
6. Ask Paris weather **or** `Search the web for retrieval-augmented generation` → External tool / Web sources (external), not document citations.
7. Optional 15s: `/prompt-lab` on the same research question; structured card shows parsed fields, not raw JSON.
8. Close: one assistant, grounded documents, labeled tools, history, Docker path. If not hosted yet, say Compose runs the same images you would deploy.

Do not apologize for AI-assisted implementation during the demo. Show the status chips and the citation footer — that is the product rule, not the generator.

## Re-read the night before

### Must-read files

- `apps/web/app/workspace/page.tsx`
- `apps/web/app/page.tsx` + `components/AppNav.tsx`
- `apps/web/features/chat/ChatPanel.tsx`
- `apps/web/features/chat/session.ts`
- `apps/web/features/chat/ConversationSidebar.tsx`
- `apps/web/app/api/v1/[...path]/route.ts` + `lib/api-base-url.ts`
- `apps/ai-service/app/services/chat.py` (retitle + route branches)
- `apps/ai-service/app/services/conversation_titles.py`
- `apps/ai-service/app/core/errors.py`
- `apps/ai-service/app/core/config.py` `validate_runtime`
- `apps/ai-service/app/main.py`
- `docker-compose.yml`
- `apps/web/Dockerfile` + `apps/ai-service/Dockerfile`
- `docs/deploy.md` + `docs/demo-script.md` + `docs/architecture.md`
- `docs/presentation.md` + `docs/linkedin-task5-draft.md`

Skim, do not re-memorize: `agent/router.py`, `rag/*`, `prompts/library.py` — the other study guides own those.

### Numbers and strings to remember

- Workspace loading: **Selecting a tool…**
- Calculator demo: `12 * (3 + 4)` → **84**
- History window: **40** messages
- Retitle max: **72** characters
- Upload: PDF, **20 MiB**, **20** docs/project, chunk **800 / 150**, top_k **5**, distances **0.55 / 0.78**
- Embedding: `gemini-embedding-001`, **768** dims
- LLM: `gemini-flash-lite-latest`, timeout **30s**
- Proxy `maxDuration`: **60s**
- Ports: web **3000**, AI **8000**
- Production rejects fake LLM/embeddings
- Isolation: **404** for other users
- Problem body: `error.code` + `error.message` + `error.request_id`
- GitHub: `ahmedmsabha/academic-research-copilot`

---

Source: this repository after Tasks 1–5. `/workspace` is the complete assistant. `/chat`, `/rag`, `/agent`, and `/prompt-lab` remain focused demos. If a follow-up goes deep on RAG, tools, or Prompt Lab, switch to those guides instead of improvising.
