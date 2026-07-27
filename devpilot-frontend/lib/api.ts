import { clearToken, getToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/";
    throw new ApiError(401, "Not authenticated");
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response wasn't JSON, keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function githubLoginUrl(): string {
  return `${API_URL}/auth/github/login`;
}

export interface StreamEvent {
  type: "meta" | "chunk" | "done" | "error";
  session_id?: string;
  session_title?: string | null;
  sources?: Source[];
  text?: string;
  message_id?: string;
  token_count?: number;
  created_at?: string;
  detail?: string;
}

/** Streams a chat reply via SSE, invoking onEvent for each "meta"/"chunk"/"done"/"error" event. */
export async function streamChat(
  repoId: string,
  message: string,
  sessionId: string | null,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const token = getToken();
  const headers = new Headers();
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}/repos/${repoId}/chat/stream`, {
    method: "POST",
    headers,
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") window.location.href = "/";
    throw new ApiError(401, "Not authenticated");
  }

  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response wasn't JSON, keep statusText
    }
    throw new ApiError(res.status, detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const line = rawEvent.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(6)) as StreamEvent);
    }
  }
}

// --- Shared response types (match app/schemas/*.py) ---

export interface User {
  id: string;
  username: string;
  avatar_url: string | null;
}

export interface Repo {
  id: string;
  github_full_name: string;
  default_branch: string;
  index_status: "pending" | "indexing" | "ready" | "failed";
  index_error: string | null;
  indexed_commit_sha: string | null;
  file_count: number | null;
  chunk_count: number | null;
  created_at: string;
}

export interface Source {
  file_path: string;
  start_line: number;
  end_line: number;
  language: string;
  score: number;
}

export interface ChatSession {
  id: string;
  repo_id: string;
  title: string | null;
  created_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[] | null;
  token_count: number | null;
  created_at: string;
}

export interface ChatResponse {
  session: ChatSession;
  message: Message;
  sources: Source[];
}

export interface InterviewQuestionsResponse {
  questions: string;
  tokens_used: number;
  cached: boolean;
}

export interface DebugResponse {
  analysis: string;
  sources: Source[];
  tokens_used: number;
  cached: boolean;
}
