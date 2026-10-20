"""Tests for reading, cleaning and chunking (uses your real files in data/)."""
import config
from src.chunking import chunk_document, split_long
from src.cleaning import clean_text, find_placeholders, redact_sensitive
from src.documents import list_data_files, read_document
from src.ingest import load_chunks


def test_every_data_file_is_readable():
    files = list_data_files(config.DATA_DIR)
    assert files, "data/ is empty"
    for path in files:
        assert read_document(path).text.strip(), f"{path.name} produced no text"


def test_pdf_headings_are_detected():
    doc = read_document(config.DATA_DIR / "My Projects.pdf")
    assert "## 2. Multilingual RAG System (English, German, Urdu)" in doc.text
    assert "Page 1 of" not in doc.text


def test_phone_number_never_reaches_the_index():
    chunks, _ = load_chunks()
    everything = " ".join(c.text for c in chunks)
    assert "3938924" not in everything
    assert "Phone:" not in everything


def test_editor_notes_and_bylines_are_removed():
    chunks, _ = load_chunks()
    everything = " ".join(c.text for c in chunks)
    for junk in ["@faizanch", "best guess", "placeholders to confirm", "general terms", "Add any"]:
        assert junk not in everything, junk


def test_chunks_have_reasonable_size():
    chunks, _ = load_chunks()
    assert all(len(c.text) <= config.MAX_CHUNK_CHARS + 120 for c in chunks)  # +label
    assert all(c.text.startswith("[") for c in chunks)


def test_clean_text_unwraps_brackets_but_keeps_links():
    out = clean_text("Year: [2025]\n\nSee [my site](https://x.dev)")
    assert "Year: 2025" in out and "[my site](https://x.dev)" in out


def test_redact_sensitive():
    assert "0300" not in redact_sensitive("call 0300-1234567 or +92 300 1234567")
    assert redact_sensitive("born 2021 – 2025, CGPA 3.31") == "born 2021 – 2025, CGPA 3.31"
    assert "12345-1234567-1" not in redact_sensitive("CNIC 12345-1234567-1")


def test_find_placeholders():
    assert find_placeholders("email [your-email@example.com], year [2025]") == ["[your-email@example.com]"]


def test_split_long_respects_limit():
    text = " ".join(f"Sentence number {i} is here." for i in range(200))
    assert all(len(p) <= 300 for p in split_long(text, 300))


def test_chunk_document_sections():
    body = "text that is comfortably longer than the minimum chunk size"
    md = f"# Doc\n\n## A\n\nalpha {body}\n\n## B\n\nbeta {body}\n\n## C\n\ntiny"
    chunks = chunk_document(md, "doc.md", "Doc")
    assert [c.section for c in chunks] == ["A", "B"]
    assert chunks[0].text.startswith("[Doc > A]")
