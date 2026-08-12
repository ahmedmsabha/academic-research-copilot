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

export type Message = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  route?: "llm" | null;
  status?: string | null;
  provider?: string | null;
  model?: string | null;
  created_at: string;
};

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
  route: "llm";
  status: string;
};
