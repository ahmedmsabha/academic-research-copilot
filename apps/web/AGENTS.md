# AGENTS.md — `apps/web`

Local operating guide for the Next.js frontend. Follow the root [`AGENTS.md`](../../AGENTS.md) unless this file overrides a rule for `apps/web`.

## Purpose

Own rendering, interaction, client-side state, browser-safe validation, and calls to the FastAPI AI service. This app must **not** call LLM, embedding, search, weather, database, vector database, or object-storage providers directly.

## Stack

- Next.js (App Router)
- TypeScript (strict)
- Tailwind CSS
- Vitest for unit/component tests
- Playwright for e2e

## Directory Map

```text
apps/web/
├── app/           # App Router routes (including /workspace)
├── components/    # Shared UI primitives
├── features/      # Feature-scoped UI, state, and API adapters
├── lib/           # Typed API client and client utilities
├── hooks/
├── types/
├── public/
├── tests/
├── e2e/
└── AGENTS.md
```

Keep feature logic close to the feature directory or route that owns it. Prefer server components for static/layout content; use client components only where browser interaction is required (chat composer, upload, polling, streamed rendering, Prompt Lab controls).

## Non-Negotiable UI Rules

1. Never fabricate or invent citations in the UI. Render only citation metadata returned by the API (filename, page range, chunk linkage).
2. Never put secrets in `NEXT_PUBLIC_*`, client bundles, logs, tests, fixtures, or screenshots.
3. Do not expose chain-of-thought or hidden prompts. Show only concise operational status from the API (e.g. “Searching uploaded documents”).
4. Label external evidence clearly when the route is web search or weather; do not present it as document citations.
5. Validate untrusted user input at the form/client boundary before submit (blank messages, file type/size hints).
6. Every async surface needs empty, loading, success, error, and disabled-while-submitting states.
7. Prefer small, reviewable changes. Do not refactor unrelated files.

## Feature Ownership (maps to Tasks)

| Area | Responsibility |
|---|---|
| Chat | Composer, message list, history, loading/error, optional streaming render (Task 1 / Task 5) |
| Workspace | Unified assistant at `/workspace`: history sidebar, auto routing, documents (Task 5) |
| Projects & documents | Project selection, PDF upload UI, indexing status, delete confirmation (Task 2 / Task 5) |
| Citations | Display filename and page/range from API metadata only (Task 2) |
| Agent status | Show user-safe route status from API; never show private reasoning (Task 3) |
| Prompt Lab | Strategy selection, comparison table, ratings, saved experiment views (Task 4) |

## API Client Rules

- Call only versioned AI-service HTTP APIs (prefer `/api/v1/...`).
- Use a typed API client that maps errors into a predictable UI error type.
- Never add a Next.js API route solely to tunnel a secret-bearing request to a third party; the AI service owns provider integrations.
- Keep JSON conventions consistent with the backend contract; update callers when contracts change.

## Chat UI Requirements

- Block blank/whitespace-only messages.
- Keyboard accessible: Enter sends when appropriate; Shift+Enter inserts a newline.
- Render Markdown safely; sanitize and disable unsafe HTML by default.
- Distinguish user messages, assistant messages, status events, tool notices, errors, and citations.
- Do not imply a PDF is searchable until `status = ready`.

## Documents UI Requirements

- Show filename, upload date, size/page count when available, and indexing state.
- Announce upload/indexing progress accessibly.
- Require deliberate confirmation for irreversible deletion.
- Handle invalid/oversized file feedback from the API with clear next actions.

## Prompt Lab UI Requirements

- Compare zero-shot, one-shot, few-shot, visible step-by-step (CoT), and structured strategies for the same input.
- Show strategy, result, timing, and usage/cost only when the API provides them.
- Never display hidden model reasoning as “structured reasoning”; show only the requested structured final answer.

## Styling and Accessibility

- Use Tailwind tokens and reusable primitives; avoid unexplained arbitrary values when a token exists.
- Semantic HTML first; labeled inputs; accessible names for icon-only buttons; dialog focus management; sufficient contrast.
- Support narrow viewports without horizontal overflow.
- Do not encode meaning by color alone.

## Testing Focus

- Component/unit: message rendering, citations, form validation, upload states, errors, Prompt Lab results.
- E2E (highest value): project → upload fixture PDF → ready → grounded Q&A with source/page; insufficient evidence; calculator route; invalid upload; delete removes retrieval/UI presence.

## Commands (when configured)

```bash
npm ci
npm run dev
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

Do not claim a script exists until it is defined in this package.

## Guidance for Agents

1. Read root `AGENTS.md` for product rules, then apply this file for frontend boundaries.
2. Implement the smallest UI change that fulfills the task; wire to existing API contracts.
3. If a needed endpoint is missing, coordinate with `apps/ai-service` rather than calling providers from the browser.
4. Update `docs/api.md` / README only when user-facing setup or contracts change as part of the task.
5. Finish by reporting changed files, UI behavior, and tests run.
