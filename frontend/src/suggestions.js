// Suggested questions come from config.py via /api/meta.
// Accepts {topic, question} objects or plain strings, and falls back to defaults.

const DEFAULTS = [
  { topic: "Life", question: "What are his interests?" },
  { topic: "Projects", question: "Tell me about the multilingual RAG system" },
  { topic: "Work", question: "What does he do at Business Analytics?" },
  { topic: "Skills", question: "What are his strongest skills?" },
  { topic: "Mobile apps", question: "Which Flutter apps has he built?" },
  { topic: "Contact", question: "How can I reach him?" },
];

export function getSuggestions(meta) {
  const list = meta?.suggestions?.length ? meta.suggestions : DEFAULTS;
  return list.map((s) => (typeof s === "string" ? { topic: null, question: s } : s));
}

// Follow-up chips in a chat: suggestions that haven't been asked yet.
export function getFollowUps(meta, messages, count = 3) {
  const asked = new Set(messages.filter((m) => m.role === "user").map((m) => m.content.trim().toLowerCase()));
  return getSuggestions(meta)
    .filter((s) => !asked.has(s.question.toLowerCase()))
    .slice(0, count);
}
