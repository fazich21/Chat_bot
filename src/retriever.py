"""Find the chunks that best answer a question.

Pipeline for every question:
  1. Rewrite it to match the documents ("his interests" -> "my interests") and add synonyms.
  2. Hybrid search: dense vectors (meaning) + BM25 (exact words), fused with RRF.
  3. Re-rank the top candidates with a cross-encoder, which reads question and chunk together
     and is much more accurate than either search alone.
  4. Add neighbouring pieces of split sections, then order the context by document.

The index is saved to index/ and rebuilt automatically whenever a file in data/ changes.
Models run with fastembed (ONNX, no PyTorch), so the whole app fits in ~512 MB of memory.
"""
import json
import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

import config
from src import query as query_prep
from src.chunking import Chunk
from src.ingest import DataReport, data_fingerprint, load_chunks

INDEX_FILE = config.INDEX_DIR / "vectors.npy"
CHUNKS_FILE = config.INDEX_DIR / "chunks.json"
MANIFEST_FILE = config.INDEX_DIR / "manifest.json"

STOPWORDS = set("""a an the and or of to in on at for with by from is are was were be been am i you
your yours me my he his she her it its we our they their what which who whom how when where why do does
did can could would should will tell about please this that these those as so if any all some""".split())


def tokenize(text: str) -> list[str]:
    tokens = []
    for t in re.findall(r"[a-z0-9+#]+", text.lower()):
        if t in STOPWORDS:
            continue
        tokens.append(t[:-1] if len(t) > 4 and t.endswith("s") else t)  # crude plural folding
    return tokens


class Embedder:
    """bge-small embedding model (ONNX via fastembed), loaded once and only when first needed."""

    def __init__(self, model_name: str = config.EMBED_MODEL, query_prefix: str = config.QUERY_PREFIX):
        self.model_name, self.query_prefix, self._model = model_name, query_prefix, None

    def encode(self, texts: list[str], is_query: bool = False) -> np.ndarray:
        if self._model is None:
            from fastembed import TextEmbedding
            self._model = TextEmbedding(self.model_name, cache_dir=str(config.MODEL_DIR),
                                        threads=config.MODEL_THREADS)
        if is_query:
            texts = [self.query_prefix + t for t in texts]
        vectors = np.asarray(list(self._model.embed(texts, batch_size=16)), dtype="float32")
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors / np.where(norms == 0, 1, norms)


class Reranker:
    """Cross-encoder that scores (question, chunk) pairs from 0 (irrelevant) to 1 (relevant)."""

    def __init__(self, model_name: str = config.RERANK_MODEL):
        self.model_name, self._model = model_name, None

    def score(self, question: str, passages: list[str]) -> list[float]:
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            self._model = TextCrossEncoder(self.model_name, cache_dir=str(config.MODEL_DIR),
                                           threads=config.MODEL_THREADS)
        raw = np.asarray(list(self._model.rerank(question, passages)), dtype="float64")
        if raw.min() < 0 or raw.max() > 1:      # model returned logits: squash to 0..1
            raw = 1 / (1 + np.exp(-raw))
        return raw.tolist()


@dataclass
class Hit:
    chunk: Chunk
    score: float   # final relevance score (rerank score, or fused score without reranker)


