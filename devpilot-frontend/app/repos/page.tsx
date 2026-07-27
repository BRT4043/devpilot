"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, type Repo } from "@/lib/api";
import { getToken } from "@/lib/auth";
import RepoCard from "@/components/RepoCard";
import Skeleton from "@/components/Skeleton";
import Toast from "@/components/Toast";

interface GitHubRepo {
  full_name: string;
  private: boolean;
  description: string | null;
}

export default function ReposPage() {
  const router = useRouter();
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [githubRepos, setGithubRepos] = useState<GitHubRepo[]>([]);
  const [fullName, setFullName] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadRepos = useCallback(async () => {
    try {
      const data = await apiFetch<Repo[]>("/repos");
      setRepos(data);
      return data;
    } catch (err) {
      if (err instanceof Error) setError(err.message);
      return null;
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/");
      return;
    }
    loadRepos();
    apiFetch<GitHubRepo[]>("/github/repos")
      .then(setGithubRepos)
      .catch(() => {
        // Non-critical — the picker just falls back to manual typing.
      });
  }, [router, loadRepos]);

  // Poll every 3s while any repo is pending/indexing.
  useEffect(() => {
    const active = repos?.some((r) => r.index_status === "pending" || r.index_status === "indexing");
    if (active && !pollRef.current) {
      pollRef.current = setInterval(loadRepos, 3000);
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
  }, [repos, loadRepos]);

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setConnecting(true);
    try {
      await apiFetch<Repo>("/repos", {
        method: "POST",
        body: JSON.stringify({ github_full_name: fullName.trim() }),
      });
      setFullName("");
      await loadRepos();
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    } finally {
      setConnecting(false);
    }
  }

  async function handleRetry(repoId: string) {
    try {
      await apiFetch<Repo>(`/repos/${repoId}/reindex`, { method: "POST" });
      await loadRepos();
    } catch (err) {
      if (err instanceof Error) setError(err.message);
    }
  }

  async function handleDelete(repoId: string) {
    setRepos((prev) => prev?.filter((r) => r.id !== repoId) ?? null);
    try {
      await apiFetch(`/repos/${repoId}`, { method: "DELETE" });
    } catch (err) {
      if (err instanceof Error) setError(err.message);
      await loadRepos();
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-10">
      <div className="animate-fade-in">
        <h1 className="text-2xl font-bold">Your repositories</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Connect a repo and DevPilot will index it so you can chat with it.
        </p>
      </div>

      <form onSubmit={handleConnect} className="animate-fade-in flex gap-2">
        <input
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="owner/repo"
          list="github-repo-options"
          required
          pattern="^[\w.\-]+/[\w.\-]+$"
          className="flex-1 rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
        />
        <datalist id="github-repo-options">
          {githubRepos.map((r) => (
            <option key={r.full_name} value={r.full_name}>
              {r.private ? "🔒 " : ""}
              {r.description ?? ""}
            </option>
          ))}
        </datalist>
        <button
          type="submit"
          disabled={connecting}
          className="btn-press rounded-lg bg-white px-4 py-2 text-sm font-medium text-black disabled:opacity-50"
        >
          {connecting ? "Connecting…" : "Connect"}
        </button>
      </form>
      {githubRepos.length > 0 && (
        <p className="animate-fade-in -mt-4 text-xs text-neutral-600">
          Start typing to pick from your {githubRepos.length} GitHub repos, or paste any owner/repo.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {repos === null && (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-[60px] w-full" />
            <Skeleton className="h-[60px] w-full" />
          </div>
        )}
        {repos?.length === 0 && (
          <p className="animate-fade-in text-sm text-neutral-500">
            No repos connected yet. Pick one above (e.g. <code>octocat/Hello-World</code>).
          </p>
        )}
        {repos?.map((repo, i) => (
          <RepoCard
            key={repo.id}
            repo={repo}
            onRetry={handleRetry}
            onDelete={handleDelete}
            style={{ animationDelay: `${i * 40}ms` }}
          />
        ))}
      </div>

      {error && <Toast message={error} onDismiss={() => setError(null)} />}
    </main>
  );
}
