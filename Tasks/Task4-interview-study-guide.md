# Task 4 interview study guide

Academic Research Copilot — Prompt Lab. Memorize the pitch, then the five strategies, then the CoT vs structured split. Task 1 is the chat spine. Task 2 is RAG. Task 3 is tools. This page is a prompt-engineering playground that compares the same question across versioned templates.

| | |
|---|---|
| Demo page | `/prompt-lab` |
| Template version | `prompt-lab-v1` |
| Strategies per run | 5 (default), independent via `asyncio.gather` |
| Cost | Always `null` — never invented |

## 30-second pitch — say this first

I built a Prompt Lab that runs the same research question through five versioned templates: zero-shot, one-shot, few-shot, visible step-by-step, and structured JSON. The browser never talks to Gemini. FastAPI renders templates from `prompts/library.py`, calls Gemini independently for each strategy with the same model settings, and persists a project-scoped experiment. Chain-of-thought here is numbered working a student can read — not a hidden scratchpad. Structured output is parsed in Python; if JSON is invalid, the user sees a safe failure message, never the raw model dump. Cost stays unavailable rather than guessed.

## What Task 4 is (and is not)

Task 4’s assignment asks for four techniques plus a comparison table. The product also ships `structured` because `AGENTS.md` forbids treating leftover model text as a “structured reasoning” result.

| Requirement | What this app does | Do not claim in Task 4 |
|---|---|---|
| Zero-shot | Direct instruction + question. No examples. `prompts/library.py` | Few-shot with zero examples, or “the model just answers” |
| One-shot | One synthetic Q&A (literature vs systematic review) | User-uploaded examples, or dynamic example retrieval |
| Few-shot | Two curated academic examples (adds “when to cite in a lab report”) | A large example bank or in-context RAG chunks as shots |
| Chain-of-thought | Visible numbered steps, then `Final answer:` | Hidden scratchpad, OpenAI reasoning tokens, or “let me think internally” |
| Structured (extra vs the brief) | JSON schema parsed in `prompts/structured.py`; only formatted fields shown | Native Gemini JSON mode / OpenAI `response_format` |
| Comparison table | Live table from `GET /prompt-library` + write-up in `docs/prompt-comparison-report.md` | A measured leaderboard or automated quality score |
| Prompt library | Versioned assets + UI `<details>` of **user** templates | Dumping chat/RAG system prompts |
| Ratings | Manual 1–5: accuracy, clarity, research usefulness | An LLM-as-judge or a cost formula |

**Name the architecture honestly.** This is a comparison harness, not a chatbot. It does not use conversation history, RAG chunks, or the agent router. Each strategy is one user message plus a strategy-specific `system_instruction`. Claiming “I used chain-of-thought prompting” without the visible-vs-hidden caveat is the fastest way to get a follow-up you cannot answer.

## Draw this request path

Browser never talks to Gemini. Next.js proxies `/api/v1` to FastAPI. `PromptLabService` owns the use case — not `ChatService`.

| Step | Layer | File | What happens |
|---|---|---|---|
| 1 | UI | `app/prompt-lab/page.tsx` | Task 4 header. Renders `PromptLabPanel`. |
| 2 | Bootstrap | `PromptLabPanel.tsx` | Load/create project. `GET` library + previous runs. |
| 3 | Client | `lib/api.ts` | POST `{ input }` (optional `strategies`) with `X-User-Id`. |
| 4 | HTTP | `api/v1/prompt_experiments.py` | `POST /projects/{id}/prompt-experiments` → 201. |
| 5 | Validate | schemas + service | Owner-scoped project. Strip. Max 8000 chars. Blank → 422. |
| 6 | Render | `prompts/library.py` `render_prompt` | Replace `{{input}}` — not `str.format`, so `{n}` in the question cannot break the template. |
| 7 | Generate | `PromptLabService._run_strategy` | Same `LLM_MODEL` for every strategy. One user turn. No chat history. |
| 8 | Parallel | `asyncio.gather` | Independent calls. One strategy failing with `AppError` does not abort the others. |
| 9 | Structured | `prompts/structured.py` | Parse JSON → format fields. Failure → safe copy, raw text discarded. |
| 10 | Persist | `postgres_store.py` | One `prompt_experiments` row per **successful** strategy. Same `run_id`. |
| 11 | UI | result cards | Label, version, model, `elapsed_ms`, tokens or “unavailable”, cost unavailable, ratings. |

