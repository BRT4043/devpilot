"use client";

import Link from "next/link";
import type { Repo } from "@/lib/api";
import IndexingStatus from "./IndexingStatus";

export default function RepoCard({
  repo,
  onRetry,
  onDelete,
  style,
}: {
  repo: Repo;
  onRetry: (id: string) => void;
  onDelete: (id: string) => void;
  style?: React.CSSProperties;
}) {
  const ready = repo.index_status === "ready";

  function handleDelete(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (window.confirm(`Remove ${repo.github_full_name} from DevPilot? This deletes its indexed data.`)) {
      onDelete(repo.id);
    }
  }

  const card = (
    <div
      style={style}
      className="animate-card-in hover-lift group flex items-center justify-between rounded-xl border border-neutral-800 bg-neutral-950 px-4 py-3 transition-colors hover:border-neutral-700 hover:shadow-lg hover:shadow-black/20"
    >
      <div>
        <p className="font-mono text-sm text-neutral-100">{repo.github_full_name}</p>
        <p className="text-xs text-neutral-500">{repo.default_branch}</p>
      </div>
      <div className="flex items-center gap-3">
        <IndexingStatus repo={repo} onRetry={() => onRetry(repo.id)} />
        <button
          onClick={handleDelete}
          className="btn-press rounded-md p-1.5 text-neutral-600 opacity-0 transition-opacity hover:bg-red-950 hover:text-red-400 group-hover:opacity-100"
          aria-label={`Remove ${repo.github_full_name}`}
          title="Remove repo"
        >
          🗑
        </button>
      </div>
    </div>
  );

  if (!ready) return card;

  return (
    <Link href={`/repos/${repo.id}`} className="block">
      {card}
    </Link>
  );
}
