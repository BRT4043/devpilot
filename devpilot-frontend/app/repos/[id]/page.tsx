"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  apiFetch,
  streamChat,
  type DebugResponse,
  type InterviewQuestionsResponse,
  type Message,
  type Repo,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import ChatMessage from "@/components/ChatMessage";
import IndexingStatus from "@/components/IndexingStatus";
import TypingIndicator from "@/components/TypingIndicator";
import StarterQuestions from "@/components/StarterQuestions";
import SessionSidebar from "@/components/SessionSidebar";
import ChatToolbar from "@/components/ChatToolbar";
import Toast from "@/components/Toast";
import Skeleton from "@/components/Skeleton";
import { SendIcon } from "@/components/icons";

const TEXTAREA_MAX_HEIGHT = 320;

export default function RepoChatPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const repoId = params.id;

  const [repo, setRepo] = useState<Repo | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streamingId, setStreamingId] = useState<string | null>(null);
  const [toolLoading, setToolLoading] = useState<"interview" | "debug" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const loadRepo = useCallback(async () => {
    try {
      const data = await apiFetch<Repo>(`/repos/${repoId}`);
      setRepo(data);
      return data;
    } catch (err) {
      if (err instanceof Error) setError(err.message);
      return null;
    }
  }, [repoId]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/");
      return;
    }
    loadRepo();
  }, [router, loadRepo]);

  useEffect(() => {
    const active = repo && (repo.index_status === "pending" || repo.index_status === "indexing");
    if (active && !pollRef.current) {
      pollRef.current = setInterval(loadRepo, 3000);
    } else if (!active && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [repo, loadRepo]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, toolLoading]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, TEXTAREA_MAX_HEIGHT)}px`;
  }, [input]);

  const ready = repo?.index_status === "ready";

  async function sendMessage(overrideText?: string) {
    const text = (overrideText ?? input).trim();
    if (!text || sending || !ready) return;

    const isNewSession = sessionId === null;
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      sources: null,
      token_count: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);
    setError(null);

    let assistantId: string | null = null;
    let accumulated = "";

    try {
      await streamChat(repoId, text, sessionId, (event) => {
        if (event.type === "meta") {
          assistantId = crypto.randomUUID();
          setStreamingId(assistantId);
          if (event.session_id) setSessionId(event.session_id);
          const placeholder: Message = {
            id: assistantId,
            role: "assistant",
            content: "",
            sources: event.sources ?? null,
            token_count: null,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, placeholder]);
        } else if (event.type === "chunk" && assistantId) {
          accumulated += event.text ?? "";
          const id = assistantId;
          setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, content: accumulated } : m)));
        } else if (event.type === "done") {
          if (isNewSession) setSidebarRefreshKey((k) => k + 1);
        } else if (event.type === "error") {
          setError(event.detail ?? "Something went wrong");
        }
      });
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setSending(false);
      setStreamingId(null);
      textareaRef.current?.focus();
    }
  }

  async function handleInterviewQuestions() {
    if (toolLoading || sending || !ready) return;
    setToolLoading("interview");
    setError(null);
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: "Generate interview questions for this repo",
        sources: null,
        token_count: null,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const res = await apiFetch<InterviewQuestionsResponse>(`/repos/${repoId}/interview-questions`, {
        method: "POST",
      });
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.questions,
          sources: null,
          token_count: res.tokens_used,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setToolLoading(null);
    }
  }

  async function handleDebug(errorText: string) {
    if (toolLoading || sending || !ready) return;
    setToolLoading("debug");
    setError(null);
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        role: "user",
        content: `Debug this error:\n\`\`\`\n${errorText}\n\`\`\``,
        sources: null,
        token_count: null,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const res = await apiFetch<DebugResponse>(`/repos/${repoId}/debug`, {
        method: "POST",
        body: JSON.stringify({ error_text: errorText }),
      });
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: res.analysis,
          sources: res.sources,
          token_count: res.tokens_used,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setToolLoading(null);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function handleNewChat() {
    setSessionId(null);
    setMessages([]);
    setError(null);
  }

  async function handleSelectSession(id: string) {
    if (id === sessionId) return;
    setError(null);
    try {
      const msgs = await apiFetch<Message[]>(`/sessions/${id}/messages`);
      setSessionId(id);
      setMessages(msgs);
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    }
  }

  const disabledReason = !ready
    ? repo?.index_status === "failed"
      ? "Indexing failed — retry from the repo list"
      : "Repository is still indexing"
    : undefined;

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 gap-4 px-4 py-6">
      {ready && (
        <SessionSidebar
          repoId={repoId}
          activeSessionId={sessionId}
          onSelect={handleSelectSession}
          onNewChat={handleNewChat}
          refreshKey={sidebarRefreshKey}
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        <div className="animate-fade-in flex items-center justify-between border-b border-neutral-800 pb-4">
          <div>
            <Link href="/repos" className="text-xs text-neutral-500 hover:text-neutral-300">
              ← All repos
            </Link>
            {repo ? (
              <h1 className="font-mono text-lg">{repo.github_full_name}</h1>
            ) : (
              <Skeleton className="mt-1 h-6 w-48" />
            )}
          </div>
          {repo && <IndexingStatus repo={repo} />}
        </div>

        <div className="flex flex-1 flex-col gap-4 overflow-y-auto py-2">
          {messages.length === 0 && !ready && (
            <p className="text-sm text-neutral-500">Waiting for indexing to finish before you can chat.</p>
          )}
          {messages.length === 0 && ready && <StarterQuestions onSelect={(q) => sendMessage(q)} />}
          {messages.map((m) => (
            <ChatMessage
              key={m.id}
              message={m}
              githubFullName={repo?.github_full_name ?? ""}
              commitSha={repo?.indexed_commit_sha ?? null}
              isStreaming={m.id === streamingId}
            />
          ))}
          {sending && streamingId === null && <TypingIndicator />}
          {toolLoading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {error && <Toast message={error} onDismiss={() => setError(null)} />}

        {ready && (
          <ChatToolbar
            onInterviewQuestions={handleInterviewQuestions}
            onDebug={handleDebug}
            disabled={sending || toolLoading !== null}
          />
        )}

        <div className="border-t border-neutral-800 pt-4" title={disabledReason}>
          <div className="group relative rounded-2xl border border-neutral-800 bg-neutral-950/80 shadow-lg shadow-black/20 backdrop-blur transition-all duration-200 focus-within:border-blue-600/60 focus-within:shadow-[0_0_0_3px_rgba(59,130,246,0.12)]">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!ready || sending}
              placeholder={ready ? "Ask about this repo…" : disabledReason}
              rows={1}
              className="scrollbar-thin block w-full resize-none bg-transparent py-3 pl-4 pr-14 text-sm leading-relaxed placeholder:text-neutral-600 focus:outline-none disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage()}
              disabled={!ready || sending || !input.trim()}
              aria-label="Send message"
              className="btn-press absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-white text-black transition-transform disabled:opacity-30 disabled:hover:scale-100 enabled:hover:scale-105"
            >
              {sending ? (
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-neutral-400 border-t-black" />
              ) : (
                <SendIcon />
              )}
            </button>
          </div>
          <p className="mt-1.5 px-1 text-[11px] text-neutral-600">Enter to send · Shift+Enter for a new line</p>
        </div>
      </div>
    </main>
  );
}