## Five strategies — what actually gets sent

Source of truth: `_SPECS` in `apps/ai-service/app/prompts/library.py`. Shared system rules: Academic Research Copilot, concise, **do not invent citations/filenames/pages**, say so if unsure.

| Strategy | User template gist | Extra system rule | When it performs better | Typical failure |
|---|---|---|---|---|
| `zero_shot` | “Answer the following research question directly.” | Shared rules only | Familiar, well-specified tasks. Fastest/cheapest. | Format drifts; skips caveats a lab needs. |
| `one_shot` | One example: literature review vs systematic review | Match the style of the example | Specific tone or compare-and-contrast shape | The single example over-anchors the domain |
| `few_shot` | Example 1 + when to cite in a lab report | Match the style of the examples | Structure is easy to miss (definition vs advice vs caveat) | Longer prompt; examples pull toward their domain |
| `chain_of_thought` | Numbered working a student could follow, then `Final answer:` | Numbered steps are student-facing. No private scratchpad. | Multi-step academic reasoning | Verbose on simple questions |
| `structured` | Return ONLY JSON: `answer`, `key_points` (2–5), `confidence` high/medium/low, `limitations` | JSON only. No fences, commentary, or CoT | Rubrics / field-by-field comparison | Invalid JSON → parse-failure message |

**The CoT trap.** Interviewers hear “chain-of-thought” and think hidden reasoning. Say: we implemented **pedagogical CoT in the answer**. The UI label is **Visible step-by-step**, not “hidden CoT.” `test_chain_of_thought_forbids_hidden_scratchpad` asserts `private scratchpad` is in the system instruction.

**The structured trap.** The model is asked for JSON, but the UI never shows JSON as the product. `_visible_output` parses, then `format_structured_answer` prints answer + Key points + Confidence + Limitations. `test_structured_parse_failure_does_not_leak_raw` sends “Let me think privately…” and asserts that phrase is **not** in `output`.

## Prompt library vs chat/RAG prompts

Three prompt surfaces exist. Do not mix them.

| Surface | Where | Shown in Prompt Lab UI? |
|---|---|---|
| Prompt Lab templates | `app/prompts/library.py` version `prompt-lab-v1` | User templates in a `<details>` block. System extra for CoT/structured is **not** in `GET /prompt-library`. |
| Chat system instruction | Task 1 `_answer_with_llm` | No — “Chat/RAG system prompts are not shown.” |
| RAG system instruction | Task 2 grounded answering | No |

`GET /api/v1/prompt-library` returns `version`, `id`, `name`, `description`, `when_better`, `user_template`. That is the live comparison table. `docs/prompt-library.md` and `docs/prompt-comparison-report.md` are the Task 4 written deliverables.

## Persistence model

`run_id` groups one comparison. Each strategy is its own row so ratings attach to one technique, not the whole run.

| Field | Why it exists |
|---|---|
| `run_id` | Groups the 5 results of one click |
| `project_id` + `owner_user_id` | Isolation. Other user listing the same project id → 404 |
| `strategy` + `template_version` | Reproducibility. Later template edits do not silently rewrite old rows |
| `model` / `provider` | Fair comparison metadata |
| `generated_output` | Visible text only (already parsed for structured) |
| `elapsed_ms` | Wall time per strategy (`time.perf_counter`) |
| `prompt_tokens` / `completion_tokens` / `total_tokens` | Copied from Gemini when present; else null |
| ratings | `rating_accuracy`, `rating_clarity`, `rating_research_usefulness` 1–5 |

