const PROJECT_KEY = "arc.projectId";
const CONVERSATION_KEY = "arc.conversationId";
const CHAT_CONVERSATION_KEY = "arc.conversationId.chat";
const RAG_CONVERSATION_KEY = "arc.conversationId.rag";
const AGENT_CONVERSATION_KEY = "arc.conversationId.agent";
const WORKSPACE_CONVERSATION_KEY = "arc.conversationId.workspace";

export type SessionKind = "shared" | "chat" | "rag" | "agent" | "workspace";

function conversationKey(kind: SessionKind): string {
  if (kind === "chat") {
    return CHAT_CONVERSATION_KEY;
  }
  if (kind === "rag") {
    return RAG_CONVERSATION_KEY;
  }
  if (kind === "agent") {
    return AGENT_CONVERSATION_KEY;
  }
  if (kind === "workspace") {
    return WORKSPACE_CONVERSATION_KEY;
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
    projectId: loadProjectId(),
    conversationId: window.localStorage.getItem(conversationKey(kind)),
  };
}

export function loadProjectId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(PROJECT_KEY);
}

export function saveProjectId(projectId: string): void {
  window.localStorage.setItem(PROJECT_KEY, projectId);
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
