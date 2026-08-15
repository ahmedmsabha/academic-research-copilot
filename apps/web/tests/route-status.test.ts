import { describe, expect, it } from "vitest";

import { isExternalRoute, ROUTE_STATUS, shouldShowRouteStatus } from "@/features/chat/routeStatus";

describe("agent route status", () => {
  it("exposes user-safe statuses without hidden reasoning", () => {
    expect(ROUTE_STATUS.calculator).toBe("Using calculator");
    expect(ROUTE_STATUS.weather).toBe("Checking weather");
    expect(ROUTE_STATUS.web_search).toBe("Searching the web");
  });

  it("labels weather and web search as external tools", () => {
    expect(isExternalRoute("weather")).toBe(true);
    expect(isExternalRoute("web_search")).toBe(true);
    expect(isExternalRoute("rag")).toBe(false);
    expect(isExternalRoute("calculator")).toBe(false);
  });

  it("shows status for tools and RAG, not general LLM chat", () => {
    expect(shouldShowRouteStatus("calculator")).toBe(true);
    expect(shouldShowRouteStatus("llm")).toBe(false);
  });
});
