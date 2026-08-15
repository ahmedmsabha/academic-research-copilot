import type { Conversation } from "@/types/api";

export function conversationLabel(conversation: Conversation): string {
  const title = conversation.title.trim();
  return title.length > 0 ? title : "Untitled chat";
}
