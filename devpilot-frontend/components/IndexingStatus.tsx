"use client";

import type { Repo } from "@/lib/api";

const STATUS_STYLES: Record<Repo["index_status"], string> = {
  pending: "bg-yellow-900 text-yellow-300",
  indexing: "bg-blue-900 text-blue-300",
  ready: "bg-green-900 text-green-300",
  failed: "bg-red-900 text-red-300",
};

export default function IndexingStatus({
  repo,
  onRetry,
}: {
  repo: Repo;
  onRetry?: () => void;
}) {
  const spinning = repo.index_status === "pending" || repo.index_status === "indexing";

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors duration-500 ${STATUS_STYLES[repo.index_status]}`}
        >
          {spinning && (
            <span className="animate-pulse-glow h-2 w-2 rounded-full bg-current" aria-hidden />
          )}
          {repo.index_status}
        </span>
        {repo.index_status === "ready" && (
          <span className="animate-chip-in text-xs text-neutral-400">
            {repo.file_count} files · {repo.chunk_count} chunks
          </span>
        )}
      </div>
      {repo.index_status === "failed" && (
        <div className="flex items-center gap-2">
          <p className="text-xs text-red-400 truncate max-w-xs" title={repo.index_error ?? undefined}>
            {repo.index_error}
          </p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="text-xs font-medium text-blue-400 hover:text-blue-300 underline"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
