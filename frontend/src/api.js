// Talks to the FastAPI backend.

export async function fetchMeta() {
  const res = await fetch("/api/meta");
  if (!res.ok) throw new Error("Couldn't load the assistant's details.");
  return res.json();
}

/**
 * Sends a question and calls onEvent for every streamed event:
 *   { type: "sources", sources: [...] } | { type: "delta", text } | { type: "error", message } | { type: "done" }
 */
export async function streamChat({ message, history, signal, onEvent }) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
    signal,
  });

  if (!res.ok) {
    let detail = "The assistant isn't responding. Check that the server is running and try again.";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {}
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop();
    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)));
    }
  }
}
