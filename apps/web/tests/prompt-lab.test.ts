import { describe, expect, it } from "vitest";

import {
  STRATEGY_LABELS,
  canRunPromptLab,
  formatUsage,
} from "@/features/prompt-lab/strategyMeta";

describe("Prompt Lab client helpers", () => {
  it("rejects blank comparison input", () => {
    expect(canRunPromptLab("   \n\t  ")).toBe(false);
    expect(canRunPromptLab("Why use RAG?")).toBe(true);
  });

  it("labels strategies without calling them hidden reasoning", () => {
    expect(STRATEGY_LABELS.chain_of_thought).toBe("Visible step-by-step");
    expect(STRATEGY_LABELS.structured).toBe("Structured output");
    expect(STRATEGY_LABELS.zero_shot).toBe("Zero-shot");
  });

  it("marks missing usage and cost as unavailable instead of inventing values", () => {
    expect(
      formatUsage({ elapsed_ms: 120, total_tokens: null, cost_usd: null }),
    ).toBe("120 ms · tokens unavailable · cost unavailable");
  });
});
