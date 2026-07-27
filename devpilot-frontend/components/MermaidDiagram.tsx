"use client";

import { useEffect, useId, useRef, useState } from "react";

export default function MermaidDiagram({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replace(/:/g, "");
  const [error, setError] = useState<string | null>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    let cancelled = false;
    import("mermaid").then(async (mod) => {
      const mermaid = mod.default;
      mermaid.initialize({ startOnLoad: false, theme: "dark", securityLevel: "strict" });
      try {
        const { svg } = await mermaid.render(`mermaid-${id}`, code);
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          setError(null);
          setRendered(true);
        }
      } catch {
        if (!cancelled) setError("Couldn't render this diagram — showing raw source instead.");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [code, id]);

  if (error) {
    return (
      <div className="animate-card-in my-2 rounded-lg border border-neutral-800 bg-neutral-950 p-3">
        <p className="mb-2 text-xs text-neutral-500">{error}</p>
        <pre className="overflow-x-auto text-xs text-neutral-400">{code}</pre>
      </div>
    );
  }

  return (
    <div
      ref={ref}
      className={`my-2 flex justify-center overflow-x-auto rounded-lg border border-neutral-800 bg-neutral-950 p-4 transition-opacity duration-500 ${
        rendered ? "opacity-100" : "opacity-0"
      }`}
    />
  );
}
