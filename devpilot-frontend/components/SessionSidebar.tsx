"use client";

import { useEffect, useState } from "react";
import { apiFetch, type ChatSession } from "@/lib/api";
import { formatRelativeTime } from "@/lib/time";
import Skeleton from "./Skeleton";

export default function SessionSidebar({
  repoId,
  activeSessionId,
  onSelect,
  onNewChat,
  refreshKey,
}: {
  repoId: string;
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onNewChat: () => void;
  refreshKey: number;
}) {
  const [sessions, setSessions] = useState<ChatSession[] | null>(null);

  useEffect(() => {
    apiFetch<ChatSession[]>(`/repos/${repoId}/sessions`)
      .then(setSessions)
      .catch(() => setSessions([]));
  }, [repoId, refreshKey]);

  return (
    <aside className="animate-fade-in flex w-56 shrink-0 flex-col gap-2 border-r border-neutral-800 pr-3">
      <button
        onClick={onNewChat}
        className="btn-press rounded-lg border border-neutral-700 px-3 py-2 text-sm font-medium text-neutral-200 transition-colors hover:border-neutral-500 hover:bg-neutral-900"
      >
        + New chat
      </button>
      <div className="flex flex-col gap-1 overflow-y-auto">
        {sessions === null && (
          <div className="flex flex-col gap-1.5 px-1 py-1">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        )}
        {sessions?.length === 0 && (
          <p className="px-2 py-1 text-xs text-neutral-600">No conversations yet.</p>
        )}
        {sessions?.map((s, i) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            style={{ animationDelay: `${i * 30}ms` }}
            className={`animate-card-in btn-press flex flex-col items-start rounded-lg px-2.5 py-2 text-left text-sm transition-colors ${
              s.id === activeSessionId
                ? "bg-neutral-800 text-white"
                : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-200"
            }`}
          >
            <span className="w-full truncate">{s.title || "New conversation"}</span>
            <span className="text-[11px] text-neutral-600">{formatRelativeTime(s.created_at)}</span>
          </button>
        ))}
      </div>
    </aside>
  );
}
