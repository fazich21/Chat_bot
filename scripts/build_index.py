"""Build the search index and check your data.

Usage (from the project folder):
    python scripts/build_index.py           # rebuild the index if data/ changed, show data warnings
    python scripts/build_index.py --force   # always rebuild
    python scripts/build_index.py --show    # also print every chunk so you can read what the bot sees
    python scripts/build_index.py --check   # only check the data (no model download, no index)

Run it on your computer after changing anything in data/, then commit the index/ folder.
On Vercel the index is already up to date, so this script only downloads the search model
(and doesn't need the PDF/Word libraries, which keeps the deployment small).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402


def report_data(show: bool) -> None:
    from src.ingest import load_chunks  # needs the PDF/Word libraries

    chunks, report = load_chunks()
    print("Files:")
    for name, count in report.files.items():
        print(f"  {name:<45} {count:>3} chunks")
    print(f"  {'TOTAL':<45} {len(chunks):>3} chunks\n")

    if show:
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


def main():
    args = set(sys.argv[1:])
    from src.retriever import Embedder, Reranker, Retriever

    if "--check" in args:
        report_data(show="--show" in args)
        return

    if Retriever.index_is_fresh() and not args & {"--force", "--show"}:
        print("Index is up to date with data/: nothing to rebuild.")
        if config.ON_VERCEL:
            # Don't bundle the model (size limit): the app downloads it to /tmp when it starts.
            print("On Vercel: the search model will be downloaded when the app starts.")
            return
        Embedder().encode(["warm up"])          # make sure the model is downloaded
        print("Embedding model ready.")
    else:
        report_data(show="--show" in args)
        Retriever.build()
        print("Index saved to index/. Remember to commit the index folder before deploying.")

    if config.USE_RERANKER:  # download the reranker too, so the server starts quickly
        Reranker().score("warm up", ["warm up"])
        print("Reranker model ready.")


if __name__ == "__main__":
    main()
