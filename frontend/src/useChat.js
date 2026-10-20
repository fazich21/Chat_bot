import { useCallback, useRef, useState } from "react";
import { streamChat } from "./api";

let nextId = 1;
const HISTORY_LIMIT = 8; // messages sent back for follow-up questions

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const controller = useRef(null);

  const update = (id, change) =>
    setMessages((all) => all.map((m) => (m.id === id ? { ...m, ...change(m) } : m)));

  const send = useCallback(
    async (text) => {
      const question = text.trim();
      if (!question || busy) return;

      const history = messages
        .filter((m) => m.status !== "error" && m.content)
        .slice(-HISTORY_LIMIT)
        .map(({ role, content }) => ({ role, content }));

      const user = { id: nextId++, role: "user", content: question, status: "done" };
      const reply = { id: nextId++, role: "assistant", content: "", sources: [], status: "thinking", question };
      setMessages((all) => [...all, user, reply]);
      setBusy(true);
      controller.current = new AbortController();

      try {
        await streamChat({
          message: question,
          history,
          signal: controller.current.signal,
          onEvent: (e) => {
            if (e.type === "sources") update(reply.id, () => ({ sources: e.sources }));
            if (e.type === "delta") update(reply.id, (m) => ({ content: m.content + e.text, status: "streaming" }));
            if (e.type === "error") update(reply.id, () => ({ status: "error", error: e.message }));
            if (e.type === "done") update(reply.id, (m) => ({ status: m.status === "error" ? "error" : "done" }));
          },
        });
      } catch (err) {
        if (err.name === "AbortError") {
          update(reply.id, (m) => ({ status: m.content ? "done" : "error", error: "Stopped.", stopped: true }));
        } else {
          update(reply.id, () => ({ status: "error", error: err.message }));
        }
      } finally {
        setBusy(false);
        controller.current = null;
      }
    },
    [busy, messages]
  );

  const stop = useCallback(() => controller.current?.abort(), []);

  const reset = useCallback(() => {
    controller.current?.abort();
    setMessages([]);
  }, []);

  const retry = useCallback(
    (id) => {
      const failed = messages.find((m) => m.id === id);
      if (!failed) return;
      setMessages((all) => all.filter((m) => m.id !== id && !(m.role === "user" && m.id === id - 1)));
      setTimeout(() => send(failed.question), 0);
    },
    [messages, send]
  );

  return { messages, busy, send, stop, reset, retry };
}
