import type { Source } from "@/lib/api";

export default function SourceList({
  sources,
  githubFullName,
  commitSha,
}: {
  sources: Source[];
  githubFullName: string;
  commitSha: string | null;
}) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {sources.map((s, i) => {
        const label = `${s.file_path}:${s.start_line}-${s.end_line}`;
        const href = commitSha
          ? `https://github.com/${githubFullName}/blob/${commitSha}/${s.file_path}#L${s.start_line}-L${s.end_line}`
          : undefined;
        const style = { animationDelay: `${i * 40}ms` };
        const chip = (
          <span
            style={style}
            className="hover-lift animate-chip-in inline-block rounded-full bg-neutral-800 px-2.5 py-1 text-xs font-mono text-neutral-300 transition-colors hover:bg-neutral-700"
          >
            {label}
          </span>
        );
        return href ? (
          <a key={i} href={href} target="_blank" rel="noopener noreferrer">
            {chip}
          </a>
        ) : (
          <span key={i}>{chip}</span>
        );
      })}
    </div>
  );
}
