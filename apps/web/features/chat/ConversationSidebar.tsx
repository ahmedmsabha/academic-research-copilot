"use client";

import { conversationLabel } from "@/features/chat/conversationTitle";
import type { Conversation } from "@/types/api";

type ConversationSidebarProps = {
  conversations: Conversation[];
  activeId: string | null;
  loading: boolean;
  creating: boolean;
  error: string | null;
  onSelect: (conversationId: string) => void;
  onCreate: () => void;
};

function formatWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function ConversationSidebar({
  conversations,
  activeId,
  loading,
  creating,
  error,
  onSelect,
  onCreate,
}: ConversationSidebarProps) {
  return (
    <aside
      className="flex h-full min-h-[16rem] flex-col overflow-hidden rounded-3xl border border-line bg-white/70 shadow-[0_16px_40px_rgba(28,36,48,0.06)] backdrop-blur"
      aria-label="Conversation history"
    >
      <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
        <h2 className="font-display text-lg text-ink">Chats</h2>
        <button
          type="button"
          onClick={onCreate}
          disabled={creating}
          className="rounded-xl bg-accent px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {creating ? "Starting…" : "New chat"}
        </button>
      </div>

      {error ? (
        <p role="alert" className="mx-3 mt-3 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      ) : null}

      {loading ? (
        <p className="px-4 py-6 text-sm text-ink-muted" aria-busy="true">
          Loading conversations…
        </p>
      ) : conversations.length === 0 ? (
        <p className="px-4 py-6 text-sm text-ink-muted">
          No chats yet. Start one to keep history in this project.
        </p>
      ) : (
        <ul className="flex-1 overflow-y-auto p-2">
          {conversations.map((conversation) => {
            const active = conversation.id === activeId;
            return (
              <li key={conversation.id}>
                <button
                  type="button"
                  onClick={() => onSelect(conversation.id)}
                  aria-current={active ? "true" : undefined}
                  className={`mb-1 flex w-full flex-col rounded-2xl px-3 py-2.5 text-left transition ${
                    active
                      ? "bg-accent text-white"
                      : "text-ink hover:bg-accent-soft"
                  }`}
                >
                  <span className="line-clamp-2 text-sm font-medium">{conversationLabel(conversation)}</span>
                  <span className={`mt-1 text-xs ${active ? "text-white/80" : "text-ink-muted"}`}>
                    {formatWhen(conversation.created_at)}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}