class Retriever:
    def __init__(self, chunks: list[Chunk], vectors: np.ndarray, embedder, reranker=None):
        self.chunks = chunks
        self.vectors = vectors          # one normalized row per chunk; dot product = cosine
        self.embedder = embedder
        self.reranker = reranker
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    # ── building / loading ───────────────────────────────────────────────
    @classmethod
    def build(cls, embedder=None, reranker=None, save: bool = True) -> tuple["Retriever", DataReport]:
        embedder = embedder or Embedder()
        chunks, report = load_chunks()
        if not chunks:
            raise RuntimeError(f"No usable documents found in {config.DATA_DIR}.")
        vectors = embedder.encode([c.text for c in chunks])
        if save:
            config.INDEX_DIR.mkdir(exist_ok=True)
            np.save(INDEX_FILE, vectors)
            CHUNKS_FILE.write_text(json.dumps([c.to_dict() for c in chunks], ensure_ascii=False, indent=1),
                                   encoding="utf-8")
            MANIFEST_FILE.write_text(json.dumps({"fingerprint": data_fingerprint(),
                                                 "embed_model": embedder.model_name,
                                                 "chunks": len(chunks)}, indent=1))
        return cls(chunks, vectors, embedder, reranker), report

    @classmethod
    def load_or_build(cls, embedder=None, reranker=None) -> "Retriever":
        """Load the saved index if data/ hasn't changed; otherwise rebuild it."""
        embedder = embedder or Embedder()
        if reranker is None and config.USE_RERANKER:
            reranker = Reranker()
        if INDEX_FILE.exists() and CHUNKS_FILE.exists() and MANIFEST_FILE.exists():
            manifest = json.loads(MANIFEST_FILE.read_text())
            if manifest.get("fingerprint") == data_fingerprint():
                chunks = [Chunk(**c) for c in json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))]
                return cls(chunks, np.load(INDEX_FILE), embedder, reranker)
            print("Data changed since the last build: rebuilding the index...")
        retriever, report = cls.build(embedder, reranker)
        for warning in report.warnings():
            print(f"WARNING: {warning}")
        print(f"Index ready: {len(retriever.chunks)} chunks.")
        return retriever

    def warm_up(self) -> None:
        """Load the models now, so the first visitor doesn't wait for them."""
        self.search("warm up")

    # ── searching ────────────────────────────────────────────────────────
    def search(self, question: str, top_k: int = config.TOP_K) -> list[Hit]:
        semantic_q, keyword_q = query_prep.prepare(question)
        candidates = self._hybrid_candidates(semantic_q, keyword_q, config.CANDIDATES)
        if not candidates:
            return []

        if self.reranker:
            hits = self._rerank(semantic_q, candidates, top_k)
        else:
            hits = [Hit(self.chunks[cid], score) for cid, score, relevant in candidates if relevant][:top_k]

        hits = self._add_neighbours(hits)
        # Keep chunks of the same document together, in document order: easier for the LLM to read.
        order = {h.chunk.source: i for i, h in reversed(list(enumerate(hits)))}
        return sorted(hits, key=lambda h: (order[h.chunk.source], h.chunk.id))

    def _hybrid_candidates(self, semantic_q: str, keyword_q: str, pool: int) -> list[tuple[int, float, bool]]:
        """Return (chunk_id, fused_score, looks_relevant) for the best `pool` chunks."""
        n = len(self.chunks)
        pool = min(pool, n)

        dense_scores = self.vectors @ self.embedder.encode([semantic_q], is_query=True)[0]
        dense_by_id = {i: float(s) for i, s in enumerate(dense_scores)}
        dense_rank = [int(i) for i in np.argsort(-dense_scores)[:pool]]

        tokens = tokenize(keyword_q)
        bm25_scores = self.bm25.get_scores(tokens) if tokens else np.zeros(n)
        bm25_rank = [int(i) for i in np.argsort(-bm25_scores)[:pool] if bm25_scores[i] > 0]

        fused: dict[int, float] = {}
        for ranking in (dense_rank, bm25_rank):
            for rank, cid in enumerate(ranking):
                fused[cid] = fused.get(cid, 0.0) + 1.0 / (config.RRF_K + rank + 1)

        top_keyword = set(bm25_rank[:config.TOP_K])
        ranked = sorted(fused.items(), key=lambda kv: -kv[1])[:pool]
        return [(cid, score, dense_by_id.get(cid, 0.0) >= config.MIN_DENSE_SCORE or cid in top_keyword)
                for cid, score in ranked]

    def _rerank(self, question: str, candidates, top_k: int) -> list[Hit]:
        ids = [cid for cid, _, _ in candidates]
        try:
            scores = self.reranker.score(question, [self.chunks[cid].text for cid in ids])
        except Exception as exc:  # model failed to load/run: fall back to hybrid order
            print(f"Reranker unavailable ({exc}); using hybrid ranking.")
            self.reranker = None
            return [Hit(self.chunks[cid], s) for cid, s, rel in candidates if rel][:top_k]
        ranked = sorted(zip(ids, scores), key=lambda kv: -kv[1])
        return [Hit(self.chunks[cid], float(s)) for i, (cid, s) in enumerate(ranked[:top_k])
                if i < config.RERANK_MIN_KEEP or s >= config.RERANK_MIN_SCORE]

    def _add_neighbours(self, hits: list[Hit]) -> list[Hit]:
        """If a section was split into several chunks, also include the next/previous piece
        so the LLM sees the whole story (e.g. a long paragraph about one person)."""
        chosen = {h.chunk.id for h in hits}
        extra = []
        for h in hits[:3]:
            for nid in (h.chunk.id - 1, h.chunk.id + 1):
                if 0 <= nid < len(self.chunks) and nid not in chosen:
                    other = self.chunks[nid]
                    if other.source == h.chunk.source and other.section == h.chunk.section:
                        extra.append(Hit(other, 0.0))
                        chosen.add(nid)
        return hits + extra
