"""Shared test helpers. Tests run offline: no model download, no Groq key needed."""
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from src import retriever as retriever_module  # noqa: E402
from src.retriever import Retriever, tokenize  # noqa: E402


class FakeEmbedder:
    """Bag-of-words hashing 'embeddings': deterministic and good enough to test the plumbing."""
    model_name = "fake"

    def encode(self, texts, is_query=False):
        out = np.zeros((len(texts), 256), dtype="float32")
        for row, text in enumerate(texts):
            for tok in tokenize(text):
                out[row, int(hashlib.md5(tok.encode()).hexdigest(), 16) % 256] += 1
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1, norms)


class FakeReranker:
    """Scores by word overlap between question and passage (0..1)."""

    def score(self, question, passages):
        q = set(tokenize(question))
        return [len(q & set(tokenize(p))) / (len(q) or 1) for p in passages]


class FakeLLM:
    """Mimics the Groq client: streams a fixed reply and remembers the request."""

    def __init__(self, reply="I graduated from IUIC Islamabad."):
        self.reply, self.calls = reply, []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        for word in self.reply.split(" "):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=word + " "))])


@pytest.fixture
def tmp_dirs(tmp_path, monkeypatch):
    index_dir = tmp_path / "index"
    monkeypatch.setattr(config, "INDEX_DIR", index_dir)
    monkeypatch.setattr(config, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(retriever_module, "INDEX_FILE", index_dir / "faiss.index")
    monkeypatch.setattr(retriever_module, "CHUNKS_FILE", index_dir / "chunks.json")
    monkeypatch.setattr(retriever_module, "MANIFEST_FILE", index_dir / "manifest.json")
    monkeypatch.setattr(config, "MIN_DENSE_SCORE", 0.1)  # fake embeddings score lower than real ones
    return tmp_path


@pytest.fixture
def retriever(tmp_dirs):
    r, _ = Retriever.build(FakeEmbedder(), FakeReranker())
    return r
