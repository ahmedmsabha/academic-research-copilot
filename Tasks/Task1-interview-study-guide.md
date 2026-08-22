# Task 1 interview study guide

Academic Research Copilot — first LLM chatbot. This guide is the **AI conversation layer**: how a language model is called, what context it sees, why it hallucinates, and how you keep secrets and errors user-safe. Later tasks (RAG, tools, Prompt Lab) sit on this same generate path; they are not Task 1.

## 30-second pitch — say this first

I built a research chatbot around a Large Language Model. The browser never talks to Gemini. FastAPI owns the generate call, maps chat roles into Gemini contents, sends a separate system instruction, and caps history at the last 40 turns so the context window stays bounded. Secrets stay on the server. Tests use a fake LLM so CI never hits a paid API.


|                  |                           |
| ---------------- | ------------------------- |
| Task 1 demo page | `/chat`                   |
| Pinned route     | `mode=llm`                |
| Model            | Gemini via `google-genai` |
| Context window   | Last 40 user/assistant turns |


## What Task 1 is (and is not)


| AI requirement       | What this app does                                            | Do not claim in Task 1                                 |
| -------------------- | ------------------------------------------------------------- | ------------------------------------------------------ |
| Integrate an LLM API | `GeminiLLMProvider` wraps generate; system prompt + history   | Browser fetch to Google; OpenAI/Claude SDKs            |
| Conversational AI    | Multi-turn messages persisted; last 40 sent as model context  | Token-budget summarization, memory, or streaming replay |
| Grounding later      | Task 1 is **parametric** knowledge only — the model’s weights | Document retrieval, citations, or tools                |
| Safe generation      | Empty model text is treated as provider failure, not an answer | Persisting blank assistant turns                       |
| Testable LLM         | `LLMProvider` Protocol + `FakeLLMProvider`                    | Live Gemini in pytest                                  |




## AI concepts you must be able to explain

### What an LLM actually does

A Large Language Model predicts the next token given a prompt. It does **not** look up your Postgres rows, run Python, or “know” the user’s PDF. Everything it can use in Task 1 is:

1. **Parametric knowledge** — facts compressed into weights during pretraining (can be stale or wrong).
2. **In-context tokens** — the system instruction plus the last 40 chat turns you send on this request.

If a fact is not in those two places, a fluent answer is still a guess. That is why Task 2 adds retrieval and Task 3 adds tools.

### Tokens, context window, and history

Gemini (and every chat API) has a finite **context window**. We do not send the whole `messages` table.

| Kind                 | Where                                                    | AI purpose                                                                             |
| -------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Durable messages     | Postgres `messages`                                      | Product history. Survive refresh. Not automatically in the model.                      |
| Model context        | `Settings.max_history_messages = 40`                     | Only the last 40 user/assistant turns become Gemini contents. Older rows stay in DB.   |
| Session pointers     | localStorage ids                                         | Which conversation to reopen. Not the transcript and not tokens.                       |


**Say this:** persistence and context are different. The database can hold 400 turns; the model only sees 40. That is a sliding window, not summarization. If they ask how to scale, say: summarize older turns into a short memory, or retrieve relevant past turns — neither is shipped.

### Roles: system vs user vs model

Interviewers love the mapping because it shows you understand the API, not just “I called Gemini.”


| App concept              | Gemini API fact                                                |
| ------------------------ | -------------------------------------------------------------- |
| `role: user`             | Stays `user`                                                   |
| `role: assistant`        | Mapped to `role: model` in `history_to_gemini_contents`        |
| System prompt            | `GenerateContentConfig.system_instruction` — **not** a chat turn |
| Empty / whitespace turns | Skipped so the model does not get blank parts                  |
| Empty model text         | `ProviderUnavailableError` — do not persist an empty assistant |


System instruction in Task 1: Academic Research Copilot for students/researchers. Be clear. Do not invent citations or claim private documents unless they are already in the conversation. (RAG has a stricter grounded prompt — that is Task 2.)

### Why the model is never called from the browser

