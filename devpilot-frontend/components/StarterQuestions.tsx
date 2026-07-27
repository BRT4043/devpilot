import { AlertTriangleIcon, GridIcon, LayersIcon, PlusCircleIcon } from "./icons";

const QUESTIONS = [
  {
    icon: LayersIcon,
    label: "Overview",
    question: "What does this project do, in simple terms?",
  },
  {
    icon: GridIcon,
    label: "Architecture",
    question: "What are the main parts of this codebase?",
  },
  {
    icon: PlusCircleIcon,
    label: "Extend",
    question: "How would I add a new feature here?",
  },
  {
    icon: AlertTriangleIcon,
    label: "Risks",
    question: "Is there anything risky or fragile I should know about?",
  },
];

export default function StarterQuestions({ onSelect }: { onSelect: (q: string) => void }) {
  return (
    <div className="animate-fade-in flex flex-col items-center justify-center gap-5 py-10 text-center">
      <p className="text-sm text-neutral-500">Not sure where to start? Try one of these.</p>
      <div className="grid w-full max-w-xl grid-cols-1 gap-3 sm:grid-cols-2">
        {QUESTIONS.map(({ icon: Icon, label, question }, i) => (
          <button
            key={question}
            onClick={() => onSelect(question)}
            style={{ animationDelay: `${i * 70}ms` }}
            className="group animate-card-in hover-lift relative overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950/60 p-4 text-left backdrop-blur transition-colors hover:border-blue-600/50"
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
              style={{
                background: "radial-gradient(160px circle at 20% 20%, rgba(59,130,246,0.12), transparent 70%)",
              }}
            />
            <div className="relative flex items-center gap-2 text-neutral-500 transition-colors group-hover:text-blue-400">
              <Icon />
              <span className="text-[11px] font-medium uppercase tracking-wide">{label}</span>
            </div>
            <p className="relative mt-2 text-sm text-neutral-300 transition-colors group-hover:text-white">
              {question}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
