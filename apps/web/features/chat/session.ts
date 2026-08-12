const PROJECT_KEY = "arc.projectId";
const CONVERSATION_KEY = "arc.conversationId";

export function loadSessionIds(): { projectId: string | null; conversationId: string | null } {
  if (typeof window === "undefined") {
    return { projectId: null, conversationId: null };
  }
  return {
    projectId: window.localStorage.getItem(PROJECT_KEY),
    conversationId: window.localStorage.getItem(CONVERSATION_KEY),
  };
}

export function saveSessionIds(projectId: string, conversationId: string): void {
  window.localStorage.setItem(PROJECT_KEY, projectId);
  window.localStorage.setItem(CONVERSATION_KEY, conversationId);
}

export function clearSessionIds(): void {
  window.localStorage.removeItem(PROJECT_KEY);
  window.localStorage.removeItem(CONVERSATION_KEY);
}
