"use client";

import { useEffect, useState } from "react";

import { ChatComposer } from "@/features/chat/ChatComposer";
import { ConversationSidebar } from "@/features/chat/ConversationSidebar";
import { MessageList } from "@/features/chat/MessageList";
import { LOADING_STATUS } from "@/features/chat/routeStatus";
import { clearSessionIds, loadSessionIds, saveSessionIds } from "@/features/chat/session";
import { DocumentPanel } from "@/features/documents/DocumentPanel";
import { ApiError, api } from "@/lib/api";
import type { Conversation, Message, MessageRoutePreference } from "@/types/api";

type ChatPanelProps = {
  title: string;
  subtitle: string;
  eyebrow: string;
  mode?: MessageRoutePreference;
  showDocuments?: boolean;
  showHistory?: boolean;
  conversationTitle?: string;
  sessionKind?: "chat" | "rag" | "agent" | "workspace";
  examplePrompts?: string[];
};

export function ChatPanel({
  title,
  subtitle,
  eyebrow,
  mode = "auto",
  showDocuments = false,
  showHistory = false,
  conversationTitle = "Research chat",
  sessionKind = "chat",
  examplePrompts,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);
  const [sending, setSending] = useState(false);
  const [creatingChat, setCreatingChat] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  async function refreshConversations(nextProjectId: string) {
    if (!showHistory) {
      return;
    }
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const items = await api.listConversations(nextProjectId);
      setConversations(items);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Unable to load conversation history.";
      setHistoryError(message);
    } finally {
      setHistoryLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setBootstrapping(true);
      setError(null);
      try {
        const saved = loadSessionIds(sessionKind);
        let nextProjectId = saved.projectId;
        let nextConversationId = saved.conversationId;

        if (!nextProjectId) {
          const project = await api.createProject();
          nextProjectId = project.id;
        } else {
          const projects = await api.listProjects();
          const found = projects.some((project) => project.id === nextProjectId);
          if (!found) {
            const project = await api.createProject();
            nextProjectId = project.id;
            nextConversationId = null;
          }
        }

        if (showHistory) {
          const items = await api.listConversations(nextProjectId);
          if (cancelled) {
            return;
          }
          setConversations(items);
          const savedStillExists = items.some((item) => item.id === nextConversationId);
          if (!savedStillExists) {
            nextConversationId = items[0]?.id ?? null;
          }
        }

        if (!nextConversationId) {
          const conversation = await api.createConversation(nextProjectId, conversationTitle);
          nextConversationId = conversation.id;
          if (showHistory) {
            setConversations((prev) => [conversation, ...prev.filter((item) => item.id !== conversation.id)]);
          }
        }

        let history: Message[] = [];
        try {
          history = await api.listMessages(nextConversationId);
        } catch (err) {
          if (err instanceof ApiError && err.status === 404) {
            const conversation = await api.createConversation(nextProjectId, conversationTitle);
            nextConversationId = conversation.id;
            history = [];
          } else {
            throw err;
          }
        }

        if (cancelled) {
          return;
        }

        saveSessionIds(nextProjectId, nextConversationId, sessionKind);
        setProjectId(nextProjectId);
        setConversationId(nextConversationId);
        setMessages(history);
      } catch (err) {
        if (cancelled) {
          return;
        }
        clearSessionIds(sessionKind);
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
  }, [conversationTitle, sessionKind, showHistory]);

  async function handleSelectConversation(nextConversationId: string) {
    if (!projectId || nextConversationId === conversationId) {
      return;
    }
    setError(null);
    try {
      const history = await api.listMessages(nextConversationId);
      saveSessionIds(projectId, nextConversationId, sessionKind);
      setConversationId(nextConversationId);
      setMessages(history);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Unable to open that conversation.";
      setError(message);
    }
  }

  async function handleNewChat() {
    if (!projectId) {
      setError("Workspace is not ready yet.");
      return;
    }
    setCreatingChat(true);
    setError(null);
    try {
      const conversation = await api.createConversation(projectId, conversationTitle);
      saveSessionIds(projectId, conversation.id, sessionKind);
      setConversationId(conversation.id);
      setMessages([]);
      setConversations((prev) => [conversation, ...prev.filter((item) => item.id !== conversation.id)]);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Unable to start a new chat.";
      setError(message);
    } finally {
      setCreatingChat(false);
    }
  }

  async function handleSend(content: string) {
    if (!conversationId) {
      setError("Chat is not ready yet.");
      return;
    }

    setSending(true);
    setLoadingStatus(LOADING_STATUS[mode]);
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
      const result = await api.sendMessage(conversationId, content, mode);
      setLoadingStatus(result.status);
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((message) => message.id !== optimistic.id);
        return [...withoutOptimistic, result.user_message, result.assistant_message];
      });
      if (projectId) {
        await refreshConversations(projectId);
      }
    } catch (err) {
      setMessages((prev) => prev.filter((message) => message.id !== optimistic.id));
      const message =
        err instanceof ApiError ? err.message : "Failed to send message. Please try again.";
      setError(message);
    } finally {
      setSending(false);
      setLoadingStatus(null);
    }
  }

  const chatSection = (
    <section className="flex h-[min(820px,calc(100vh-7rem))] flex-col overflow-hidden rounded-3xl border border-line bg-white/70 shadow-[0_20px_60px_rgba(28,36,48,0.08)] backdrop-blur">
      <header className="border-b border-line px-5 py-4 sm:px-6">
        <p className="text-xs uppercase tracking-[0.18em] text-ink-muted">{eyebrow}</p>
        <h1 className="font-display text-2xl text-ink sm:text-3xl">{title}</h1>
        <p className="mt-1 text-sm text-ink-muted">{subtitle}</p>
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
        <MessageList
          messages={messages}
          isLoading={sending}
          loadingStatus={loadingStatus}
          emptyTitle={
            mode === "rag"
              ? "Ask about your documents"
              : mode === "auto"
                ? "Ask — the assistant will pick a tool"
                : "Ask a research question"
          }
          emptyDescription={
            mode === "rag"
              ? "Upload a PDF, then ask about it. Answers use retrieved document context and show filename and page citations when evidence is found."
              : mode === "auto"
                ? "Try a document question, arithmetic, weather, or “search the web for…”. Status shows which tool ran — never hidden model reasoning."
                : "Start a conversation. Messages are saved to your project database and reload after refresh."
          }
        />
      )}

      <ChatComposer
        disabled={bootstrapping || sending || !conversationId}
        onSend={handleSend}
        examplePrompts={examplePrompts}
      />
    </section>
  );

  const historySection = showHistory ? (
    <div className="lg:h-[min(820px,calc(100vh-7rem))]">
      <ConversationSidebar
        conversations={conversations}
        activeId={conversationId}
        loading={bootstrapping || historyLoading}
        creating={creatingChat}
        error={historyError}
        onSelect={(id) => {
          void handleSelectConversation(id);
        }}
        onCreate={() => {
          void handleNewChat();
        }}
      />
    </div>
  ) : null;

  const documentsSection = showDocuments ? (
    <div className="lg:h-[min(820px,calc(100vh-7rem))]">
      <DocumentPanel projectId={projectId} />
    </div>
  ) : null;

  if (!showDocuments && !showHistory) {
    return <div className="mx-auto w-full max-w-4xl">{chatSection}</div>;
  }

  const layoutClass = showHistory && showDocuments
    ? "mx-auto grid w-full max-w-[88rem] gap-6 lg:grid-cols-[minmax(220px,260px)_minmax(0,1fr)_minmax(260px,320px)]"
    : showHistory
      ? "mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(220px,260px)_minmax(0,1fr)]"
      : "mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1fr)_320px]";

  return (
    <div className={layoutClass}>
      {historySection}
      {chatSection}
      {documentsSection}
    </div>
  );
}
