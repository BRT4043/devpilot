export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1.5 rounded-2xl border border-neutral-800 bg-neutral-900 px-4 py-3.5">
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "0ms" }} />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "150ms" }} />
        <span className="typing-dot h-1.5 w-1.5 rounded-full bg-neutral-400" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}
