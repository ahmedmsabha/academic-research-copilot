"use client";

import { FormEvent, useEffect, useState } from "react";

import { MarkdownMessage } from "@/components/MarkdownMessage";
import { loadProjectId, saveProjectId } from "@/features/chat/session";
import {
  STRATEGY_LABELS,
  canRunPromptLab,
  formatUsage,
} from "@/features/prompt-lab/strategyMeta";
import { ApiError, api } from "@/lib/api";
import type {
  PromptExperiment,
  PromptExperimentRun,
  PromptLibrary,
} from "@/types/api";

const EXAMPLE_PROMPTS = [
  "Why do researchers use retrieval-augmented generation instead of relying only on a model's training data?",
  "What is the difference between correlation and causation in a student lab report?",
  "How should a student write a focused research question?",
];

const RATING_FIELDS = [
  { key: "rating_accuracy", label: "Accuracy" },
  { key: "rating_clarity", label: "Clarity" },
  { key: "rating_research_usefulness", label: "Research usefulness" },
] as const;

type RatingKey = (typeof RATING_FIELDS)[number]["key"];

export function PromptLabPanel() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [library, setLibrary] = useState<PromptLibrary | null>(null);
  const [history, setHistory] = useState<PromptExperimentRun[]>([]);
  const [activeRun, setActiveRun] = useState<PromptExperimentRun | null>(null);
  const [input, setInput] = useState("");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setBootstrapping(true);
      setError(null);
      try {
        let nextProjectId = loadProjectId();
        if (!nextProjectId) {
          const project = await api.createProject();
          nextProjectId = project.id;
        } else {
          const projects = await api.listProjects();
          const found = projects.some((project) => project.id === nextProjectId);
          if (!found) {
            const project = await api.createProject();
            nextProjectId = project.id;
          }
        }
        saveProjectId(nextProjectId);

        const [promptLibrary, listed] = await Promise.all([
          api.getPromptLibrary(),
          api.listPromptExperiments(nextProjectId),
        ]);
        if (cancelled) {
          return;
        }
        setProjectId(nextProjectId);
        setLibrary(promptLibrary);
        setHistory(listed.runs);
        setActiveRun(listed.runs[0] ?? null);
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message =
          err instanceof ApiError
            ? err.message
            : "Unable to start Prompt Lab. Is the AI service running?";
        setError(message);
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function runComparison(raw: string) {
    if (!projectId || !canRunPromptLab(raw) || running) {
      return;
    }
    setRunning(true);
    setStatus("Comparing prompting strategies");
    setError(null);
    try {
      const run = await api.runPromptExperiments(projectId, raw.trim());
      setActiveRun(run);
      setHistory((prev) => [run, ...prev.filter((item) => item.run_id !== run.run_id)]);
      setInput("");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to run the comparison. Please try again.";
      setError(message);
    } finally {
      setRunning(false);
      setStatus(null);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runComparison(input);
  }

  async function handleRate(experiment: PromptExperiment, key: RatingKey, value: number) {
    if (!experiment.id) {
      return;
    }
    setError(null);
    try {
      const updated = await api.ratePromptExperiment(experiment.id, { [key]: value });
      setActiveRun((current) => {
        if (!current) {
          return current;
        }
        return {
          ...current,
          results: current.results.map((item) => (item.id === updated.id ? updated : item)),
        };
      });
      setHistory((prev) =>
        prev.map((run) =>
          run.run_id === updated.run_id
            ? {
                ...run,
                results: run.results.map((item) => (item.id === updated.id ? updated : item)),
              }
            : run,
        ),
      );
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to save the rating. Please try again.";
      setError(message);
    }
  }

  const trimmed = input.trim();
  const canSubmit = !bootstrapping && !running && Boolean(projectId) && canRunPromptLab(trimmed);

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      {error ? (
        <div
          role="alert"
          className="rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger"
        >
          {error}
        </div>
      ) : null}

      {bootstrapping ? (
        <div
          className="rounded-3xl border border-line bg-white/70 px-5 py-16 text-center text-ink-muted"
          aria-busy="true"
        >
          Preparing Prompt Lab…
        </div>
      ) : (
        <>
          <section className="rounded-3xl border border-line bg-white/70 p-5 shadow-[0_16px_40px_rgba(28,36,48,0.06)] backdrop-blur sm:p-6">
            <h2 className="font-display text-xl text-ink">When each technique tends to work</h2>
            <p className="mt-1 text-sm text-ink-muted">
              Same user input, independent runs, equivalent model settings. Structured output shows
              parsed fields only — never hidden chain-of-thought.
            </p>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <caption className="sr-only">Prompting strategy comparison</caption>
                <thead>
                  <tr className="border-b border-line text-ink-muted">
                    <th scope="col" className="py-2 pr-4 font-medium">
                      Strategy
                    </th>
                    <th scope="col" className="py-2 pr-4 font-medium">
                      What it does
                    </th>
                    <th scope="col" className="py-2 font-medium">
                      When it performs better
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(library?.strategies ?? []).map((strategy) => (
                    <tr key={strategy.id} className="border-b border-line/70 align-top">
                      <th scope="row" className="py-3 pr-4 font-medium text-ink">
                        {strategy.name}
                      </th>
                      <td className="py-3 pr-4 text-ink-muted">{strategy.description}</td>
                      <td className="py-3 text-ink-muted">{strategy.when_better}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <form
            onSubmit={handleSubmit}
            className="rounded-3xl border border-line bg-white/70 p-5 shadow-[0_16px_40px_rgba(28,36,48,0.06)] backdrop-blur sm:p-6"
          >
            <label htmlFor="prompt-lab-input" className="text-sm font-medium text-ink">
              Compare the same research question
            </label>
            <textarea
              id="prompt-lab-input"
              name="prompt-lab-input"
              rows={4}
              value={input}
              disabled={running}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask a research question to compare prompting strategies…"
              className="mt-2 w-full resize-y rounded-xl border border-line bg-paper px-3 py-2 text-ink outline-none ring-accent focus:ring-2 disabled:opacity-60"
            />
            <div className="mt-3 flex flex-wrap gap-2" aria-label="Example questions">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  disabled={running}
                  onClick={() => void runComparison(prompt)}
                  className="rounded-full border border-line bg-paper px-3 py-1.5 text-left text-xs text-ink transition hover:border-accent/50 hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={!canSubmit}
                className="rounded-xl bg-accent px-4 py-2.5 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {running ? "Comparing…" : "Run comparison"}
              </button>
              {status ? (
                <p className="text-sm text-ink-muted" aria-live="polite">
                  {status}
                </p>
              ) : (
                <p className="text-sm text-ink-muted">
                  Runs zero-shot, one-shot, few-shot, visible step-by-step, and structured output.
                </p>
              )}
            </div>
          </form>

          {running && !activeRun ? (
            <div className="rounded-3xl border border-line bg-white/70 px-5 py-12 text-center text-ink-muted">
              Comparing prompting strategies…
            </div>
          ) : null}

          {activeRun ? (
            <section aria-live="polite">
              <h2 className="font-display text-xl text-ink">Results</h2>
              <p className="mt-1 text-sm text-ink-muted">Input: {activeRun.input}</p>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                {activeRun.results.map((result) => (
                  <article
                    key={`${result.run_id}-${result.strategy}`}
                    className="flex flex-col rounded-3xl border border-line bg-white/80 p-5 shadow-[0_16px_40px_rgba(28,36,48,0.06)]"
                  >
                    <header className="border-b border-line pb-3">
                      <p className="text-xs uppercase tracking-[0.16em] text-ink-muted">
                        {STRATEGY_LABELS[result.strategy]}
                      </p>
                      <p className="mt-1 text-xs text-ink-muted">
                        {result.template_version}
                        {result.model ? ` · ${result.model}` : ""}
                        {result.provider ? ` · ${result.provider}` : ""}
                      </p>
                      <p className="mt-1 text-xs text-ink-muted">
                        {formatUsage({
                          elapsed_ms: result.elapsed_ms,
                          total_tokens: result.total_tokens,
                          cost_usd: result.cost_usd,
                        })}
                      </p>
                    </header>
                    <div className="mt-3 flex-1 text-sm text-ink">
                      {result.error_message ? (
                        <p className="text-danger">{result.error_message}</p>
                      ) : (
                        <MarkdownMessage content={result.output} />
                      )}
                    </div>
                    {result.id && !result.error_message ? (
                      <fieldset className="mt-4 border-t border-line pt-3">
                        <legend className="text-xs font-medium text-ink-muted">Ratings (1–5)</legend>
                        <div className="mt-2 grid gap-2 sm:grid-cols-3">
                          {RATING_FIELDS.map((field) => (
                            <label key={field.key} className="text-xs text-ink-muted">
                              {field.label}
                              <select
                                className="mt-1 w-full rounded-lg border border-line bg-paper px-2 py-1 text-sm text-ink"
                                value={result[field.key] ?? ""}
                                aria-label={`${STRATEGY_LABELS[result.strategy]} ${field.label}`}
                                onChange={(event) => {
                                  const next = Number(event.target.value);
                                  if (!Number.isFinite(next)) {
                                    return;
                                  }
                                  void handleRate(result, field.key, next);
                                }}
                              >
                                <option value="">—</option>
                                {[1, 2, 3, 4, 5].map((score) => (
                                  <option key={score} value={score}>
                                    {score}
                                  </option>
                                ))}
                              </select>
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          ) : !running ? (
            <section className="rounded-3xl border border-line bg-white/70 px-5 py-12 text-center">
              <h2 className="font-display text-xl text-ink">No comparison yet</h2>
              <p className="mt-2 text-sm text-ink-muted">
                Enter a question or pick an example. Each strategy runs independently with the same
                input.
              </p>
            </section>
          ) : null}

          {library ? (
            <details className="rounded-3xl border border-line bg-white/70 p-5">
              <summary className="cursor-pointer font-display text-lg text-ink">
                Prompt library ({library.version})
              </summary>
              <p className="mt-2 text-sm text-ink-muted">
                Versioned templates used for this comparison. Chat/RAG system prompts are not shown.
              </p>
              <ul className="mt-4 space-y-4">
                {library.strategies.map((strategy) => (
                  <li key={strategy.id}>
                    <h3 className="text-sm font-medium text-ink">{strategy.name}</h3>
                    <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded-xl bg-paper-deep px-3 py-3 text-xs text-ink">
                      {strategy.user_template}
                    </pre>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}

          {history.length > 1 ? (
            <section>
              <h2 className="font-display text-xl text-ink">Earlier runs</h2>
              <ul className="mt-3 space-y-2">
                {history.slice(1).map((run) => (
                  <li key={run.run_id}>
                    <button
                      type="button"
                      className="w-full rounded-xl border border-line bg-white/70 px-4 py-3 text-left text-sm text-ink hover:border-accent/40"
                      onClick={() => setActiveRun(run)}
                    >
                      {run.input}
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
