"""Rebuild the search index and check your data.

Usage (from the project folder):
    python scripts/build_index.py           # rebuild index + show data warnings
    python scripts/build_index.py --show    # also print every chunk so you can read what the bot sees
    python scripts/build_index.py --check   # only check the data (no model download, no index)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ingest import load_chunks  # noqa: E402


def main():
    args = set(sys.argv[1:])
    chunks, report = load_chunks()

    print("Files:")
    for name, count in report.files.items():
        print(f"  {name:<45} {count:>3} chunks")
    print(f"  {'TOTAL':<45} {len(chunks):>3} chunks\n")

    if "--show" in args:
        for c in chunks:
            print(f"--- #{c.id} | {c.source} | {c.section} ({len(c.text)} chars)\n{c.text}\n")

    warnings = report.warnings()
    if warnings:
        print("Things to fix in your documents:")
        for w in warnings:
            print(f"  - {w}")
        print()
    else:
        print("No data problems found.\n")

    if "--check" in args:
        return

    from src.retriever import Retriever
    Retriever.build()
    print("Index saved to index/.")


if __name__ == "__main__":
    main()