**Failed generate is not stored.** If `_llm.generate` raises `AppError`, that strategy returns `error_code` / `error_message` with empty `output` and **no** `create_prompt_experiment`. The HTTP status for the comparison is still 201. Ratings UI requires `result.id` and no `error_message`.

**Cost is always `None`.** `_to_response` hard-codes `cost_usd=None`. `formatUsage` prints `cost unavailable`. Do not invent a dollars-per-token figure in the interview.

## API contract

| Method | Path | Role |
|---|---|---|
| GET | `/api/v1/prompt-library` | Versioned strategy guide (auth required; 401 without `X-User-Id`) |
| POST | `/api/v1/projects/{project_id}/prompt-experiments` | Run comparison. 201. Default all five strategies |
| GET | `/api/v1/projects/{project_id}/prompt-experiments` | `{ runs: [...] }` grouped by `run_id`, newest first |
| PATCH | `/api/v1/prompt-experiments/{experiment_id}` | Partial ratings. At least one field required |

`strategies` on POST is optional. Empty list is rejected. Duplicates are dropped while preserving order. The UI currently sends only `input` and lets the server default to all five.

## Errors: comparison vs HTTP problem

| Failure | HTTP | What the user sees |
|---|---|---|
| Missing `X-User-Id` | 401 | `UNAUTHORIZED` |
| Blank / whitespace input | 422 | `VALIDATION_ERROR` — Prompt Lab input cannot be blank |
| Input > 8000 chars | 422 | Prompt Lab input is too long |
| Project not owned / missing | 404 | Project not found (`NOT_FOUND`) — same 404-not-403 policy as Task 1 |
| Rate with no fields | 422 | Provide at least one rating |
| Rate another user’s experiment | 404 | Prompt experiment not found |
| One strategy’s Gemini call fails | 201 | That card shows `error_message`; others may succeed |
| Structured JSON invalid | 201 | “The model did not return valid structured output… No hidden reasoning is shown.” |
| Gemini timeout / down (uncaught at gather if not `AppError`) | mapped globally | Safe problem detail; no traceback |

**Do not say a failed strategy is always a 4xx.** Per-strategy `AppError` is in-band on the result object, similar in spirit to Task 3 `ToolError` staying HTTP 201.

## Frontend contract

| Surface | Behavior |
|---|---|
| `/prompt-lab` | Prompt Lab only. No chat composer, no PDF panel, no auto router |
| Bootstrap | “Preparing Prompt Lab…” then library table + form |
| Empty | “No comparison yet” |
| Running | Composer disabled. Status: Comparing prompting strategies |
| Success | Grid of cards. Markdown via `MarkdownMessage`. Usage line from `formatUsage` |
| Error | `role=alert` with `ApiError.message` |
| Library | `<details>` Prompt library (`prompt-lab-v1`) — user templates only |
| History | Earlier runs listed by input text; click to reopen |
| Ratings | Three `<select>` 1–5; PATCH one field at a time |

Client helper `canRunPromptLab` is `trim().length > 0`. Same blank-input rule as chat.

Example chips (good live demo questions):

1. Why do researchers use retrieval-augmented generation instead of relying only on a model's training data?
2. What is the difference between correlation and causation in a student lab report?
3. How should a student write a focused research question?

## How this coexists with Tasks 1–3

Same Gemini adapter (`LLMProvider`). Same project + `X-User-Id` isolation. **Different service and table.** Prompt Lab does not POST to `/conversations/{id}/messages`, does not pin `mode`, does not retrieve chunks, and does not call calculator/weather/search.

If they ask “could Prompt Lab use RAG as few-shot examples?” — say that would mix untrusted document text into the comparison and break the “same input, independent templates” contract. Keep retrieved evidence in Task 2.

## Structured parser — details interviewers love

`parse_structured_answer` in `prompts/structured.py`:

