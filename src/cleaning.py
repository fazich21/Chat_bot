"""Clean extracted text before it is indexed.

- removes editing notes, date/author bylines and page footers
- removes [square brackets] but keeps the text inside them
- removes phone numbers and ID numbers so the bot can never reveal them
- finds leftover placeholders so you can fix them in your documents
"""
import re

# Paragraphs containing any of these phrases are notes to the author, not facts about you
EDITOR_NOTE_PHRASES = [
    "are placeholders to confirm",
    "are my best guess",
    "You didn't give me details",
    "The new paragraphs are written in general terms",
    "Change any that don't match",
    "REPLACE_ME",
]

FILL_IN_PROMPT = re.compile(r"^Add (any|a|your) .+ here\.?$", re.I)          # "Add any awards here."
BYLINE = re.compile(r"^[A-Z][a-z]{2} \d{1,2}, \d{4}\s*·\s*@\S+$")       # "Oct 13, 2026 · @faizanch"
PAGE_FOOTER = re.compile(r"^Page \d+ of \d+$", re.I)
ZERO_WIDTH = re.compile(r"[​‌‍﻿]")
BRACKETED = re.compile(r"\[([^\[\]\n]+)\](?!\()")                         # [text] but not [text](link)
OPTIONAL_PREFIX = re.compile(r"^\s*Optional:\s*", re.I)

# Sensitive numbers the bot must never see
PHONE = re.compile(r"(?<!\d)(?:\+?92[\s-]?|0)3\d{2}[\s-]?\d{7}(?!\d)"    # Pakistani mobile
                   r"|(?<!\d)\+\d[\d\s-]{8,14}\d(?!\d)")                  # international
CNIC = re.compile(r"(?<!\d)\d{5}-\d{7}-\d(?!\d)")
PHONE_LABEL_ONLY = re.compile(r"^(phone|mobile|cell|whatsapp|contact)\s*(no\.?|number)?\s*:?\s*$", re.I)

# Things that look like unfinished placeholders
PLACEHOLDER_HINTS = re.compile(
    r"your-|example\.com|X members|grade or outcome|\b(year)\b|open / not|"
    r"\[[^\]]*\s/\s[^\]]*\]|\[such as|\[and group\]|\[your answer\]", re.I)


def redact_sensitive(text: str) -> str:
    text = PHONE.sub("", text)
    return CNIC.sub("", text)


def _unwrap_brackets(text: str) -> str:
    return BRACKETED.sub(lambda m: OPTIONAL_PREFIX.sub("", m.group(1)), text)


def clean_text(text: str) -> str:
    text = ZERO_WIDTH.sub("", text)
    text = redact_sensitive(text)

    kept = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if BYLINE.match(para) or PAGE_FOOTER.match(para) or PHONE_LABEL_ONLY.match(para):
            continue
        if any(phrase.lower() in para.lower() for phrase in EDITOR_NOTE_PHRASES):
            continue
        para = re.sub(r"[ \t]{2,}", " ", _unwrap_brackets(para)).strip()
        if FILL_IN_PROMPT.match(para):
            continue
        kept.append(para)
    return "\n\n".join(kept)


def find_placeholders(raw_text: str) -> list[str]:
    """Return bracketed bits and lines that still look like unfinished placeholders."""
    found = []
    for match in BRACKETED.finditer(ZERO_WIDTH.sub("", raw_text)):
        snippet = match.group(0)
        if PLACEHOLDER_HINTS.search(snippet):
            found.append(snippet)
    return sorted(set(found))


EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def find_emails(raw_text: str) -> set[str]:
    return {e.lower().rstrip(".") for e in EMAIL.findall(raw_text) if "example.com" not in e}
