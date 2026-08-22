# Task 4 interview study guide

Academic Research Copilot — Prompt Lab. This guide is the **AI prompting layer**: how instruction design changes model behavior, why examples and structure matter, and how you evaluate outputs without faking scores. Task 1 is chat. Task 2 is RAG. Task 3 is tools. This page is a comparison harness, not a chatbot.

| | |
|---|---|
| Demo page | `/prompt-lab` |
| Template version | `prompt-lab-v1` |
| Strategies per run | 5, independent `asyncio.gather` |
| Cost | Always `null` — never invented |

## 30-second pitch — say this first

I built a Prompt Lab that runs the same research question through five versioned templates: zero-shot, one-shot, few-shot, **visible** step-by-step, and structured JSON. FastAPI renders templates from `prompts/library.py` and calls Gemini independently with the same model settings. Chain-of-thought here is numbered working a student can read — not a hidden scratchpad. Structured output is parsed in Python; invalid JSON never reaches the UI as raw model text. Cost stays unavailable rather than guessed.

## What Task 4 is (and is not)

The assignment asks for four techniques plus a comparison table. The product also ships `structured` because leftover model text must not be presented as a “structured reasoning” result.

| Technique | What this app does | Do not claim |
|---|---|---|
| Zero-shot | Direct instruction + question. No examples. | “The model just answers” with no instruction wrapper |
| One-shot | One synthetic Q&A (literature vs systematic review) | User-uploaded or retrieved examples |
| Few-shot | Two curated academic examples | A large example bank or RAG chunks as shots |
| Chain-of-thought | Visible numbered steps, then `Final answer:` | Hidden scratchpad, o-series reasoning tokens |
| Structured | JSON schema parsed in Python; only formatted fields shown | Native Gemini JSON mode / OpenAI `response_format` |
| Evaluation | Manual 1–5 ratings; write-up of *when* techniques tend to work | LLM-as-judge, automatic leaderboard, or invented USD cost |

**Name the architecture honestly.** This is a **comparison harness**. It does not use conversation history, RAG chunks, or the agent router. Each strategy is one user message plus a strategy-specific `system_instruction`. Claiming “I used chain-of-thought” without the visible-vs-hidden caveat is the fastest way to get a follow-up you cannot answer.

## AI concepts you must be able to explain

### What prompt engineering is

Choosing the **instruction wrapper** around a user question so the same model produces a more usable completion. You are not training weights (that would be fine-tuning / RLHF). You are steering **in-context** behavior: role, format, examples, and constraints.

Templates are versioned application assets (`TEMPLATE_VERSION = "prompt-lab-v1"`), not strings pasted into React. Changing the wrapper is a science change — it is persisted with each result so old runs stay reproducible.

### In-context learning: zero / one / few-shot

The model can imitate a pattern that appears in the prompt. That is **in-context learning**, not a weight update.

| Strategy | Extra tokens | When it tends to work | Typical failure |
|---|---|---|---|
| `zero_shot` | Instruction only | Familiar, well-specified tasks. Fastest / cheapest. | Format drifts; skips caveats a lab needs. |
| `one_shot` | One worked example | You need a specific tone or compare-and-contrast shape. | The single example **over-anchors** the domain. |
| `few_shot` | Two+ examples | Structure is easy to miss (definition vs advice vs caveat). | Longer prompt; examples pull toward their domain. |

**Over-anchoring:** if your one-shot is about literature reviews, a question about lab-report citations may still come back in “review” language. Few-shot reduces that by showing more than one shape — at the cost of tokens.

Shared system rules for every strategy: Academic Research Copilot, concise, **do not invent citations/filenames/pages**, say so if unsure. Prompting does not replace Task 2 grounding; it only shapes how the *same ungrounded* question is answered.

### Chain-of-thought — the interview trap

Classic CoT (“think step by step”) can improve multi-step reasoning **and** can hide a private scratchpad. Product rule: we implemented **pedagogical CoT in the answer**.

- UI label: **Visible step-by-step**, not “hidden CoT.”
- Template asks for numbered working a student could follow, then `Final answer:`.
- System extra: numbered steps are student-facing; **no private scratchpad**.
- `test_chain_of_thought_forbids_hidden_scratchpad` asserts that phrase is in the system instruction.

