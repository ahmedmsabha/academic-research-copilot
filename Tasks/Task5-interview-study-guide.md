# Task 5 interview study guide

Academic Research Copilot — complete AI assistant. This guide is the **AI product layer**: how chat, retrieval, tools, and prompting compose into one system, when each capability should fire, and how you keep a shipped assistant honest. Tasks 1–4 already built the pieces. Deep dives stay in those guides.

- LLM chat / context window → `Task1-interview-study-guide.md`
- RAG / embeddings / citations → `Task2-interview-study-guide.md`
- Agents / tool routing → `Task3-interview-study-guide.md`
- Prompt techniques / evaluation → `Task4-interview-study-guide.md`

| | |
|---|---|
| Demo page | `/workspace` |
| Mode | `auto` (same router as `/agent`) |
| Layout | History + chat + documents |
| AI contract | One generate adapter, one router, grounded citations, labeled tools |

## 30-second pitch — say this first

I shipped a complete research assistant that combines persistent LLM chat, project-scoped PDF RAG with filename/page citations, a constrained tool router, and a Prompt Lab. `/workspace` is the product surface: conversation history, document panel, and auto routing. The browser never talks to Gemini. Failures return user-safe problem details — never stack traces or hidden reasoning. Auth is still a development header, not OAuth; I will not pretend this is multi-tenant SaaS.

## What Task 5 is (and is not)

Task 5’s brief is: chat, history, tools, PDF upload, RAG, error handling, modern UI, **deploy**. It is **composition of AI capabilities**, not a new model.

| Requirement | AI meaning in this app | Do not claim |
|---|---|---|
| Chat + history | Multi-turn context window (last 40 turns) on the `llm` path | Infinite memory or summarization |
| Tool calling | Same single-route classifier as Task 3 | Native function calling, ReAct, multi-hop |
| PDF + RAG | Same grounded pipeline; citations from retrieval metadata | The model invents `Filename.pdf, p. 4` |
| Error handling | Provider / tool / retrieval failures stay user-safe | Dumping Gemini exceptions |
| Deploy | Same three-process shape; production **rejects fake LLM/embeddings** | Kubernetes or a client-side model |

**Name the architecture honestly.** Task 5 did not rewrite Tasks 1–4. One `ChatService`, one router, one `LLMProvider`. Focused demo pages still pin `mode` so earlier walkthroughs stay clean. Claiming “five separate AI apps glued at deploy time” is wrong. Claiming “production multi-tenant AI SaaS” is also wrong.

## AI concepts you must be able to explain

### One assistant, five generation modes

The model is not “the product.” The product is a **policy** for what the model is allowed to see and when a tool must run instead.

| User intent | Route | What the model sees | Evidence the UI must show |
|---|---|---|---|
| Ready PDF, question about the paper | `rag` | Excerpts + question only | `Filename.pdf, p. N` from metadata |
| PDF cannot answer | `rag` | (retrieval empty / weak) | Insufficient-evidence copy, **no** citations |
| `12 * (3 + 4)` | `calculator` | **Nothing** — AST, zero generate | 84, no sources |
| Paris weather / latest news | `weather` / `web_search` | Weather fields or search hits (untrusted) | External tool; web ≠ PDF citations |
| Vague general question, no docs | `llm` | System prompt + last 40 turns | No tools; parametric answer |
| Compare prompting strategies | Prompt Lab (not chat) | One question + one template | Five independent outputs |

Router order (must still know): **preferred → deterministic → LLM JSON → fallback**. Workspace does not pin a preferred route. Calculator extraction still wins if PDFs are ready. “What weather events does this paper describe?” stays `rag` because the document hint runs before the weather hint.

### Why composition beats a single mega-prompt

A mega-prompt that says “you have a calculator, weather, PDFs, and the web” invites the model to **fake** tool use, invent citations, or mix sources. We split capabilities:

- **Pinning** on `/chat` and `/rag` for demos (no silent tool use).
- **Deterministic tools** for exact / current facts.
- **Grounded RAG** when documents are the source of truth.
- **Prompt Lab** as a separate use case so comparison science does not share chat state.

FastAPI does not know which page you opened — it only sees `mode` and identity. Pages are UI policy. The service is the AI policy.

### Context is mode-specific

Do not say “the assistant always has full history and the PDF.”

| Mode | In the generate call |
|---|---|
| `llm` | Last 40 user/assistant turns |
| `rag` | Current question + retrieved excerpts — **not** the 40-turn window |
| `calculator` | No LLM call |
| `weather` | No LLM call (formatted tool result) |
| `web_search` | Provider hits + a summarizer instruction |
| Prompt Lab | One user message; no history, no chunks, no tools |

