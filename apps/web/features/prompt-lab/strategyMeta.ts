import type { PromptStrategy } from "@/types/api";

export const STRATEGY_ORDER: PromptStrategy[] = [
  "zero_shot",
  "one_shot",
  "few_shot",
  "chain_of_thought",
  "structured",
];

export const STRATEGY_LABELS: Record<PromptStrategy, string> = {
  zero_shot: "Zero-shot",
  one_shot: "One-shot",
  few_shot: "Few-shot",
  chain_of_thought: "Visible step-by-step",
  structured: "Structured output",
};

export function canRunPromptLab(input: string): boolean {
  return input.trim().length > 0;
}

export function formatUsage(params: {
  elapsed_ms: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
}): string {
  const parts: string[] = [];
  if (params.elapsed_ms != null) {
    parts.push(`${params.elapsed_ms} ms`);
  }
  if (params.total_tokens != null) {
    parts.push(`${params.total_tokens} tokens`);
  } else {
    parts.push("tokens unavailable");
  }
  if (params.cost_usd == null) {
    parts.push("cost unavailable");
  } else {
    parts.push(`$${params.cost_usd.toFixed(4)}`);
  }
  return parts.join(" · ");
}
