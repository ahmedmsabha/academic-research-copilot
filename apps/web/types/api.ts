export type Project = {
  id: string;
  name: string;
  owner_user_id: string;
  created_at: string;
};

export type Conversation = {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
};

export type Citation = {
  document_id: string;
  chunk_id: string;
  filename: string;
  page_start: number | null;
  page_end: number | null;
  label: string;
};

export type MessageRoute = "llm" | "rag" | "calculator" | "web_search" | "weather";

export type MessageRoutePreference = "auto" | MessageRoute;

export type WebSource = {
  title: string;
  url: string;
  snippet: string | null;
  provider: string;
  retrieved_at: string | null;
};

export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  route?: MessageRoute | null;
  status?: string | null;
  provider?: string | null;
  model?: string | null;
  citations?: Citation[];
  web_sources?: WebSource[];
  created_at: string;
};

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
  route: MessageRoute;
  status: string;
  citations: Citation[];
  web_sources: WebSource[];
};

export type DocumentStatus =
  | "uploaded"
  | "queued"
  | "extracting"
  | "chunking"
  | "embedding"
  | "indexing"
  | "ready"
  | "failed";

export type Document = {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  page_count: number | null;
  status: DocumentStatus;
  failure_code: string | null;
  failure_message: string | null;
  created_at: string;
  updated_at: string;
};

export type PromptStrategy =
  | "zero_shot"
  | "one_shot"
  | "few_shot"
  | "chain_of_thought"
  | "structured";

export type PromptExperiment = {
  id: string | null;
  run_id: string;
  project_id: string;
  strategy: PromptStrategy;
  template_version: string;
  input: string;
  output: string;
  model: string | null;
  provider: string | null;
  elapsed_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  cost_usd: number | null;
  rating_accuracy: number | null;
  rating_clarity: number | null;
  rating_research_usefulness: number | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string | null;
};

export type PromptExperimentRun = {
  run_id: string;
  project_id: string;
  input: string;
  results: PromptExperiment[];
};

export type PromptLibraryStrategy = {
  id: PromptStrategy;
  name: string;
  description: string;
  when_better: string;
  user_template: string;
  template_version: string;
};

export type PromptLibrary = {
  version: string;
  strategies: PromptLibraryStrategy[];
};
