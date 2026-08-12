import type {
  Conversation,
  Message,
  Project,
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

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": getUserId(),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
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
    throw new ApiError({ message, code, status: response.status, requestId });
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

  listMessages(conversationId: string): Promise<Message[]> {
    return apiFetch<Message[]>(`/api/v1/conversations/${conversationId}/messages`);
  },

  sendMessage(conversationId: string, content: string): Promise<SendMessageResponse> {
    return apiFetch<SendMessageResponse>(
      `/api/v1/conversations/${conversationId}/messages`,
      {
        method: "POST",
        body: JSON.stringify({ content }),
      },
    );
  },
};
