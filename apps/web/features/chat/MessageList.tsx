"use client";

import { MarkdownMessage } from "@/components/MarkdownMessage";
import type { Message } from "@/types/api";

type MessageListProps = {
  messages: Message[];
  isLoading: boolean;
  loadingStatus?: string | null;
  emptyTitle?: string;
  emptyDescription?: string;
};

export function MessageList({
  messages,
  isLoading,
  loadingStatus,
  emptyTitle = "Ask a research question",
  emptyDescription = "Start a conversation. Messages are saved to your project database and reload after refresh.",
}: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16 text-center">
        <div className="max-w-md">
          <p className="font-display text-2xl text-ink">{emptyTitle}</p>
          <p className="mt-3 text-ink-muted">{emptyDescription}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-6 sm:px-6" role="log" aria-live="polite">
      {messages.map((message) => {
        const isUser = message.role === "user";
        const citations = message.citations ?? [];
        return (
          <article
            key={message.id}
            className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            aria-label={isUser ? "Your message" : "Assistant message"}
          >
            <div
              className={`max-w-[min(720px,92%)] rounded-2xl px-4 py-3 shadow-sm ${
                isUser
                  ? "bg-[var(--user-bubble)] text-white"
                  : "border border-line bg-[var(--assistant-bubble)] text-ink"
              }`}
            >
              {!isUser && message.route === "rag" ? (
                <p className="mb-2 text-xs uppercase tracking-[0.14em] text-ink-muted">
                  {message.status ?? "Searching uploaded documents"}
                </p>
              ) : null}
              {isUser ? (
                <p className="whitespace-pre-wrap text-[0.95rem] leading-relaxed">{message.content}</p>
              ) : (
                <MarkdownMessage content={message.content} />
              )}
              {!isUser && citations.length > 0 ? (
                <footer className="mt-3 border-t border-line pt-3">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-ink-muted">
                    Sources
                  </p>
                  <ul className="mt-2 space-y-1">
                    {citations.map((citation) => (
                      <li key={`${citation.chunk_id}-${citation.label}`} className="text-sm text-ink">
                        {citation.label}
                      </li>
                    ))}
                  </ul>
                </footer>
              ) : null}
            </div>
          </article>
        );
      })}

      {isLoading ? (
        <div className="flex justify-start" aria-busy="true">
          <div className="rounded-2xl border border-line bg-white px-4 py-3 text-ink-muted shadow-sm">
            <span className="inline-flex items-center gap-2">
              <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
              {loadingStatus ?? "Generating response…"}
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}
