import { AppNav } from "@/components/AppNav";
import { PromptLabPanel } from "@/features/prompt-lab/PromptLabPanel";

export default function PromptLabPage() {
  return (
    <>
      <AppNav currentPath="/prompt-lab" />
      <main className="px-4 py-8 sm:px-6 sm:py-10">
        <header className="mx-auto w-full max-w-6xl">
          <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Task 4 · Prompt Lab</p>
          <h1 className="mt-2 font-display text-3xl text-ink sm:text-4xl">Prompt engineering playground</h1>
          <p className="mt-2 max-w-3xl text-sm text-ink-muted sm:text-base">
            Compare zero-shot, one-shot, few-shot, visible step-by-step, and structured-output
            prompting on the same question. Results show timing and usage when the model returns
            them; cost stays unavailable until a documented pricing formula exists.
          </p>
        </header>
        <div className="mt-8">
          <PromptLabPanel />
        </div>
      </main>
    </>
  );
}
