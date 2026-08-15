# Prompt library (`prompt-lab-v1`)

Source of truth: `apps/ai-service/app/prompts/library.py`.
The UI also loads this via `GET /api/v1/prompt-library`. Placeholders use `{{input}}`.

These are Prompt Lab assets. Chat, RAG, and agent system prompts are not listed here.

## Shared rules (system)

You are Academic Research Copilot helping a student or researcher. Be accurate and concise. Do not invent citations, filenames, page numbers, or sources. If you are unsure, say so.

## Zero-shot

```text
Answer the following research question directly.

Question:
{{input}}
```

## One-shot

Includes one synthetic example (literature review vs systematic review). User template:

```text
Answer the research question in the same style as the example.

Example question:
…

Example answer:
…

Question:
{{input}}
```

## Few-shot

Adds a second synthetic example (when to cite in a lab report).

```text
Answer the research question in the same style as the examples.

Example 1 …
Example 2 …

Question:
{{input}}
```

## Visible step-by-step (chain-of-thought)

System extra: numbered steps are student-facing. Do not write private scratchpad or “let me think internally”.

```text
Explain the answer with short numbered working a student could follow,
then one line starting with 'Final answer:'.

Question:
{{input}}
```

## Structured output

System extra: return only JSON. No markdown fences, commentary, or chain-of-thought.

```text
Return ONLY a JSON object with these keys:
- "answer": string (concise final answer)
- "key_points": array of 2 to 5 short strings
- "confidence": one of "high", "medium", "low"
- "limitations": string (what the answer does not cover)

Question:
{{input}}
```

Parsed fields are formatted for the UI. If parsing fails, the user sees a safe failure message — not the raw model text.