`GEMINI_API_KEY` would leak in `NEXT_PUBLIC_*` / the Network tab. The backend also:

- Enforces length limits (8,000 characters) so a single prompt cannot blow the window.
- Scopes history to the conversation owner.
- Classifies provider failures (timeout, 429, bad key, empty text) into safe codes.

The frontend only calls `/api/v1`. Same rule for embeddings and tools later.

### Why `LLMProvider` is a Protocol

Generation is I/O behind a stable interface. `GeminiLLMProvider` wraps `google-genai`. `FakeLLMProvider` records calls and returns a fixed string. Pytest never spends quota or waits on a nondeterministic model. Same `ChatService` in prod and tests — only the adapter changes. This is how you unit-test AI products without paying for tokens.

### Temperature, determinism, and why tests fake the model

Live Gemini is **stochastic**: the same prompt can yield different wording. CI cannot assert exact prose. We assert **contracts** instead: HTTP 201, `route=llm`, two messages in history, and that a boom provider becomes 503 with no traceback. Role mapping is a pure unit test.

### Hallucination (Task 1 version)

Without documents, the model will still answer confidently. Task 1 mitigates lightly: the system prompt forbids invented citations. It does **not** stop the model from using training-data trivia. Strict grounding is Task 2. Do not claim Task 1 is “hallucination-proof.”

## Request path (so you can still whiteboard it)

Browser `ChatPanel` → typed client → Next.js proxy → FastAPI `POST /conversations/{id}/messages` → `ChatService.send_message` → `select_route(preferred=llm)` → `_answer_with_llm` → map history to Gemini contents → `generate` → persist assistant message.

`/chat` pins `mode=llm` so the later agent router cannot pick calculator, weather, search, or RAG. `source=preferred`. The interviewer sees a plain chatbot.

## Error handling — AI-provider codes


| HTTP | code                    | When (AI-shaped)                                  |
| ---- | ----------------------- | ------------------------------------------------- |
| 401  | `UNAUTHORIZED`          | Missing identity header                           |
| 404  | `NOT_FOUND`             | Conversation not owned (404, not 403 — no leak)   |
| 422  | `VALIDATION_ERROR`      | Blank / oversized prompt                          |
| 503  | `PROVIDER_UNAVAILABLE`  | Gemini down, empty completion, rate limit         |
| 503  | `PROVIDER_CONFIG_ERROR` | Missing key, rejected credentials, bad model name |
| 504  | `PROVIDER_TIMEOUT`      | Deadline (`LLM_TIMEOUT_MS = 30000`)               |


We do **not** automatically retry `generate`. A retry would duplicate assistant messages in the conversation. Own the known gap: the user row is committed before Gemini runs; if generate fails, that turn stays without a reply.

## Drill these questions



### What is an LLM, in one minute?

A neural network trained to predict the next token. At inference we send a system instruction plus recent turns. The completion is sampled from a probability distribution over tokens — it is not a database query. Fluency is not evidence.

### Walk me through sending a message (AI path)

The client POSTs `{ content, mode: "llm" }`. FastAPI stores the user turn, loads the last 40 user/assistant messages, maps assistant → model, attaches `system_instruction`, and calls Gemini with a 30s timeout. The assistant text is persisted with `route=llm`. The UI never sees the API key or the raw SDK exception.

### Why not put the API key in Next.js?

Anything in `NEXT_PUBLIC_*` or a client bundle is visible. Even a Next server action that only proxies Gemini would skip conversation ownership, history capping, and centralized provider-error mapping. The AI service is the only process allowed to talk to model providers.

### How do you test an LLM without paying Google?

`FakeLLMProvider` implements the same Protocol. Integration tests assert status, route, and history shape. `history_to_gemini_contents` is a unit test: assistant → model, blanks skipped. We never call a paid, nondeterministic API in default CI.

### How is conversation history maintained for the *model*?

Postgres holds the durable log. For generation, `ChatService` slices `history[-40:]` and only includes user/assistant roles. Gemini contents use user/model. localStorage only stores which conversation id to reopen.

