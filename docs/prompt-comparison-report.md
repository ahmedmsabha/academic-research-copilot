# Prompt comparison report

Synthetic comparison of Prompt Lab strategies in Academic Research Copilot (`prompt-lab-v1`).
The same user question is sent independently to each template with equivalent model settings.
Hidden model scratchpad is never treated as a deliverable.

**Question used for this write-up**

> Why do researchers use retrieval-augmented generation instead of relying only on a model's training data?

Live output will vary by model and date. The table below describes *when each technique tends to perform better* and what the lab is designed to show. Capture `/prompt-lab` screenshots as `docs/screenshots/task4-*.png` after a local run.

## Comparison table

| Technique | What the template does | When it performs better | Typical failure mode |
|---|---|---|---|
| **Zero-shot** | Direct instruction + question. No examples. | Familiar, well-specified tasks (short definitions, “what is X?”). Fastest and cheapest. | Format drifts; may skip caveats a lab report needs. |
| **One-shot** | One representative Q&A example. | You need a specific tone or compare-and-contrast shape and one example is enough. | The single example can over-anchor the answer. |
| **Few-shot** | Two curated academic examples. | The desired structure is easy to miss (definition vs. advice vs. limitation). | Longer prompt; examples can pull the model toward the example domain. |
| **Visible step-by-step (CoT)** | Numbered working a student can read, then `Final answer:`. | Multi-step academic reasoning (method choice, evaluating a claim). | Verbose on simple questions; still not a hidden scratchpad. |
| **Structured output** | JSON with `answer`, `key_points`, `confidence`, `limitations`. Only parsed fields are shown. | Rubrics, labs, and anything that must be compared field-by-field. | Invalid JSON → safe parse-failure message, never a CoT dump. |

## How this maps to Task 4

Task 4 asks for zero-shot, one-shot, few-shot, and chain-of-thought. The product implements CoT as **visible pedagogical steps in the answer**. AGENTS.md also requires a `structured` strategy that must not present hidden reasoning as the result — the parser keeps only the schema fields.

## Quality dimensions (manual ratings)

Each saved result can be rated 1–5 on:

- **Accuracy** — would you trust this for a student-facing explanation?
- **Clarity** — is the wording easy to follow?
- **Research usefulness** — does it help someone write or read academic work?

Token counts appear only when the provider returns usage metadata. **Cost is unavailable**; the app does not invent a price.

## Expected qualitative pattern (not a live-model score)

On the RAG question above, a typical pattern is:

1. Zero-shot: correct gist, less consistent structure.
2. One-shot / few-shot: closer to the example’s “definition then contrast” shape.
3. Visible step-by-step: slower to read, better for teaching *why*.
4. Structured: easiest to scan and to compare across runs.

Use the live playground to confirm with the current Gemini model rather than treating this paragraph as a measured benchmark.
