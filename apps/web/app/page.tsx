import Link from "next/link";

import { AppNav } from "@/components/AppNav";

const capabilities = [
  {
    href: "/workspace",
    label: "Workspace",
    title: "Complete assistant",
    body: "Chat, PDF grounding, tools, and conversation history in one research workspace.",
  },
  {
    href: "/chat",
    label: "Chat",
    title: "Persistent conversations",
    body: "Gemini chat with loading states, safe errors, and history that reloads after refresh.",
  },
  {
    href: "/rag",
    label: "Documents",
    title: "PDF upload and RAG",
    body: "Index project-scoped PDFs and get answers cited to filename and page.",
  },
  {
    href: "/agent",
    label: "Tools",
    title: "Calculator, weather, search",
    body: "The agent picks a tool automatically and labels external evidence.",
  },
  {
    href: "/prompt-lab",
    label: "Prompt Lab",
    title: "Prompting comparison",
    body: "Compare zero-shot, one-shot, few-shot, step-by-step, and structured output.",
  },
] as const;

export default function HomePage() {
  return (
    <>
      <AppNav currentPath="/" />
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <section className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Production assistant</p>
          <h1 className="mt-2 font-display text-4xl text-ink sm:text-5xl">
            Academic Research Copilot
          </h1>
          <p className="mt-4 text-lg text-ink-muted">
            A complete AI assistant for students and researchers: chat with history, grounded PDF
            answers, tool calling, and a Prompt Lab — with safe errors and a modern workspace.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/workspace"
              className="rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Open workspace
            </Link>
            <Link
              href="/prompt-lab"
              className="rounded-xl border border-line bg-white/70 px-4 py-2.5 text-sm font-medium text-ink transition hover:bg-accent-soft"
            >
              Compare prompts
            </Link>
          </div>
        </section>

        <section className="mt-10 grid gap-4 sm:grid-cols-2" aria-label="Capabilities">
          {capabilities.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="rounded-3xl border border-line bg-white/70 p-5 shadow-[0_16px_40px_rgba(28,36,48,0.06)] backdrop-blur transition hover:border-accent/40"
            >
              <p className="text-xs uppercase tracking-[0.16em] text-ink-muted">{item.label}</p>
              <h2 className="mt-2 font-display text-2xl text-ink">{item.title}</h2>
              <p className="mt-2 text-sm text-ink-muted">{item.body}</p>
              <p className="mt-4 text-sm font-medium text-accent">Open →</p>
            </Link>
          ))}
        </section>
      </main>
    </>
  );
}
