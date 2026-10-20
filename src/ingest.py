"""Turn the files in data/ into clean chunks, and report problems in the data."""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import config
from src.chunking import Chunk, chunk_document
from src.cleaning import clean_text, find_emails, find_placeholders
from src.documents import list_data_files, read_document


@dataclass
class DataReport:
    files: dict[str, int] = field(default_factory=dict)              # file -> chunk count
    failed: dict[str, str] = field(default_factory=dict)             # file -> error
    placeholders: dict[str, list[str]] = field(default_factory=dict)  # file -> leftover placeholders
    emails: dict[str, set[str]] = field(default_factory=dict)        # email -> files mentioning it

    def warnings(self) -> list[str]:
        out = [f"Could not read {f}: {err}" for f, err in self.failed.items()]
        for f, items in self.placeholders.items():
            out.append(f"{f}: unfinished placeholders -> {', '.join(items)}")
        if len(self.emails) > 1:
            listed = "; ".join(f"{e} (in {', '.join(sorted(fs))})" for e, fs in self.emails.items())
            out.append(f"Different email addresses found, the bot may give the wrong one: {listed}")
        return out


def load_chunks(data_dir: Path = config.DATA_DIR) -> tuple[list[Chunk], DataReport]:
    chunks: list[Chunk] = []
    report = DataReport()
    for path in list_data_files(data_dir):
        try:
            doc = read_document(path)
        except Exception as exc:  # a broken file shouldn't stop the whole bot
            report.failed[path.name] = str(exc)
            continue

        if found := find_placeholders(doc.text):
            report.placeholders[path.name] = found
        for email in find_emails(doc.text):
            report.emails.setdefault(email, set()).add(path.name)

        new = chunk_document(clean_text(doc.text), doc.source, doc.title, start_id=len(chunks))
        chunks.extend(new)
        report.files[path.name] = len(new)
    return chunks, report


def data_fingerprint(data_dir: Path = config.DATA_DIR) -> str:
    """Hash of all data files + settings that affect the index. Changes trigger a rebuild."""
    h = hashlib.sha256()
    h.update(f"{config.EMBED_MODEL}|{config.MAX_CHUNK_CHARS}|{config.MIN_CHUNK_CHARS}".encode())
    for path in list_data_files(data_dir):
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()