Conversation ids are **per page** (`sessionKind`). Project id is shared, so a PDF uploaded on `/rag` is searchable on `/workspace`. Opening `/chat` does not dump Task 1 turns into the workspace thread.

### Grounding and labeling as product rules

An interviewer for a “complete AI assistant” will probe honesty more than Docker.

1. **Never fabricate citations.** Labels come from retrieved chunk metadata.
2. **Document mode is strict.** Insufficient evidence > fluent trivia.
3. **External data is labeled.** Weather/search must not look like PDF sources.
4. **No hidden CoT.** Status is operational: “Searching uploaded documents,” “Using calculator.”
5. **Untrusted evidence.** PDFs and SERP snippets cannot grant tools or leak secrets.
6. **One tool per turn.** We do not let the model chain actions we cannot test.

### Production AI vs demo AI

Locally, `FakeLLMProvider` / `FakeEmbeddingProvider` keep CI free and deterministic. `Settings.validate_runtime()` when `APP_ENV=production`:

1. Reject `DEV_FAKE_LLM` / `DEV_FAKE_EMBEDDINGS`
2. Require `GEMINI_API_KEY`
3. Require `DATABASE_URL`

That is the AI-ops talking point: you must not ship a “working” assistant that is a stub. `/docs` is disabled in production. Secrets never go in `NEXT_PUBLIC_*`.

Compose is the local replica (web, FastAPI, Postgres+pgvector). Production is two apps on one Prisma database — say that if asked “how do you run it,” then return to the AI contract. Do not make infra the whole Task 5 answer.

### Errors an AI interviewer cares about

Three layers, same as the product:

| Layer | Example | User sees |
|---|---|---|
| Provider | Gemini/search timeout, empty completion | 503/504 problem details, no traceback |
| Tool domain | Div/0, missing city, empty SERP | HTTP 201 assistant bubble (`ToolError`) |
| Retrieval honesty | No ready docs / weak scores | 201, `route=rag`, empty citations, fixed sentence |

Unhandled exceptions become `500 INTERNAL_ERROR` with a generic sentence. We do not automatically retry `generate` (duplicate assistant turns). Optimistic user bubbles roll back on failure.

### History as a product feature, not a bigger window

Task 1 already persisted messages. Task 5 made history **visible and switchable**. The model still only sees 40 turns on the `llm` path. First user message retitles a default “New chat” (max 72 chars). Later messages do not rename it. New chat = empty thread, **same** project embeddings.

## Five pages, one AI backend

| Page | Mode | History | Documents | Why it still exists |
|---|---|---|---|---|
| `/workspace` | `auto` | yes | yes | Task 5 complete assistant |
| `/chat` | `llm` | no | no | Task 1: parametric only |
| `/rag` | `rag` | no | yes | Task 2: tools skipped |
| `/agent` | `auto` | no | no | Task 3: tools without a PDF panel |
| `/prompt-lab` | n/a | n/a | n/a | Task 4: **not** `ChatService` |

**The coexistence sentence.** One `ChatService.send_message`. Pages pin `mode` so a Task 1 demo cannot search the web, and a Task 2 demo cannot use the calculator. Workspace and Agent leave mode `auto`. Prompt Lab is a different use case.

## Drill these questions

### Is Task 5 just a new page?

No. `/workspace` is the product surface. Task 5 also made history switchable, rejected fake providers in production, and unified error/status UX. The **model call** did not change. The **policy for when the model runs** is what you demo.

### Walk me through a workspace session (AI path)

Bootstrap project + workspace conversation. Upload PDF → index → ready. Ask about the paper → `auto` → document hint or JSON → `rag` → retrieve → cite from metadata. **New chat.** Ask `12 * (3 + 4)` → calculator, Gemini not called, sidebar title updates. Ask Paris weather → labeled external, not a PDF citation.

### Why not one Next.js app that calls Gemini with a huge system prompt?

The key would leak. A huge prompt cannot reliably force tool use or faithful citations. The backend owns routing, retrieval filters, the calculator AST, and citation assembly. Same answer as Task 1; Task 5 did not reverse it.

### What happens if Gemini is down during a calculator question?

Nothing Gemini-shaped. Deterministic calculator never calls the LLM. If Gemini is down on `llm` or search summarization, the user sees `PROVIDER_UNAVAILABLE` / timeout — not a traceback.