### What happens if Gemini is down or returns empty text?

SDK exceptions and empty completions are classified in `_map_provider_exception`. The API returns a problem-detail JSON. The UI shows a safe message and rolls back the optimistic bubble. Empty text is a provider failure, not a valid answer.

### Is this streaming?

No. One JSON response after generation. Loading is a status bubble (“Generating response…”), not tokens. If asked what you would add: SSE with user-safe status then tokens, cancel on browser abort, persist only the final assembled assistant text. Never stream hidden reasoning.

### Context window vs summarization — which did you ship?

A sliding window of 40 messages. No map-reduce summary, no “memory” store. Tradeoff: cheap and predictable; the model forgets older turns even though they are still in the UI after a refresh of the full GET list.

### How does this relate to Task 2–5?

Same `generate` adapter. `/chat` keeps `mode=llm` (parametric only). `/rag` adds retrieved chunks as **non-parametric** context. `/agent` and `/workspace` let a router pick tools. Prompt Lab reuses `LLMProvider` with different system instructions. Task 1 is the spine: roles, history window, provider adapter, safe errors.

## If they ask “was this AI-generated?”

Do not deny it. Own the **LLM contract**.

I used AI to move faster on boilerplate, but I can defend why the browser never calls Gemini, why assistant maps to model, why history is a 40-turn window not a dump of the table, why empty completions are failures, and why tests fake the provider. Then walk ChatComposer → `GeminiLLMProvider.generate`. That is what they are testing — comprehension of the model boundary.

### Phrases that sound like you built it


| Say                                                                | Avoid                                                            |
| ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| The model only sees a system instruction plus the last 40 turns.   | The chatbot uses Gemini. (too vague)                             |
| Assistant role is mapped to Gemini `model`; system is not a turn.  | We send the whole chat as one string.                            |
| `FakeLLMProvider` keeps pytest deterministic and free.             | I tested it by chatting.                                         |
| Task 1 is parametric knowledge only; RAG is Task 2.                | It knows my documents. (not on `/chat`)                          |
| We do not retry generate — that would duplicate assistant turns.   | If it fails we just call the API again.                          |




## Honest limitations (better than getting caught)


| Limitation       | Accurate AI sentence                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| Hallucination    | No retrieval. The model can invent facts that sound academic.                              |
| History window   | Last 40 messages to the model; no conversation summarization or long-term memory.          |
| Streaming        | Request/response generation; no token stream.                                              |
| Failed generate  | User row can remain without an assistant if Gemini fails after persist.                    |
| Auth             | Development identity via `X-User-Id`, not production OAuth.                                |
| Model default    | `gemini-flash-lite-latest` — fast/cheap, not the strongest reasoning model.                |




## Live demo (about 90 seconds)

Open `/chat`. Ask “Explain embeddings in one paragraph.” Point at the loading bubble. When the reply lands, say: this answer came from the model’s weights plus a short system prompt — no PDF was retrieved. Refresh — history returns from Postgres; the *next* generate will only send the last 40 turns. Optionally stop the AI service to show a safe provider error. Do not upload a PDF or ask for weather on this page if you are presenting Task 1.

## Re-read the night before



### Must-read files

- `apps/web/app/chat/page.tsx` — `mode=llm`
- `apps/web/features/chat/ChatPanel.tsx`
- `apps/ai-service/app/services/chat.py` — `_answer_with_llm`
- `apps/ai-service/app/providers/llm.py` — role mapping, timeout, exception map
- `apps/ai-service/app/core/errors.py`
- `apps/ai-service/tests/integration/test_chat_api.py`


### Numbers to remember

- Max prompt: 8,000 characters
- History sent to Gemini: last 40 messages
- LLM timeout: 30,000 ms
- Model default: `gemini-flash-lite-latest`
- Status string: Generating response
- Send message HTTP: 201

---

Source: this repository’s Task 1 path after Tasks 2–5 were added. `/chat` still pins `llm`. Skip RAG and tools unless asked how the chatbot grew.
