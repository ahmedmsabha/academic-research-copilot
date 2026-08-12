const PROJECT_KEY = "arc.projectId";
const CONVERSATION_KEY = "arc.conversationId";
const CHAT_CONVERSATION_KEY = "arc.conversationId.chat";
const RAG_CONVERSATION_KEY = "arc.conversationId.rag";

export type SessionKind = "shared" | "chat" | "rag";

function conversationKey(kind: SessionKind): string {
  if (kind === "chat") {
    return CHAT_CONVERSATION_KEY;
  }
  if (kind === "rag") {
    return RAG_CONVERSATION_KEY;
  }
  return CONVERSATION_KEY;
}

export function loadSessionIds(
  kind: SessionKind = "shared",
): { projectId: string | null; conversationId: string | null } {
  if (typeof window === "undefined") {
    return { projectId: null, conversationId: null };
  }
  return {
    projectId: window.localStorage.getItem(PROJECT_KEY),
    conversationId: window.localStorage.getItem(conversationKey(kind)),
  };
}

export function saveSessionIds(
  projectId: string,
  conversationId: string,
  kind: SessionKind = "shared",
): void {
  window.localStorage.setItem(PROJECT_KEY, projectId);
  window.localStorage.setItem(conversationKey(kind), conversationId);
}

export function clearSessionIds(kind: SessionKind = "shared"): void {
  if (typeof window === "undefined") {
    return;
  }
  // Keep the shared project id for chat/rag failures so one broken conversation
  // does not wipe the whole workspace.
  if (kind === "shared") {
    window.localStorage.removeItem(PROJECT_KEY);
  }
  window.localStorage.removeItem(conversationKey(kind));
}
