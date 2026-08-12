import { AppNav } from "@/components/AppNav";
import { ChatPanel } from "@/features/chat/ChatPanel";

export default function ChatPage() {
  return (
    <>
      <AppNav currentPath="/chat" />
      <main className="px-4 py-8 sm:px-6 sm:py-10">
        <ChatPanel
          eyebrow="Task 1 · Chat"
          title="General research chat"
          subtitle="Gemini-powered conversation with session history, loading states, and safe errors."
          mode="llm"
          showDocuments={false}
          conversationTitle="General chat"
          sessionKind="chat"
        />
      </main>
    </>
  );
}
