import { getSuggestions } from "../suggestions";

export default function Welcome({ meta, onAsk }) {
  const first = meta?.first_name ?? "Faizan";
  const suggestions = getSuggestions(meta);

  return (
    <section className="relative flex flex-col gap-6 pt-5 sm:gap-12 sm:pt-16">
      <div className="flex flex-col gap-2.5 sm:gap-4">
        <span className="inline-flex items-center gap-2 self-start rounded-full border border-ridge bg-paper px-3 py-1 text-[13px] text-moss">
          <span className="h-2 w-2 rounded-full bg-[#2E8B68]" />
          AI assistant, answers from his own notes
        </span>
        <h1 className="font-display text-[60px] leading-[0.88] font-bold tracking-[-0.045em] sm:text-[clamp(5rem,12vw,8rem)]">
          {first}
        </h1>
        <p className="max-w-[34ch] text-base text-moss sm:text-[clamp(17px,2.2vw,21px)]">
          {meta?.role ?? "AI Engineer"}. Ask about his work, projects, skills or life outside the office.
        </p>
      </div>

      {/* phones: 4 compact rows; larger screens: all tiles in a grid */}
      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-[repeat(auto-fill,minmax(min(100%,290px),1fr))] sm:gap-3">
        {suggestions.map((s, i) => (
          <li key={s.question} className={i >= 4 ? "max-sm:hidden" : ""}>
            <button
              onClick={() => onAsk(s.question)}
              className="flex h-full min-h-14 w-full flex-col gap-0.5 rounded-[14px] border border-ridge bg-paper px-3.5 py-2.5 text-left transition-colors hover:border-pine/60 hover:bg-pine-tint/40 sm:min-h-24 sm:rounded-[18px] sm:p-[18px]"
            >
              {s.topic && <span className="text-xs font-semibold text-pine">{s.topic}</span>}
              <span className="text-[15px] leading-snug sm:text-[17px]">{s.question}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
