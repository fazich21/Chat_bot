"""Split cleaned Markdown-style text into chunks, one per section where possible."""
import re
from dataclasses import asdict, dataclass

import config


@dataclass
class Chunk:
    id: int
    text: str      # what gets embedded and sent to the LLM (includes a "[Title > Section]" label)
    source: str    # file name
    title: str
    section: str

    def to_dict(self) -> dict:
        return asdict(self)


def _split_sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s]


def _pack(units: list[str], limit: int, joiner: str) -> list[str]:
    """Greedily join units (paragraphs or sentences) into pieces no longer than `limit`."""
    pieces, current = [], ""
    for unit in units:
        if current and len(current) + len(joiner) + len(unit) > limit:
            pieces.append(current)
            current = unit
        else:
            current = f"{current}{joiner}{unit}" if current else unit
    if current:
        pieces.append(current)
    return pieces


def split_long(text: str, limit: int) -> list[str]:
    """Split on paragraphs first, then on sentences for very long paragraphs."""
    if len(text) <= limit:
        return [text]
    units = []
    for para in re.split(r"\n\s*\n", text):
        if len(para) > limit:
            # keep sentences of one paragraph together as running text
            units.extend(_pack(_split_sentences(para), limit, " "))
        else:
            units.append(para)
    return _pack(units, limit, "\n\n")


def chunk_document(text: str, source: str, title: str, start_id: int = 0) -> list[Chunk]:
    sections: list[tuple[str, str]] = []
    current_heading, current_body = title, []

    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block.startswith("# ") or block == title:    # document title: not a section
            continue
        if block.startswith("## "):
            if current_body:
                sections.append((current_heading, "\n\n".join(current_body)))
            current_heading, current_body = block[3:].strip(), []
        elif block:
            current_body.append(block)
    if current_body:
        sections.append((current_heading, "\n\n".join(current_body)))

    chunks, next_id = [], start_id
    for heading, body in sections:
        label = title if heading == title else f"{title} > {heading}"
        for piece in split_long(body, config.MAX_CHUNK_CHARS):
            if len(piece) < config.MIN_CHUNK_CHARS:
                continue
            chunks.append(Chunk(id=next_id, text=f"[{label}]\n{piece}",
                                source=source, title=title, section=heading))
            next_id += 1
    return chunks
