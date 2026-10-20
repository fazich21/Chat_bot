import { useEffect, useRef, useState } from "react";
import { fetchMeta } from "./api";
import Composer from "./components/Composer";
import Contours from "./components/Contours";
import Header from "./components/Header";
import Message from "./components/Message";
import Welcome from "./components/Welcome";
import { getFollowUps } from "./suggestions";
import { useChat } from "./useChat";

export default function App() {
  const [meta, setMeta] = useState(null);
  const { messages, busy, send, stop, reset, retry } = useChat();
  const bottom = useRef(null);
  const followScroll = useRef(true);

  useEffect(() => { fetchMeta().then(setMeta).catch(() => {}); }, []);

  // keep the newest text in view while streaming, unless the visitor scrolled up to read
  useEffect(() => {
    const onScroll = () => {
      followScroll.current = window.innerHeight + window.scrollY >= document.body.scrollHeight - 160;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  useEffect(() => {
    if (followScroll.current) bottom.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  const ask = (q) => { followScroll.current = true; send(q); };
  const empty = messages.length === 0;
  const first = meta?.first_name ?? "Faizan";
  const followUps = empty || busy ? [] : getFollowUps(meta, messages);

  return (
    <div className="relative flex min-h-dvh flex-col overflow-x-clip">
      <Contours className="absolute -top-10 -right-[330px] h-[380px] w-[640px] opacity-80 sm:-right-56 sm:h-[520px] sm:w-[900px]" />

      <Header meta={meta} onNewChat={reset} inChat={!empty} />

      <main className={`relative mx-auto w-full flex-1 px-4 pb-6 ${empty ? "max-w-5xl" : "max-w-[820px]"}`}>
        {empty ? (
          <Welcome meta={meta} onAsk={ask} />
        ) : (
          <div className="flex flex-col gap-5 pt-4 sm:gap-6 sm:pt-6" aria-live="polite">
            {messages.map((m) => <Message key={m.id} message={m} onRetry={retry} ownerName={first} />)}
          </div>
        )}
        <div ref={bottom} className="h-2 scroll-mb-[220px]" />
      </main>

      {/* Chat bar: a solid strip pinned to the bottom on phones, floating on larger screens */}
      <div className="sticky bottom-0 z-10 border-t border-ridge bg-paper/95 shadow-[0_-10px_24px_-18px_rgb(20_36_32/0.4)] backdrop-blur sm:border-ridge/60 sm:bg-mist/85 sm:pt-1 sm:shadow-none">
        <div className="mx-auto flex max-w-[820px] flex-col gap-2.5 px-3 pt-2.5 pb-[max(0.9rem,env(safe-area-inset-bottom))] sm:px-4">
          {followUps.length > 0 && (
            <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-0.5 [scrollbar-width:none]">
              {followUps.map((s) => (
                <button key={s.question} onClick={() => ask(s.question)}
                  className="shrink-0 rounded-full border border-ridge bg-paper px-3.5 py-1.5 text-sm transition-colors hover:border-pine/60">
                  {s.question}
                </button>
              ))}
            </div>
          )}
          <Composer onSend={ask} onStop={stop} busy={busy} maxChars={meta?.max_chars} first={first} />
          <p className="text-center text-xs text-moss">AI answers from {first}'s own notes; they can be wrong.</p>
        </div>
      </div>
    </div>
  );
}
