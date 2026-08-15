import { describe, expect, it } from "vitest";

import { conversationLabel } from "@/features/chat/conversationTitle";
import { loadSessionIds, saveSessionIds } from "@/features/chat/session";

describe("conversationLabel", () => {
  it("returns the stored title", () => {
    expect(
      conversationLabel({
        id: "c1",
        project_id: "p1",
        title: "What is RAG?",
        created_at: "2026-08-15T00:00:00.000Z",
      }),
    ).toBe("What is RAG?");
  });

  it("falls back when the title is blank", () => {
    expect(
      conversationLabel({
        id: "c1",
        project_id: "p1",
        title: "   ",
        created_at: "2026-08-15T00:00:00.000Z",
      }),
    ).toBe("Untitled chat");
  });
});

describe("workspace session keys", () => {
  it("stores workspace conversations separately from chat", () => {
    const memory = new Map<string, string>();
    const storage = {
      getItem: (key: string) => memory.get(key) ?? null,
      setItem: (key: string, value: string) => {
        memory.set(key, value);
      },
      removeItem: (key: string) => {
        memory.delete(key);
      },
    };
    Object.defineProperty(globalThis, "window", {
      value: { localStorage: storage },
      configurable: true,
    });

    saveSessionIds("project-1", "chat-1", "chat");
    saveSessionIds("project-1", "workspace-1", "workspace");

    expect(loadSessionIds("chat").conversationId).toBe("chat-1");
    expect(loadSessionIds("workspace").conversationId).toBe("workspace-1");
  });
});
