"""Lightweight TF-IDF engine for semantic search and skill matching.

This module provides a zero-dependency (pure Python) TF-IDF vectorizer
and cosine similarity scorer. It is used by:

- ``tools.coding.semantic_search`` — semantic code search across a project
- ``coding_core._semantic_matcher`` — TF-IDF based skill activation

Design constraints
------------------
- **No external dependencies**: must run inside sandboxes without pip.
- **Fast cold-start**: index build for a typical project (< 500 files)
  should complete in < 2 seconds.
- **CJK-aware**: Chinese/Japanese/Korean text is character-tokenized so
  that queries in Chinese match Chinese-language comments and docs.
- **Incremental cache**: the IDF table and per-file vectors are cached
  in a module-level dict keyed by ``project_root`` so repeated queries
  within the same thread do not re-scan the codebase.

API
---
- :class:`TfidfIndex` — build and query a TF-IDF index over a set of documents
- :func:`tokenize` — shared tokenizer (ASCII words + CJK chars, stopwords removed)
- :func:`cosine_similarity` — sparse-vector cosine similarity
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------- #

_STOPWORDS = frozenset({
    # English
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with",
    "this", "that", "is", "are", "be", "will", "can", "do", "does",
    "you", "your", "i", "we", "they", "it", "if", "else", "then",
    "code", "file", "project", "task", "please", "help", "me", "my",
    "use", "used", "using", "get", "set", "new", "def", "class",
    "return", "import", "from", "self", "true", "false", "none", "null",
    # Chinese stopwords
    "的", "了", "在", "是", "和", "与", "或", "请", "帮", "我",
    "把", "这个", "那个", "一下", "里面", "中", "上", "下",
    "不", "也", "都", "就", "还", "又", "已", "要", "会",
})

# Minimum token length (ASCII tokens shorter than this are dropped).
_MIN_TOKEN_LEN = 2

# Pre-compiled patterns.
_ASCII_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
# Split camelCase / snake_case into sub-tokens for better matching.
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z])(?=[A-Z])|_+")


def tokenize(text: str | None) -> list[str]:
    """Tokenize *text* into lowercase terms for TF-IDF.

    - ASCII words (len >= 2) are lowercased. camelCase and snake_case
      are split into sub-tokens (``getUserData`` → ``get``, ``user``,
      ``data``).
    - CJK characters are each emitted as individual tokens.
    - Stopwords are removed.
    """
    if not text:
        return []

    tokens: list[str] = []

    # ASCII words
    for word in _ASCII_WORD_RE.findall(text):
        # Split camelCase / snake_case
        parts = _CAMEL_SPLIT_RE.split(word)
        for part in parts:
            if not part or len(part) < _MIN_TOKEN_LEN:
                continue
            low = part.lower()
            if low in _STOPWORDS:
                continue
            tokens.append(low)

    # CJK characters
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            if ch not in ("的", "了", "在", "是", "和", "与", "或"):
                tokens.append(ch)

    return tokens


# --------------------------------------------------------------------- #
# TF-IDF Vector
# --------------------------------------------------------------------- #


def _term_frequency(tokens: list[str]) -> dict[str, float]:
    """Compute raw term frequency → normalized TF (0..1)."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for tok in tokens:
        counts[tok] = counts.get(tok, 0) + 1
    total = len(tokens)
    return {tok: count / total for tok, count in counts.items()}


def cosine_similarity(
    vec_a: dict[str, float],
    vec_b: dict[str, float],
) -> float:
    """Cosine similarity for sparse dict vectors. Returns 0..1."""
    if not vec_a or not vec_b:
        return 0.0
    # Iterate over the smaller vector for efficiency.
    if len(vec_a) > len(vec_b):
        vec_a, vec_b = vec_b, vec_a
    dot = sum(val * vec_b.get(tok, 0.0) for tok, val in vec_a.items())
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


# --------------------------------------------------------------------- #
# TF-IDF Index
# --------------------------------------------------------------------- #


@dataclass
class IndexedDocument:
    """A single document in the index."""

    doc_id: str
    tokens: list[str] = field(default_factory=list)
    tfidf_vector: dict[str, float] = field(default_factory=dict)


@dataclass
class SearchResult:
    """A single search result."""

    doc_id: str
    score: float
    preview: str = ""


