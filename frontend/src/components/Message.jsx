import { Check, Copy, RotateCcw } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const mdComponents = { a: (props) => <a {...props} target="_blank" rel="noreferrer" /> };

// While streaming, "**Bold te" would show raw asterisks; close it temporarily.
function closeOpenBold(text) {
  return (text.match(/\*\*/g) || []).length % 2 ? `${text}**` : text;
}

/**
 * Split an answer into intro text, labelled groups and closing text, so groups like
 * "**Professional**" + bullet list can be shown as side-by-side boxes.
 */
const LABEL = /^\s*(?:\*\*([^*]+?)\*\*:?|#{1,4}\s+(.+?))\s*$/;
const LIST_LINE = /^\s*(?:[-*+]|\d+\.)\s|^\s{2,}\S/;

export function splitAnswer(text) {
  const intro = [], outro = [], groups = [];
  let current = null;
  for (const line of text.split("\n")) {
    const label = line.match(LABEL);
    if (label) {
      current = { title: (label[1] || label[2]).trim(), lines: [] };
      groups.push(current);
    } else if (current && (!line.trim() || LIST_LINE.test(line))) {
      // "- **Label** – detail" becomes "- **Label** detail"; CSS puts the detail on its own line
      current.lines.push(line.replace(/^(\s*(?:[-*+]|\d+\.)\s+\*\*[^*]+\*\*)\s*[–—:-]\s*/, "$1 "));
    } else {
      current = null;
      (groups.length ? outro : intro).push(line);
    }
  }
  const usable = groups.filter((g) => g.lines.some((l) => l.trim()));
  return { intro: intro.join("\n").trim(), groups: usable, outro: outro.join("\n").trim() };
}

function Markdown({ text, streaming, className = "" }) {
  if (!text) return null;
  return (
    <div className={`answer ${streaming ? "streaming" : ""} ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
        {streaming ? closeOpenBold(text) : text}
      </ReactMarkdown>
    </div>
  );
}

function AnswerBody({ content, streaming }) {
  const { intro, groups, outro } = splitAnswer(content);
  if (!groups.length) return <Markdown text={content} streaming={streaming} />;

  const last = outro ? "outro" : `g${groups.length - 1}`;
  return (
    <>
      <Markdown text={intro} />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))]">
        {groups.map((g, i) => (
          <div key={`${g.title}-${i}`} className="flex flex-col gap-2 rounded-2xl bg-mist p-4">
            <h3 className="font-display text-[17px] font-semibold">{g.title}</h3>
            <Markdown text={g.lines.join("\n").trim()} streaming={streaming && last === `g${i}`} className="group-list" />
          </div>
        ))}
      </div>
      <Markdown text={outro} streaming={streaming && last === "outro"} />
    </>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {}
  };
  return (
    <button onClick={copy} className="ml-auto inline-flex items-center gap-1.5 rounded-md px-1.5 py-1 text-sm text-moss hover:text-ink">
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export default function Message({ message, onRetry, ownerName = "Faizan" }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-[22px] rounded-br-md bg-pine px-4 py-2.5 whitespace-pre-wrap text-mist sm:px-[18px]">
          {message.content}
        </p>
      </div>
    );
  }

  const { status, content, error } = message;
  const streaming = status === "streaming";
  const titles = [...new Set((message.sources ?? []).map((s) => s.title))];

  return (
    <article className="flex flex-col gap-3.5 rounded-[22px] border border-ridge bg-paper p-4 shadow-[0_18px_40px_-28px_rgb(20_36_32/0.35)] sm:p-7">
      <div className="flex items-center gap-2.5 text-sm text-moss">
        <span aria-hidden="true" className="grid h-[26px] w-[26px] place-items-center rounded-lg bg-pine font-display text-[13px] font-bold text-mist">F</span>
        {ownerName}'s assistant
      </div>

      {status === "thinking" && (
        <p className="thinking" role="status" aria-label="Writing an answer">
          <span /><span /><span />
        </p>
      )}

      {content && <AnswerBody content={content} streaming={streaming} />}

      {status === "error" && (
        <div className={`flex flex-wrap items-center gap-3 text-sm ${message.stopped ? "text-moss" : "text-danger"}`}>
          <span>{error}</span>
          {!message.stopped && (
            <button onClick={() => onRetry(message.id)} className="inline-flex items-center gap-1.5 font-medium text-pine hover:underline">
              <RotateCcw size={14} /> Try again
            </button>
          )}
        </div>
      )}

      {status === "done" && content && (
        <div className="flex flex-wrap items-center gap-2 border-t border-ridge pt-3 text-[13px]">
          {titles.map((t) => (
            <span key={t} className="rounded-full bg-pine-tint px-2.5 py-1 text-pine">{t}</span>
          ))}
          <CopyButton text={content} />
        </div>
      )}
    </article>
  );
}