1. Strip. If fenced ` ```json `, unwrap.
2. `json.loads` the whole string if it is a dict.
3. Else slice from first `{` to last `}` and parse.
4. `StructuredLabAnswer` Pydantic: non-blank `answer`/`limitations`, 1–8 key points after stripping empties, `confidence` ∈ high/medium/low.
5. `None` on JSON or validation failure → `STRUCTURED_PARSE_FAILURE`.

The prompt asks for 2–5 key points; the parser allows up to 8 so a slightly oversized array still displays rather than dumping raw text.

## Drill these questions

### What is prompt engineering in this product?

Choosing and versioning the **instruction wrapper** around one user question, then measuring the visible output. The lab is how we show zero-shot vs examples vs visible steps vs JSON without changing the model. Templates are application assets with `TEMPLATE_VERSION = "prompt-lab-v1"`, not strings pasted into a React file.

### Walk me through one comparison click

`/prompt-lab` posts the trimmed question. `PromptLabService.run_comparison` checks the project, assigns a `run_id`, and `asyncio.gather`s five `_run_strategy` calls. Each one `render_prompt`s, times `llm.generate`, and for `structured` runs `_visible_output`. Successful rows hit Postgres. The UI shows five cards with the same input and different labels.

### Why not put templates in the frontend?

The frontend must not call Gemini. Templates also need a version field persisted with the result. If the copy lived only in React, a UI tweak would silently change science for old screenshots. `library.py` is the single source; `GET /prompt-library` and `docs/prompt-library.md` read from that idea.

### Is this chain-of-thought?

Visible pedagogical CoT. The answer contains numbered working a student can follow, then `Final answer:`. We explicitly forbid private scratchpad language. We do not claim better hidden reasoning, OpenAI o-series traces, or that CoT always scores highest.

### Why add structured when Task 4 only listed four techniques?

`AGENTS.md` requires a structured strategy that must not present hidden reasoning as the result. JSON plus a Python parser is how we keep the fifth card comparable and safe. The assignment’s comparison table still covers the four classic techniques; structured is the lab’s machine-checkable column.

### Why is cost always unavailable?

Gemini usage metadata may include token counts. Turning tokens into USD needs a documented price table that goes stale. The product rule is: mark unavailable rather than estimate. Tests assert `cost_usd is None` even when `total_tokens == 33`.

### Why `replace("{{input}}")` instead of `.format()`?

User questions can contain `{n}` or `{k}`. `str.format` would throw or swallow braces. `test_user_braces_do_not_break_rendering` covers this.

### How do you keep comparisons fair?

Same `llm_model` from settings. Independent calls (no previous strategy’s output in the next prompt). No conversation history, so older chat turns cannot leak into one card. Strategies default to a fixed order in the API list and in `_strategy_order` when grouping history.

### How is this isolated?

`get_project(project_id, owner_user_id)` before run/list. Ratings update with `experiment_id` **and** `owner_user_id`. `test_project_isolation` uses `X-User-Id: other-user` and expects 404 on list and patch — not 403.

### How do you test without paying Google?

`StrategyAwareFakeLLM` inspects the **user** message: JSON schema → structured payload; “same style as the examples” → few-shot; “same style as the example” → one-shot; “numbered working” → CoT; else zero-shot. Unit tests never call the network. Integration tests assert 201, five outputs, `Final answer:` in CoT, `Key points:` in structured, blank input 422, isolation 404, and raw CoT leak blocked.

### How would you improve this with another week?

Honest next steps: native JSON schema / constrained decoding for `structured`, optional user-supplied one-shot examples, streaming per card, an LLM-as-judge **behind** the same ratings fields (do not replace manual scores silently), and a documented cost table if product asks for it. Do not claim automatic “best prompt” ranking you did not ship.

## If they ask “was this AI-generated?”

**Do not deny it. Own the prompting contract.**

I used AI to move faster on boilerplate, but I can defend why templates are versioned server-side, why CoT is visible not hidden, why structured output is parsed in Python, why cost is unavailable, why `{{input}}` is replace not format, and why Prompt Lab is not `ChatService`. Then walk one comparison from `/prompt-lab` to `asyncio.gather` to five cards. That is what they are testing — comprehension, not who typed `library.py`.

### Phrases that sound like you built it

| Say | Avoid |
|---|---|
| Five versioned templates, same input, independent Gemini calls via `asyncio.gather`. | I prompt-engineered the chatbot. (that is Tasks 1–3) |
| CoT is numbered student-facing working. The UI says Visible step-by-step. | We use chain-of-thought. (hidden? tokens? which API?) |
| Structured JSON is parsed in Python. Invalid JSON never reaches the UI as raw text. | The model returns JSON to the browser. |
| `cost_usd` is always null. Tokens only when Gemini sends usage. | We calculated the cost. |
| Templates live in `prompts/library.py` as `prompt-lab-v1`, not in React. | The frontend has the prompts. |
| Failed strategy is in-band on the card. Successful rows persist. Isolation is 404. | Errors always return 400. |
| Prompt Lab does not use RAG or tools. It is a comparison harness on one question. | The agent picks the best prompt. |

## Honest limitations (better than getting caught)

| Limitation | Accurate sentence |
|---|---|
| Not a quality benchmark | The comparison report describes *when techniques tend to work*. Live Gemini output varies; we do not publish automatic scores. |
| Examples are synthetic and fixed | Literature-review and citation examples are baked in. Users cannot upload their own shots yet. |
| CoT is not hidden reasoning | We show the steps. We cannot prove the model’s private chain improved. |
| Structured is prompt + parse, not native JSON mode | Gemini can still emit fences or prose; the parser is the safety net. |
| No conversation / RAG context | Fair for A/B templates; worse if you wanted “prompt against this PDF.” |
| Per-strategy failure not persisted | You cannot rate a card that never got an `id`. |
| Five Gemini calls per click | Latency and quota. Parallelism helps wall time, not billable tokens. |
| Auth | Same as Task 1: `X-User-Id` in development, not OAuth. |
| Frontend tests are thin | Vitest covers labels, blank input, and `formatUsage`. Backend integration tests are the real coverage. |

## Live demo (about 90 seconds)

Open `/prompt-lab`. Point at the **When each technique tends to work** table (loaded from the API). Click the RAG example chip. Status: Comparing prompting strategies. When five cards land: zero-shot is a direct paragraph; one/few-shot should echo example style; visible step-by-step has numbered lines and `Final answer:`; structured shows Key points / Confidence / Limitations — not a JSON blob. Open Prompt library (`prompt-lab-v1`) and show a user template with `{{input}}`. Rate Accuracy 4 on one card. Optional: mention `docs/prompt-comparison-report.md` as the written Task 4 deliverable. Do not upload a PDF or ask for weather on this page if you are presenting Task 4 only.

## Re-read the night before

### Must-read files

- `apps/web/app/prompt-lab/page.tsx`
- `apps/web/features/prompt-lab/PromptLabPanel.tsx`
- `apps/web/features/prompt-lab/strategyMeta.ts`
- `apps/ai-service/app/prompts/library.py`
- `apps/ai-service/app/prompts/structured.py`
- `apps/ai-service/app/services/prompt_lab.py`
- `apps/ai-service/app/api/v1/prompt_experiments.py`
- `docs/prompt-comparison-report.md`
- `docs/prompt-library.md`
- `apps/ai-service/tests/unit/test_prompt_library.py`
- `apps/ai-service/tests/integration/test_prompt_lab_api.py`

### Numbers and strings to remember

- Version: `prompt-lab-v1`
- Five strategies; default all of them
- Max input: 8,000 characters (same as chat)
- Ratings: 1–5, three axes
- `cost_usd` always `null`
- Status: Comparing prompting strategies
- Structured failure copy: valid structured output / No hidden reasoning is shown
- CoT must include `Final answer:`
- Isolation: 404 for other users
- Blank input: 422 `VALIDATION_ERROR`
- Demo question: Why do researchers use retrieval-augmented generation…?

---

Source: this repository’s Task 4 path as it exists after Tasks 1–5 were added. `/prompt-lab` is still a dedicated playground. `ChatService` is a different use case — skip it unless asked how Prompt Lab stays separate from chat, RAG, and tools.
