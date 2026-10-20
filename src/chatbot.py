"""The RAG chat logic: guard → retrieve → build prompt → stream answer from Groq → log.

`Chatbot.stream_events()` yields small dicts that the API sends to the browser:
    {"type": "sources", "sources": [...]}   which documents were used
    {"type": "delta",   "text": "..."}      next piece of the answer
    {"type": "done"}                         answer finished
"""
import json
import time
from collections.abc import Iterator

import config
from src.guard import check_input, clean_output
from src.retriever import Hit, Retriever

NO_INFO_MARKERS = ("don't have that information", "do not have that information",
                   "don't have information")
HOLD_BACK = 20  # characters kept back while streaming so a phone number can't slip out in pieces


class Chatbot:
    def __init__(self, retriever: Retriever | None = None, llm_client=None):
        self.retriever = retriever or Retriever.load_or_build()
        self.client = llm_client or self._make_groq_client()
        self.system_prompt = config.PROMPT_FILE.read_text(encoding="utf-8").strip()

    @staticmethod
    def _make_groq_client():
        if not config.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is not set. Put it in .env (local) or in the Space secrets.")
        from groq import Groq
        return Groq(api_key=config.GROQ_API_KEY)

    # ── prompt building ──────────────────────────────────────────────────
    @staticmethod
    def clean_history(history: list[dict] | None) -> list[dict]:
        """Keep only well-formed user/assistant text turns, trimmed to the recent ones."""
        clean = []
        for m in history or []:
            role, content = m.get("role"), m.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                clean.append({"role": role, "content": content[:config.MAX_HISTORY_MESSAGE_CHARS]})
        return clean[-config.HISTORY_TURNS * 2:]

    @staticmethod
    def search_query(question: str, history: list[dict]) -> str:
        """Short follow-ups ("tell me more", "which tech?") are searched together with the
        previous question so retrieval still knows the topic."""
        previous = [m["content"] for m in history if m["role"] == "user"]
        if previous and len(question.split()) <= 8:
            return f"{previous[-1]} {question}"
        return question

    @staticmethod
    def _format_context(hits: list[Hit]) -> str:
        if not hits:
            return "(No relevant information was found for this question.)"
        return "\n\n---\n\n".join(h.chunk.text for h in hits)

    def build_messages(self, question: str, history: list[dict]) -> tuple[list[dict], list[Hit]]:
        hits = self.retriever.search(self.search_query(question, history))
        system = f"{self.system_prompt}\n\nCONTEXT:\n{self._format_context(hits)}"
        return [{"role": "system", "content": system}, *history,
                {"role": "user", "content": question}], hits

    # ── answering ────────────────────────────────────────────────────────
    def stream_events(self, question: str, history: list[dict] | None = None) -> Iterator[dict]:
        question = (question or "").strip()
        history = self.clean_history(history)

        if (blocked := check_input(question)) is not None:
            yield {"type": "delta", "text": blocked}
            yield {"type": "done"}
            return

        messages, hits = self.build_messages(question, history)
        yield {"type": "sources", "sources": self._sources(hits)}

        raw, sent = "", 0
        try:
            for piece in self._stream_llm(messages):
                raw += piece
                safe = clean_output(raw)
                if len(safe) - HOLD_BACK > sent:
                    yield {"type": "delta", "text": safe[sent:len(safe) - HOLD_BACK]}
                    sent = len(safe) - HOLD_BACK
            final = clean_output(raw)
            if len(final) > sent:
                yield {"type": "delta", "text": final[sent:]}
            if not raw.strip():
                raw = "Sorry, I couldn't come up with an answer. Please try asking in a different way."
                yield {"type": "delta", "text": raw}
        except Exception as exc:
            print(f"LLM error: {type(exc).__name__}: {exc}")
            raw = self._error_message(exc)
            yield {"type": "error", "message": raw}
        finally:
            self._log(question, hits, raw)
        yield {"type": "done"}

    def answer(self, question: str, history: list[dict] | None = None) -> str:
        """Non-streaming helper (used by scripts and tests)."""
        parts = []
        for event in self.stream_events(question, history):
            if event["type"] == "delta":
                parts.append(event["text"])
            elif event["type"] == "error":
                parts.append(event["message"])
        return "".join(parts)

    def _stream_llm(self, messages: list[dict]) -> Iterator[str]:
        kwargs = dict(model=config.LLM_MODEL, messages=messages, temperature=config.TEMPERATURE,
                      max_completion_tokens=config.MAX_TOKENS, stream=True)
        if config.REASONING_EFFORT and "gpt-oss" in config.LLM_MODEL:
            kwargs["reasoning_effort"] = config.REASONING_EFFORT
        for part in self.client.chat.completions.create(**kwargs):
            if part.choices and part.choices[0].delta.content:
                yield part.choices[0].delta.content

    @staticmethod
    def _sources(hits: list[Hit]) -> list[dict]:
        seen, out = set(), []
        for h in hits:
            key = (h.chunk.title, h.chunk.section)
            if key not in seen:
                seen.add(key)
                out.append({"title": h.chunk.title, "section": h.chunk.section})
        return out

    @staticmethod
    def _error_message(exc: Exception) -> str:
        name = type(exc).__name__
        if "RateLimit" in name:
            return "I'm getting a lot of questions right now. Please try again in a minute."
        if "Connection" in name or "Timeout" in name:
            return "I couldn't reach my AI service. Please try again in a moment."
        if "Authentication" in name:
            return "The chatbot's API key isn't working. Faizan needs to check the GROQ_API_KEY setting."
        return f"Something went wrong on my side. You can also contact Faizan directly {config.CONTACT_HINT}."

    # ── logging ──────────────────────────────────────────────────────────
    @staticmethod
    def _log(question: str, hits: list[Hit], answer: str) -> None:
        """Append each question to logs/questions.jsonl so you can see what people ask
        and which questions the bot couldn't answer (= what to add to your documents)."""
        if not config.LOG_QUESTIONS:
            return
        try:
            config.LOG_DIR.mkdir(exist_ok=True)
            entry = {
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "question": question,
                "sources": sorted({h.chunk.source for h in hits}),
                "answered": bool(hits) and not any(m in answer.lower() for m in NO_INFO_MARKERS),
            }
            with open(config.LOG_DIR / "questions.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass  # logging must never break the chat
