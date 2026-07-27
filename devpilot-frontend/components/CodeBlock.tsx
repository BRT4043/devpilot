"use client";

import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import MermaidDiagram from "./MermaidDiagram";

export default function CodeBlock({
  code,
  language,
  isStreaming,
}: {
  code: string;
  language: string;
  isStreaming: boolean;
}) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  // Wait for the message to finish streaming before attempting to render a diagram —
  // partial Mermaid syntax mid-stream would just fail to parse repeatedly.
  if (language === "mermaid" && !isStreaming) {
    return <MermaidDiagram code={code} />;
  }

  return (
    <div className="animate-card-in my-2 overflow-hidden rounded-lg border border-neutral-800">
      <div className="flex items-center justify-between bg-neutral-900 px-3 py-1.5 text-xs text-neutral-500">
        <span>{language || "code"}</span>
        <button onClick={handleCopy} className="btn-press text-neutral-400 hover:text-neutral-200">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        style={oneDark as any}
        language={language}
        PreTag="div"
        customStyle={{ margin: 0, borderRadius: 0 }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