We do **not** claim better hidden reasoning, OpenAI o-series traces, or that CoT always scores highest. On simple questions it is just verbose.

### Structured output — prompt + parse, not native JSON mode

We ask for ONLY JSON: `answer`, `key_points` (2–5), `confidence` high/medium/low, `limitations`. Then Python:

1. Unwrap ` ```json ` fences if present.
2. `json.loads`, or slice first `{` to last `}`.
3. Pydantic `StructuredLabAnswer` — non-blank fields, 1–8 key points, enum confidence.
4. Failure → `STRUCTURED_PARSE_FAILURE` and a safe sentence. Raw text discarded.

`test_structured_parse_failure_does_not_leak_raw` sends “Let me think privately…” and asserts that phrase is **not** in `output`. The fifth card shows Answer / Key points / Confidence / Limitations — never a JSON blob, never hidden CoT.

The prompt asks for 2–5 key points; the parser allows up to 8 so a slightly oversized array still displays rather than dumping raw text.

**Why add structured when the brief listed four techniques?** A structured strategy must not present leftover reasoning as the result. JSON + a parser is the machine-checkable column.

### Why comparisons must be independent

Fair A/B on **prompting**, not on leaked state:

- Same `LLM_MODEL` and settings for every strategy.
- `asyncio.gather` — independent calls; strategy A’s output is not in strategy B’s prompt.
- No conversation history (older chat turns cannot contaminate one card).
- No RAG chunks (that would mix untrusted document text into the “same input” contract).
- `{{input}}` replacement, not `str.format` — user `{n}` braces must not break the template.

One strategy’s `AppError` does not abort the others. Failed generate is **not** persisted; the card shows `error_message` and cannot be rated.

### Evaluation — what you can and cannot claim

| Signal | What we store | What we do **not** do |
|---|---|---|
| Manual ratings | Accuracy, clarity, research usefulness (1–5) | LLM-as-judge replacing the human |
| Latency | `elapsed_ms` per strategy (`perf_counter`) | Calling the slowest “worse” automatically |
| Tokens | Copied from Gemini usage when present; else null | Inventing a cost formula |
| Cost | Always `cost_usd=None` | Dollars-per-token from a stale price table |
| Report | `docs/prompt-comparison-report.md` — *when* techniques tend to work | A published leaderboard of live Gemini quality |

Live completions vary. The comparison table from `GET /prompt-library` is a **guide**, not a benchmark score.

### Three prompt surfaces — do not mix them

| Surface | Where | In Prompt Lab UI? |
|---|---|---|
| Prompt Lab templates | `prompts/library.py` `prompt-lab-v1` | User templates in `<details>`. CoT/structured **system extras** are not in `GET /prompt-library`. |
| Chat system instruction | Task 1 `_answer_with_llm` | No |
| RAG system instruction | Task 2 grounded answering | No |
| Router system instruction | Task 3 JSON classifier | No |

If they ask “could Prompt Lab use RAG as few-shot examples?” — that would mix untrusted document text into the comparison and break “same input, independent templates.” Keep retrieved evidence in Task 2.

## Persistence (so evaluation is reproducible)

`run_id` groups one click. Each strategy is its own row so ratings attach to a **technique**, not the whole run. `template_version` means later copy edits do not silently rewrite old science.

## Drill these questions

### What is prompt engineering in this product?

Versioning the instruction wrapper around one question, then comparing visible outputs. The lab shows zero-shot vs examples vs visible steps vs JSON **without changing the model**.

### Walk me through one comparison click

POST trimmed input → `run_comparison` assigns `run_id` → five `render_prompt` + `llm.generate` in parallel → structured path runs `_visible_output` → successful rows hit Postgres → five cards, same input, different labels.

### Why not put templates in the frontend?

The frontend must not call Gemini. Templates need a version persisted with the result. If the copy lived only in React, a UI tweak would silently change old screenshots. `library.py` is the single source.

### Is this chain-of-thought?

Visible pedagogical CoT. Numbered student-facing working, then `Final answer:`. We forbid private scratchpad language. We do not claim hidden reasoning improved.

### Why is cost always unavailable?

Token → USD needs a documented price table that goes stale. Product rule: mark unavailable rather than estimate. Tests assert `cost_usd is None` even when `total_tokens == 33`.

### Why `replace("{{input}}")` instead of `.format()`?

User questions can contain `{n}`. `str.format` would throw or swallow braces.

### How do you keep comparisons fair?

Same model, independent calls, no history, no RAG, fixed strategy order. Failures stay in-band on that card.

### How do you test prompting without paying Google?

`StrategyAwareFakeLLM` inspects the **user** message: JSON schema → structured payload; “same style as the examples” → few-shot; “numbered working” → CoT; else zero-shot. Integration tests assert `Final answer:` in CoT, `Key points:` in structured, and that raw scratchpad text is not leaked.

### How would you improve this with another week?

Native JSON schema / constrained decoding, optional user-supplied shots, streaming per card, LLM-as-judge **behind** the same rating fields (do not replace manual scores silently). Do not claim automatic “best prompt” ranking you did not ship.

## If they ask “was this AI-generated?”

**Do not deny it. Own the prompting contract.**

I used AI to move faster on boilerplate, but I can defend why templates are versioned server-side, why CoT is visible not hidden, why structured output is parsed in Python, why cost is unavailable, why `{{input}}` is replace not format, and why Prompt Lab is not `ChatService`. Then walk one comparison to five cards.

### Phrases that sound like you built it

| Say | Avoid |
|---|---|
| Five versioned templates, same input, independent Gemini calls. | I prompt-engineered the chatbot. (that is Tasks 1–3) |
| CoT is numbered student-facing working. The UI says Visible step-by-step. | We use chain-of-thought. (hidden? which API?) |
| Structured JSON is parsed in Python. Invalid JSON never reaches the UI raw. | The model returns JSON to the browser. |
| `cost_usd` is always null. Tokens only when Gemini sends usage. | We calculated the cost. |
| Prompt Lab does not use RAG or tools. It is a comparison harness. | The agent picks the best prompt. |

## Honest limitations (better than getting caught)

| Limitation | Accurate AI sentence |
|---|---|
| Not a quality benchmark | The report describes *when* techniques tend to work. Live output varies. |
| Examples are synthetic and fixed | Users cannot upload their own shots. |
| CoT is not hidden reasoning | We show the steps. We cannot prove a private chain improved. |
| Structured is prompt + parse | Gemini can still emit fences or prose; the parser is the safety net. |
| No conversation / RAG context | Fair for A/B templates; worse if you wanted “prompt against this PDF.” |
| Five generate calls per click | Parallelism helps wall time, not billable tokens. |

## Live demo (about 90 seconds)

Open `/prompt-lab`. Point at **When each technique tends to work** (from the API). Click the RAG example chip. Status: Comparing prompting strategies. When five cards land:

- Zero-shot: direct paragraph
- One/few-shot: echo example style
- Visible step-by-step: numbered lines + `Final answer:`
- Structured: Key points / Confidence / Limitations — **not** a JSON blob

Open Prompt library (`prompt-lab-v1`) and show `{{input}}`. Rate Accuracy 4 on one card. Do not upload a PDF or ask for weather on this page if you are presenting Task 4 only.

## Re-read the night before

### Must-read files

- `apps/ai-service/app/prompts/library.py`
- `apps/ai-service/app/prompts/structured.py`
- `apps/ai-service/app/services/prompt_lab.py`
- `docs/prompt-comparison-report.md`
- `docs/prompt-library.md`
- `apps/ai-service/tests/unit/test_prompt_library.py`
- `apps/ai-service/tests/integration/test_prompt_lab_api.py`

### Numbers and strings to remember

- Version: `prompt-lab-v1`
- Five strategies; default all of them
- Max input: 8,000 characters
- Ratings: 1–5, three axes
- `cost_usd` always `null`
- Status: Comparing prompting strategies
- CoT must include `Final answer:`
- Demo question: Why do researchers use retrieval-augmented generation…?

---

Source: this repository’s Task 4 path after Tasks 1–5. `/prompt-lab` is still a dedicated playground. Skip `ChatService` unless asked how Prompt Lab stays separate from chat, RAG, and tools.
