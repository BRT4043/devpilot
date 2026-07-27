"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { githubLoginUrl } from "@/lib/api";
import { getToken } from "@/lib/auth";
import Logo from "@/components/Logo";
import { CpuIcon, LinkIcon, MessageIcon } from "@/components/icons";

const STEPS = [
  {
    icon: LinkIcon,
    title: "Connect a repo",
    body: "Sign in with GitHub and pick any repo you have access to — no exact path typing required.",
  },
  {
    icon: CpuIcon,
    title: "DevPilot indexes it",
    body: "Every file is chunked and embedded so answers are grounded in your actual code, not guesses.",
  },
  {
    icon: MessageIcon,
    title: "Ask anything",
    body: "Get streamed, plain-language answers with clickable citations straight to the exact lines.",
  },
];

const FEATURES = [
  "Streaming answers",
  "Source citations",
  "Mermaid diagrams",
  "AI Tech Lead mode",
  "Debug assistant",
  "Interview questions",
];

export default function LandingPage() {
  const router = useRouter();
  const [checked, setChecked] = useState(false);
  const spotlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (getToken()) {
      router.replace("/repos");
    } else {
      setChecked(true);
    }
  }, [router]);

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    spotlightRef.current?.style.setProperty("--spot-x", `${e.clientX - rect.left}px`);
    spotlightRef.current?.style.setProperty("--spot-y", `${e.clientY - rect.top}px`);
  }

  if (!checked) return null;

  return (
    <main
      onMouseMove={handleMouseMove}
      className="bg-grid relative flex flex-1 flex-col items-center overflow-hidden px-4 py-16"
    >
      <div
        ref={spotlightRef}
        className="pointer-events-none absolute inset-0 opacity-70 transition-opacity duration-300"
        style={{
          background:
            "radial-gradient(500px circle at var(--spot-x, 50%) var(--spot-y, 20%), rgba(59,130,246,0.14), transparent 70%)",
        }}
      />
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background: "radial-gradient(600px circle at 50% 10%, rgba(124,58,237,0.2), transparent 60%)",
        }}
      />

      <div className="relative flex flex-col items-center gap-6 text-center">
        <div className="animate-fade-in flex flex-col items-center gap-4">
          <Logo size={56} animated />
          <div className="space-y-3">
            <h1 className="text-gradient text-5xl font-bold tracking-tight">DevPilot AI</h1>
            <p className="max-w-lg text-neutral-400">
              Chat with your GitHub repository. Connect a repo, DevPilot indexes it, then ask it
              anything — every answer is grounded in your actual code.
            </p>
          </div>
        </div>

        <a
          href={githubLoginUrl()}
          style={{ animationDelay: "100ms" }}
          className="btn-press animate-fade-in flex items-center gap-2 rounded-lg bg-white px-5 py-2.5 font-medium text-black shadow-lg shadow-blue-500/10 transition-all hover:scale-[1.02] hover:opacity-90"
        >
          <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden>
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
          </svg>
          Login with GitHub
        </a>

        <div className="flex flex-wrap justify-center gap-2">
          {FEATURES.map((f, i) => (
            <span
              key={f}
              style={{ animationDelay: `${150 + i * 50}ms` }}
              className="animate-chip-in rounded-full border border-neutral-800 bg-neutral-950/60 px-3 py-1 text-xs text-neutral-400 backdrop-blur"
            >
              {f}
            </span>
          ))}
        </div>
      </div>

      <div className="relative mt-20 grid w-full max-w-4xl grid-cols-1 gap-4 sm:grid-cols-3">
        {STEPS.map(({ icon: Icon, title, body }, i) => (
          <div
            key={title}
            style={{ animationDelay: `${300 + i * 100}ms` }}
            className="animate-card-in hover-lift rounded-xl border border-neutral-800 bg-neutral-950/60 p-5 text-left backdrop-blur"
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
              <Icon />
            </span>
            <p className="mt-3 font-semibold text-neutral-100">{title}</p>
            <p className="mt-1 text-sm text-neutral-500">{body}</p>
          </div>
        ))}
      </div>
    </main>
  );
}
