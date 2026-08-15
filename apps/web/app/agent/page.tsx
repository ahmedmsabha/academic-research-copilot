import { AppNav } from "@/components/AppNav";
import { ChatPanel } from "@/features/chat/ChatPanel";

const EXAMPLE_PROMPTS = [
  "What is 12 * (3 + 4)?",
  "What's the weather in Paris?",
  "Search the web for retrieval-augmented generation",
];

export default function AgentPage() {
  return (
    <>
      <AppNav currentPath="/agent" />
      <main className="px-4 py-8 sm:px-6 sm:py-10">
        <ChatPanel
          eyebrow="Task 3 · Agent tools"
          title="Tool-calling agent"
          subtitle="The assistant chooses calculator, weather, web search, document retrieval, or a direct answer. Status is user-safe — not hidden reasoning."
          mode="auto"
          showDocuments={false}
          conversationTitle="Agent chat"
          sessionKind="agent"
          examplePrompts={EXAMPLE_PROMPTS}
        />
      </main>
    </>
  );
}
