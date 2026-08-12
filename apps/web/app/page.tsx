import Link from "next/link";

import { AppNav } from "@/components/AppNav";

const features = [
  {
    href: "/chat",
    task: "Task 1",
    title: "General chat",
    body: "Gemini conversational chat with history, loading states, and safe errors.",
  },
  {
    href: "/rag",
    task: "Task 2",
    title: "Documents & RAG",
    body: "Upload PDFs, index embeddings, and ask grounded questions with page citations.",
  },
  {
    href: "/chat",
    task: "Task 3",
    title: "Agent tools",
    body: "Coming next: calculator, weather, and web search routing.",
    disabled: true,
  },
  {
    href: "/chat",
    task: "Task 4",
    title: "Prompt Lab",
    body: "Coming next: compare zero-shot, one-shot, few-shot, and structured prompts.",
    disabled: true,
  },
] as const;

export default function HomePage() {
  return (
    <>
      <AppNav currentPath="/" />
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <section className="max-w-3xl">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Portfolio app</p>
          <h1 className="mt-2 font-display text-4xl text-ink sm:text-5xl">
            Academic Research Copilot
          </h1>
          <p className="mt-4 text-lg text-ink-muted">
            One product with cumulative features. Each task adds a capability—nothing replaces what
            came before.
          </p>
        </section>

        <section className="mt-10 grid gap-4 sm:grid-cols-2" aria-label="Features">
          {features.map((feature) => {
            const className =
              "rounded-3xl border border-line bg-white/70 p-5 shadow-[0_16px_40px_rgba(28,36,48,0.06)] backdrop-blur transition hover:border-accent/40";
            const content = (
              <>
                <p className="text-xs uppercase tracking-[0.16em] text-ink-muted">{feature.task}</p>
                <h2 className="mt-2 font-display text-2xl text-ink">{feature.title}</h2>
                <p className="mt-2 text-sm text-ink-muted">{feature.body}</p>
                {"disabled" in feature && feature.disabled ? (
                  <p className="mt-4 text-xs font-medium text-ink-muted">Coming soon</p>
                ) : (
                  <p className="mt-4 text-sm font-medium text-accent">Open feature →</p>
                )}
              </>
            );

            if ("disabled" in feature && feature.disabled) {
              return (
                <div key={feature.title} className={`${className} opacity-70`} aria-disabled="true">
                  {content}
                </div>
              );
            }

            return (
              <Link key={feature.title} href={feature.href} className={className}>
                {content}
              </Link>
            );
          })}
        </section>
      </main>
    </>
  );
}
