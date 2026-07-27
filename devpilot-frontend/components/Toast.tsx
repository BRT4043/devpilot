"use client";

import { useEffect } from "react";

export default function Toast({
  message,
  onDismiss,
  durationMs = 5000,
}: {
  message: string;
  onDismiss: () => void;
  durationMs?: number;
}) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(timer);
  }, [message, durationMs, onDismiss]);

  return (
    <div className="animate-toast-in fixed bottom-5 left-1/2 z-50 flex max-w-md -translate-x-1/2 items-start gap-3 rounded-xl border border-red-900/50 bg-neutral-900 px-4 py-3 shadow-2xl">
      <span className="mt-0.5 text-red-400">⚠</span>
      <p className="flex-1 text-sm text-neutral-200">{message}</p>
      <button
        onClick={onDismiss}
        className="text-neutral-500 transition-colors hover:text-neutral-300"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}
