"use client";

import { useEffect, useState } from "react";

import { ChatComposer } from "@/features/chat/ChatComposer";
import { MessageList } from "@/features/chat/MessageList";
import { clearSessionIds, loadSessionIds, saveSessionIds } from "@/features/chat/session";
import { ApiError, api } from "@/lib/api";
import type { Message } from "@/types/api";

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setBootstrapping(true);
      setError(null);
      try {
        const saved = loadSessionIds();
        let projectId = saved.projectId;
        let nextConversationId = saved.conversationId;

        if (!projectId) {
          const project = await api.createProject();
          projectId = project.id;
        } else {
          const projects = await api.listProjects();
          const found = projects.some((project) => project.id === projectId);
          if (!found) {
            const project = await api.createProject();
            projectId = project.id;
            nextConversationId = null;
          }
        }

        if (!nextConversationId) {
          const conversation = await api.createConversation(projectId, "Research chat");
          nextConversationId = conversation.id;
        }

        let history: Message[] = [];
        try {
          history = await api.listMessages(nextConversationId);
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            const conversation = await api.createConversation(projectId, "Research chat");
            nextConversationId = conversation.id;
            history = [];
          } else {
            throw err;
          }
        }

        if (cancelled) {
          return;
        }

        saveSessionIds(projectId, nextConversationId);
        setConversationId(nextConversationId);
        setMessages(history);
      } catch (err) {
        if (cancelled) {
          return;
        }
        clearSessionIds();
        const message =
          err instanceof ApiError
            ? err.message
            : "Unable to start chat. Is the AI service running?";
        setError(message);
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSend(content: string) {
    if (!conversationId) {
      setError("Chat is not ready yet.");
      return;
    }

    setSending(true);
    setError(null);

    const optimistic: Message = {
      id: `local-${crypto.randomUUID()}`,
      conversation_id: conversationId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const result = await api.sendMessage(conversationId, content);
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((message) => message.id !== optimistic.id);
        return [...withoutOptimistic, result.user_message, result.assistant_message];
      });
    } catch (err) {
      setMessages((prev) => prev.filter((message) => message.id !== optimistic.id));
      const message =
        err instanceof ApiError ? err.message : "Failed to send message. Please try again.";
      setError(message);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="mx-auto flex h-[min(820px,calc(100vh-7rem))] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-line bg-white/70 shadow-[0_20px_60px_rgba(28,36,48,0.08)] backdrop-blur">
      <header className="border-b border-line px-5 py-4 sm:px-6">
        <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">Task 1 · Chat</p>
        <h1 className="font-display text-2xl text-ink sm:text-3xl">Academic Research Copilot</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Gemini-powered conversation with session history, loading states, and safe errors.
        </p>
      </header>

      {error ? (
        <div
          role="alert"
          className="mx-4 mt-4 rounded-xl border border-danger/30 bg-danger-soft px-4 py-3 text-sm text-danger sm:mx-6"
        >
          {error}
        </div>
      ) : null}

      {bootstrapping ? (
        <div className="flex flex-1 items-center justify-center text-ink-muted" aria-busy="true">
          Preparing your workspace…
        </div>
      ) : (
        <MessageList messages={messages} isLoading={sending} />
      )}

      <ChatComposer disabled={bootstrapping || sending || !conversationId} onSend={handleSend} />
    </section>
  );
}
