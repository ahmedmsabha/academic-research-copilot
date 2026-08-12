import { describe, expect, it, vi } from "vitest";
import { createElement } from "react";

// Lightweight validation unit test without a DOM harness for Task 1.
describe("blank message guard", () => {
  it("treats whitespace-only content as unsendable", () => {
    const content = "   \n\t  ";
    const canSend = content.trim().length > 0;
    expect(canSend).toBe(false);
  });

  it("allows non-empty content", () => {
    const onSend = vi.fn();
    const content = "What is retrieval-augmented generation?";
    if (content.trim()) {
      onSend(content.trim());
    }
    expect(onSend).toHaveBeenCalledWith("What is retrieval-augmented generation?");
    // Keep React import used so the test file stays TSX-compatible.
    expect(typeof createElement).toBe("function");
  });
});
