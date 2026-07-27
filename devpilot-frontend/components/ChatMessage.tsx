"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "@/lib/api";
import SourceList from "./SourceList";
import CodeBlock from "./CodeBlock";
import { formatRelativeTime } from "@/lib/time";

export default function ChatMessage({
  message,
  githubFullName,
  commitSha,
  isStreaming = false,
}: {
  message: Message;
  githubFullName: string;
  commitSha: string | null;
  isStreaming?: boolean;
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className={`flex animate-message-in flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`relative max-w-2xl rounded-2xl px-4 py-3 ${
          isUser ? "bg-blue-600 text-white" : "bg-neutral-900 text-neutral-100 border border-neutral-800"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown
              components={{
                code(props) {
                  const { children, className } = props;
                  const match = /language-(\w+)/.exec(className || "");
                  if (!match) {
                    return <code className={className}>{children}</code>;
                  }
                  return (
                    <CodeBlock
                      code={String(children).replace(/\n$/, "")}
                      language={match[1]}
                      isStreaming={isStreaming}
                    />
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {message.sources && message.sources.length > 0 && (
          <SourceList sources={message.sources} githubFullName={githubFullName} commitSha={commitSha} />
        )}
        {!isUser && message.content && (
          <button
            onClick={handleCopy}
            className="absolute -top-2.5 -right-2.5 rounded-full border border-neutral-700 bg-neutral-800 px-2 py-0.5 text-[10px] text-neutral-400 hover:text-neutral-200"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        )}
      </div>
      {!isStreaming && message.content && (
        <span className="px-1 text-[11px] text-neutral-600">{formatRelativeTime(message.created_at)}</span>
      )}
    </div>
  );
}
