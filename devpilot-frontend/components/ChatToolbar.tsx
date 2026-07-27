"use client";

import { useState } from "react";
import { QuestionIcon, TerminalIcon } from "./icons";

export default function ChatToolbar({
  onInterviewQuestions,
  onDebug,
  disabled,
}: {
  onInterviewQuestions: () => void;
  onDebug: (errorText: string) => void;
  disabled: boolean;
}) {
  const [debugOpen, setDebugOpen] = useState(false);
  const [errorText, setErrorText] = useState("");

  function submitDebug() {
    const text = errorText.trim();
    if (!text) return;
    onDebug(text);
    setErrorText("");
    setDebugOpen(false);
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <button
          onClick={onInterviewQuestions}
          disabled={disabled}
          className="btn-press hover-lift flex items-center gap-1.5 rounded-md border border-neutral-800 bg-neutral-950/60 px-3 py-1.5 text-xs font-medium text-neutral-300 backdrop-blur transition-colors hover:border-neutral-600 hover:text-white disabled:opacity-50"
        >
          <QuestionIcon />
          Interview Questions
        </button>
        <button
          onClick={() => setDebugOpen((v) => !v)}
          disabled={disabled}
          className={`btn-press hover-lift flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium backdrop-blur transition-colors disabled:opacity-50 ${
            debugOpen
              ? "border-neutral-600 bg-neutral-900 text-white"
              : "border-neutral-800 bg-neutral-950/60 text-neutral-300 hover:border-neutral-600 hover:text-white"
          }`}
        >
          <TerminalIcon />
          Debug Assistant
        </button>
      </div>
      {debugOpen && (
        <div className="animate-expand-down flex gap-2">
          <textarea
            value={errorText}
            onChange={(e) => setErrorText(e.target.value)}
            placeholder="Paste an error message or stack trace…"
            rows={3}
            className="flex-1 resize-none rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-xs font-mono placeholder:text-neutral-600 focus:border-neutral-600 focus:outline-none"
          />
          <button
            onClick={submitDebug}
            disabled={!errorText.trim() || disabled}
            className="btn-press self-end rounded-lg bg-white px-3 py-2 text-xs font-medium text-black disabled:opacity-50"
          >
            Analyze
          </button>
        </div>
      )}
    </div>
  );
}
