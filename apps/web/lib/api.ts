import type {
  Conversation,
  Document,
  Message,
  MessageRoutePreference,
  Project,
  PromptExperiment,
  PromptExperimentRun,
  PromptLibrary,
  PromptStrategy,
  SendMessageResponse,
} from "@/types/api";

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly requestId?: string;

  constructor(params: {
    message: string;
    code: string;
    status: number;
    requestId?: string;
  }) {
    super(params.message);
    this.name = "ApiError";
    this.code = params.code;
    this.status = params.status;
    this.requestId = params.requestId;
  }
}

function getBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new ApiError({
      message: "NEXT_PUBLIC_API_BASE_URL is not configured.",
      code: "CONFIG_ERROR",
      status: 500,
    });
  }
  return base.replace(/\/$/, "");
}

function getUserId(): string {
  if (typeof window === "undefined") {
    return "dev-user";
  }
  const key = "arc.userId";
  const existing = window.localStorage.getItem(key);
  if (existing) {
    return existing;
  }
  const created = `dev-user-${crypto.randomUUID().slice(0, 8)}`;
  window.localStorage.setItem(key, created);
  return created;
}

async function parseError(response: Response): Promise<ApiError> {
  let code = "HTTP_ERROR";
  let message = "Something went wrong. Please try again.";
  let requestId: string | undefined;
  try {
    const body = (await response.json()) as {
      error?: { code?: string; message?: string; request_id?: string };
    };
    code = body.error?.code ?? code;
    message = body.error?.message ?? message;
    requestId = body.error?.request_id;
  } catch {
    // Keep safe defaults when the body is not JSON.
  }
  return new ApiError({ message, code, status: response.status, requestId });
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("X-User-Id", getUserId());
  if (!headers.has("Content-Type") && !(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${getBaseUrl()}${path}`, {
      ...init,
      headers,
    });
  } catch {
    throw new ApiError({
      message: "Unable to reach the AI service. Is it running on the configured API URL?",
      code: "NETWORK_ERROR",
      status: 0,
    });
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  listProjects(): Promise<Project[]> {
    return apiFetch<Project[]>("/api/v1/projects");
  },

  createProject(name = "My Research Project"): Promise<Project> {
    return apiFetch<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  createConversation(projectId: string, title = "New chat"): Promise<Conversation> {
    return apiFetch<Conversation>(`/api/v1/projects/${projectId}/conversations`, {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  listConversations(projectId: string): Promise<Conversation[]> {
    return apiFetch<Conversation[]>(`/api/v1/projects/${projectId}/conversations`);
  },

  listMessages(conversationId: string): Promise<Message[]> {
    return apiFetch<Message[]>(`/api/v1/conversations/${conversationId}/messages`);
  },

  sendMessage(
    conversationId: string,
    content: string,
    mode: MessageRoutePreference = "auto",
  ): Promise<SendMessageResponse> {
    return apiFetch<SendMessageResponse>(
      `/api/v1/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content, mode }),
      },
    );
  },

  listDocuments(projectId: string): Promise<Document[]> {
    return apiFetch<Document[]>(`/api/v1/projects/${projectId}/documents`);
  },

  uploadDocument(projectId: string, file: File): Promise<Document> {
    const body = new FormData();
    body.append("file", file);
    return apiFetch<Document>(`/api/v1/projects/${projectId}/documents`, {
      method: "POST",
      body,
    });
  },

  retryDocument(projectId: string, documentId: string): Promise<Document> {
    return apiFetch<Document>(
      `/api/v1/projects/${projectId}/documents/${documentId}/retry`,
      { method: "POST" },
    );
  },

  deleteDocument(projectId: string, documentId: string): Promise<void> {
    return apiFetch<void>(`/api/v1/projects/${projectId}/documents/${documentId}`, {
      method: "DELETE",
    });
  },

  getPromptLibrary(): Promise<PromptLibrary> {
    return apiFetch<PromptLibrary>("/api/v1/prompt-library");
  },

  runPromptExperiments(
    projectId: string,
    input: string,
    strategies?: PromptStrategy[],
  ): Promise<PromptExperimentRun> {
    return apiFetch<PromptExperimentRun>(`/api/v1/projects/${projectId}/prompt-experiments`, {
      method: "POST",
      body: JSON.stringify({
        input,
        ...(strategies ? { strategies } : {}),
      }),
    });
  },

  listPromptExperiments(projectId: string): Promise<{ runs: PromptExperimentRun[] }> {
    return apiFetch<{ runs: PromptExperimentRun[] }>(
      `/api/v1/projects/${projectId}/prompt-experiments`,
    );
  },

  ratePromptExperiment(
    experimentId: string,
    ratings: {
      rating_accuracy?: number;
      rating_clarity?: number;
      rating_research_usefulness?: number;
    },
  ): Promise<PromptExperiment> {
    return apiFetch<PromptExperiment>(`/api/v1/prompt-experiments/${experimentId}`, {
      method: "PATCH",
      body: JSON.stringify(ratings),
    });
  },
};
