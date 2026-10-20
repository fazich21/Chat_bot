import { ArrowUp, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export default function Composer({ onSend, onStop, busy, maxChars = 500, first = "Faizan" }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  // grow with the text, up to ~6 lines
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 168)}px`;
  }, [text]);

  const submit = (e) => {
    e?.preventDefault();
    if (busy || !text.trim()) return;
    onSend(text);
    setText("");
  };

  const nearLimit = text.length > maxChars * 0.8;

  return (
    <form onSubmit={submit}
      className="rounded-[26px] border-[1.5px] border-pine/70 bg-white p-1.5 pl-2 shadow-[0_16px_36px_-22px_rgb(20_36_32/0.45)] focus-within:border-pine dark:bg-paper">
      <div className="flex items-end gap-2">
        <label htmlFor="question" className="sr-only">Your question</label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={text}
          maxLength={maxChars}
          enterKeyHint="send"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) submit(e);
          }}
          placeholder={`Ask about ${first}`}
          className="max-h-42 flex-1 resize-none bg-transparent px-2.5 py-[11px] text-[16px] text-ink outline-none placeholder:text-moss/80 focus-visible:outline-none"
        />
        {busy ? (
          <button type="button" onClick={onStop} aria-label="Stop answering"
            className="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-ink text-mist transition-opacity hover:opacity-85">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button type="submit" disabled={!text.trim()} aria-label="Send"
            className="grid h-[46px] w-[46px] shrink-0 place-items-center rounded-full bg-pine text-mist transition-opacity enabled:hover:opacity-90 disabled:opacity-40">
            <ArrowUp size={19} strokeWidth={2.4} />
          </button>
        )}
      </div>
      {nearLimit && (
        <p className="px-3 pb-1 text-right text-xs text-moss">{text.length}/{maxChars}</p>
      )}
    </form>
  );
}
