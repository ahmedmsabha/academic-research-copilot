import { AppNav } from "@/components/AppNav";
import { ChatPanel } from "@/features/chat/ChatPanel";

const EXAMPLE_PROMPTS = [
  "What is 12 * (3 + 4)?",
  "What's the weather in Paris?",
  "Search the web for retrieval-augmented generation",
  "What do my uploaded documents say about the main claim?",
];

export default function WorkspacePage() {
  return (
    <>
      <AppNav currentPath="/workspace" />
      <main className="px-4 py-8 sm:px-6 sm:py-10">
        <ChatPanel
          eyebrow="Complete assistant"
          title="Research workspace"
          subtitle="One chat that can search your PDFs, use tools, or answer directly. History stays in this project. Status is user-safe — not hidden reasoning."
          mode="auto"
          showDocuments
          showHistory
          conversationTitle="New chat"
          sessionKind="workspace"
          examplePrompts={EXAMPLE_PROMPTS}
        />
      </main>
    </>
  );
}
