import { describe, expect, it } from "vitest";

import { normalizeApiBaseUrl } from "@/lib/api-base-url";

describe("normalizeApiBaseUrl", () => {
  it("keeps a bare origin", () => {
    expect(normalizeApiBaseUrl("https://ai.example.com")).toBe("https://ai.example.com");
    expect(normalizeApiBaseUrl("https://ai.example.com/")).toBe("https://ai.example.com");
  });

  it("strips accidental API or health suffixes", () => {
    expect(normalizeApiBaseUrl("https://ai.example.com/api")).toBe("https://ai.example.com");
    expect(normalizeApiBaseUrl("https://ai.example.com/api/")).toBe("https://ai.example.com");
    expect(normalizeApiBaseUrl("https://ai.example.com/api/v1")).toBe("https://ai.example.com");
    expect(normalizeApiBaseUrl("https://ai.example.com/health")).toBe("https://ai.example.com");
    expect(normalizeApiBaseUrl("https://ai.example.com/api/health")).toBe(
      "https://ai.example.com",
    );
  });

  it("rejects a relative value", () => {
    expect(() => normalizeApiBaseUrl("/api")).toThrow(/absolute URL/);
  });
});
