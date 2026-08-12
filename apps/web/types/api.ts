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

export type MessageRoute = "llm" | "rag";

export type MessageRoutePreference = "auto" | "llm" | "rag";

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
  created_at: string;
};

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
  route: MessageRoute;
  status: string;
  citations: Citation[];
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
