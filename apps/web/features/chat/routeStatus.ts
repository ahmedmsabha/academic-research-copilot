import type { MessageRoute, MessageRoutePreference } from "@/types/api";

export const ROUTE_STATUS: Record<MessageRoute, string> = {
  rag: "Searching uploaded documents",
  calculator: "Using calculator",
  web_search: "Searching the web",
  weather: "Checking weather",
  llm: "Generating response",
};

export const LOADING_STATUS: Record<MessageRoutePreference, string> = {
  auto: "Selecting a tool…",
  rag: "Searching uploaded documents…",
  calculator: "Using calculator…",
  web_search: "Searching the web…",
  weather: "Checking weather…",
  llm: "Generating response…",
};

export function isExternalRoute(route: MessageRoute | null | undefined): boolean {
  return route === "web_search" || route === "weather";
}

export function shouldShowRouteStatus(route: MessageRoute | null | undefined): boolean {
  return route === "rag" || route === "calculator" || route === "web_search" || route === "weather";
}