### How do you keep Task 1–4 demos from breaking?

Pin `mode` on `/chat` and `/rag`. Separate conversation keys. Shared project so embeddings transfer. Prompt Lab stays off the chat router.

### How would you improve the *AI system* with another week?

Clerk (real identity for isolation), object storage, SSE token streaming, native function calling for multi-hop, hybrid search + reranker, conversation summarization for the 40-turn cap. Do not claim any of those are shipped.

## If they ask “was this AI-generated?”

**Do not deny it. Own the product contract.**

I used AI to move faster on boilerplate, but I can defend why the browser never holds the API key, why `/workspace` is composition not a rewrite, why citations are built in Python, why the calculator is an AST, why production rejects fake providers, and why Prompt Lab is not the workspace router. Then walk workspace → `select_route` → one capability.

### Phrases that sound like you built it

| Say | Avoid |
|---|---|
| One `ChatService`. Pages pin `mode`. Workspace is `auto` plus history and documents. | I connected five AI products with LangChain. |
| Constrained single-route tool calling — not a tools array, not ReAct. | Function calling. (which API?) |
| Citations come from retrieved chunk metadata. The model is not trusted to invent pages. | The LLM cites the PDF. |
| Calculator is `ast.parse`. Never `eval`. Zero tokens. | The AI does the math. |
| RAG is question + excerpts. LLM mode is a 40-turn window. They are different contexts. | The assistant always has the full chat and the PDF. |
| Production rejects fake LLM/embeddings. | We have production auth. / It’s fully multi-tenant. |

## Honest limitations (better than getting caught)

| Limitation | Accurate AI sentence |
|---|---|
| Not multi-tenant auth | Development `X-User-Id`. A public URL is shared-device scoped. |
| No token streaming | Loading status, then full assistant message. |
| Single tool per turn | Cannot search then calculate in one request. |
| RAG without chat memory | Grounded answers ignore the last 40 turns. |
| No hybrid / reranker | Single-stage cosine; overview queries bias to early pages. |
| Search default is HTML scrape | Fragile; Tavily if a key is set. |
| Prompt Lab cost is always `null` | No invented USD. |
| Local PDF storage | Not R2/Supabase in this deployment. |
| Live URL | Only claim it if README actually has the host. |

## Live demo (about 2–3 minutes)

Wide viewport. Follow `docs/demo-script.md`.

1. `/` — one product; **Open workspace**.
2. Three columns: Chats, chat, Documents.
3. Upload a small synthetic PDF. Wait until **Ready for search**.
4. Ask a question the PDF can answer → Searching uploaded documents → `Filename.pdf, p. N`. Say: citation from retrieval, not from the model.
5. **New chat.** `What is 12 * (3 + 4)?` → Using calculator → **84**. Say: zero Gemini calls.
6. Paris weather **or** `Search the web for retrieval-augmented generation` → External tool / Web sources — not document citations.
7. Optional 15s: `/prompt-lab` on the same research question; structured card is parsed fields, not raw JSON.
8. Close: one assistant, **grounded** documents, **labeled** tools, bounded history, fakes banned in production.

Do not apologize for AI-assisted implementation during the demo. Show the status chips and the citation footer — that is the product rule.

## Re-read the night before

### Must-read files

- `apps/web/app/workspace/page.tsx`
- `apps/web/features/chat/ChatPanel.tsx` + `session.ts`
- `apps/ai-service/app/services/chat.py` (retitle + route branches)
- `apps/ai-service/app/agent/router.py` (order only — details in Task 3)
- `apps/ai-service/app/core/config.py` `validate_runtime`
- `apps/ai-service/app/core/errors.py`
- `docs/demo-script.md` + `docs/architecture.md`

Skim, do not re-memorize: `rag/*`, `prompts/library.py` — the other study guides own those.

### Numbers and strings to remember

- Workspace loading: **Selecting a tool…**
- Calculator demo: `12 * (3 + 4)` → **84** (no LLM)
- History window: **40** messages (`llm` only)
- Chunk **800 / 150**, top_k **5**, distances **0.55 / 0.78**
- Embedding: `gemini-embedding-001`, **768** dims
- LLM: `gemini-flash-lite-latest`, timeout **30s**
- Isolation: **404** for other users
- Production rejects fake LLM/embeddings
- Problem body: `error.code` + `error.message` + `error.request_id`

---

Source: this repository after Tasks 1–5. `/workspace` is the complete assistant. If a follow-up goes deep on embeddings, routing, or prompting, switch to those guides instead of improvising.