class TfidfIndex:
    """An in-memory TF-IDF index over a set of documents.

    Usage::

        index = TfidfIndex()
        index.add("file1.py", source_code_of_file1)
        index.add("file2.py", source_code_of_file2)
        index.finalize()  # compute IDF

        results = index.search("authentication logic", top_k=5)
    """

    def __init__(self) -> None:
        self._docs: dict[str, IndexedDocument] = {}
        self._idf: dict[str, float] = {}
        self._finalized: bool = False
        # Average tokens per doc — used for BM25-like smoothing.
        self._avg_doc_len: float = 0.0

    @property
    def size(self) -> int:
        return len(self._docs)

    @property
    def finalized(self) -> bool:
        return self._finalized

    def add(self, doc_id: str, text: str) -> None:
        """Add a document to the index (before finalize)."""
        if self._finalized:
            raise RuntimeError("Cannot add documents after finalize()")
        tokens = tokenize(text)
        self._docs[doc_id] = IndexedDocument(doc_id=doc_id, tokens=tokens)

    def add_many(self, items: list[tuple[str, str]]) -> None:
        """Add multiple documents at once."""
        for doc_id, text in items:
            self.add(doc_id, text)

    def finalize(self) -> None:
        """Compute IDF weights and build per-document TF-IDF vectors.

        After this call, the index is read-only (no more ``add``).
        """
        n_docs = len(self._docs)
        if n_docs == 0:
            self._finalized = True
            return

        # Document frequency
        df: dict[str, int] = {}
        total_tokens = 0
        for doc in self._docs.values():
            total_tokens += len(doc.tokens)
            seen = set(doc.tokens)
            for tok in seen:
                df[tok] = df.get(tok, 0) + 1

        self._avg_doc_len = total_tokens / n_docs

        # IDF (smoothed, similar to BM25 style but simpler)
        for tok, freq in df.items():
            self._idf[tok] = math.log((n_docs + 1) / (freq + 0.5)) + 1.0

        # Build TF-IDF vectors
        for doc in self._docs.values():
            tf = _term_frequency(doc.tokens)
            doc.tfidf_vector = {
                tok: tf_val * self._idf.get(tok, 0.0)
                for tok, tf_val in tf.items()
            }

        self._finalized = True

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        min_score: float = 0.01,
    ) -> list[SearchResult]:
        """Search the index for *query*, returning the top *top_k* results.

        Documents with score < *min_score* are excluded.
        """
        if not self._finalized or not self._docs:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Build query TF-IDF vector
        query_tf = _term_frequency(query_tokens)
        query_vec = {
            tok: tf_val * self._idf.get(tok, 0.0)
            for tok, tf_val in query_tf.items()
            if tok in self._idf  # skip terms not in corpus
        }
        if not query_vec:
            return []

        results: list[SearchResult] = []
        for doc_id, doc in self._docs.items():
            score = cosine_similarity(query_vec, doc.tfidf_vector)
            if score >= min_score:
                results.append(SearchResult(doc_id=doc_id, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def query_vector(self, query: str) -> dict[str, float]:
        """Return the TF-IDF vector for *query* against this index.

        Useful for external similarity comparisons (e.g. skill matching).
        """
        if not self._finalized:
            return {}
        query_tokens = tokenize(query)
        query_tf = _term_frequency(query_tokens)
        return {
            tok: tf_val * self._idf.get(tok, 0.0)
            for tok, tf_val in query_tf.items()
            if tok in self._idf
        }


# --------------------------------------------------------------------- #
# Per-project index cache
# --------------------------------------------------------------------- #

# Keyed by project_root, so different threads/projects don't collide.
# Each entry is (TfidfIndex, mtime_snapshot) so we can detect staleness.
_INDEX_CACHE: dict[str, tuple[TfidfIndex, dict[str, float]]] = {}

# Maximum files to index per project (keeps memory bounded).
_MAX_INDEXED_FILES = 800


def _should_index(path: str) -> bool:
    """Heuristic: should this file be included in the code index?"""
    # Source code extensions
    code_exts = {
        ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs",
        ".ts", ".tsx", ".go", ".rs", ".java", ".kt",
        ".rb", ".php", ".c", ".h", ".cpp", ".cc", ".hpp",
        ".cs", ".swift", ".scala", ".clj", ".ex", ".exs",
        ".sql", ".graphql", ".gql",
        ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini",
        ".md", ".rst", ".txt",
    }
    import os

    _, ext = os.path.splitext(path)
    if ext.lower() not in code_exts:
        return False
    # Skip common noise directories
    lower = path.lower().replace("\\", "/")
    skip_dirs = (
        "/node_modules/", "/.git/", "/.venv/", "/venv/",
        "/__pycache__/", "/dist/", "/build/", "/.next/",
        "/.pytest_cache/", "/.ruff_cache/", "/target/",
    )
    for skip in skip_dirs:
        if skip in lower:
            return False
    return True


__all__ = [
    "TfidfIndex",
    "IndexedDocument",
    "SearchResult",
    "tokenize",
    "cosine_similarity",
]
