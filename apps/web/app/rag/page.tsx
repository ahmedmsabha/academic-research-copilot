import { AppNav } from "@/components/AppNav";
import { ChatPanel } from "@/features/chat/ChatPanel";

export default function RagPage() {
  return (
    <>
      <AppNav currentPath="/rag" />
      <main className="px-4 py-8 sm:px-6 sm:py-10">
        <ChatPanel
          eyebrow="Task 2 · RAG"
          title="Documents & grounded answers"
          subtitle="Upload PDFs, wait for Ready, then ask questions cited to filename and page."
          mode="rag"
          showDocuments
          conversationTitle="Document chat"
          sessionKind="rag"
        />
      </main>
    </>
  );
}
