"""Cheap checks that run before and after the LLM, so abuse never costs API quota."""
import re
import time
from collections import defaultdict, deque

import config
from src.cleaning import redact_sensitive

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above|your) (instructions|rules)",
    r"(reveal|show|print|repeat|tell me) (me )?(your|the) (system )?(prompt|instructions|rules)",
    r"\bsystem prompt\b",
    r"you are (now|no longer)\b",
    r"\b(jailbreak|DAN mode|developer mode)\b",
    r"pretend (to be|you are) (?!faizan)",
    r"act as (?!faizan)(an?|the) ",
]
INJECTION = re.compile("|".join(INJECTION_PATTERNS), re.I)

REFUSAL_INJECTION = ("I'm here to answer questions about Faizan, his work, projects and interests, "
                     "so I can't change how I work. What would you like to know about him?")


class RateLimiter:
    """Allow at most `limit` messages per `window` seconds per visitor."""

    def __init__(self, limit: int = config.RATE_LIMIT_MESSAGES,
                 window: int = config.RATE_LIMIT_WINDOW_SECONDS):
        self.limit, self.window = limit, window
        self.events: dict[str, deque] = defaultdict(deque)

    def allow(self, visitor_id: str) -> bool:
        now = time.monotonic()
        q = self.events[visitor_id]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def check_input(message: str) -> str | None:
    """Return a reply to send instead of calling the LLM, or None if the message is fine."""
    if not message.strip():
        return "Please type a question."
    if len(message) > config.MAX_QUESTION_CHARS:
        return f"Please keep your question under {config.MAX_QUESTION_CHARS} characters."
    if INJECTION.search(message):
        return REFUSAL_INJECTION
    return None


def clean_output(text: str) -> str:
    """Last line of defence: strip any phone/ID number that slipped into an answer."""
    return redact_sensitive(text)
