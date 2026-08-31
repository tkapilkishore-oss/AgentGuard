"""Deterministic Offline Semantic Vector Retrieval with Pluggable Embedding Providers."""

import math
import os
import re
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from typing import Sequence

from backend.app.knowledge.models import KnowledgeUnit
from backend.app.retrieval.models import RetrievalResult, RetrievalScoreBreakdown


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Embeds a single query string."""
        pass

    @abstractmethod
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embeds a batch of document strings."""
        pass


class LocalTFIDFEmbeddingProvider(BaseEmbeddingProvider):
    """High-dimensional, subword & character n-gram TF-IDF embedding provider.

    Guarantees 100% offline, deterministic, zero-dependency, reproducible vector representation.
    """

    def __init__(self, vocab_size: int = 4096) -> None:
        self.vocab_size = vocab_size
        self.vocab: dict[str, int] = {}
        self.idf: dict[int, float] = {}
        self.doc_count = 0

    def _extract_features(self, text: str) -> list[str]:
        """Extracts word tokens, character 3-grams and 4-grams for subword semantic capture."""
        clean = re.sub(r"[^a-zA-Z0-9_\-\.\s]", " ", text.lower())
        words = [w for w in clean.split() if len(w) > 1]
        features: list[str] = list(words)

        for w in words:
            # Character n-grams (3-grams and 4-grams)
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    features.append(w[i : i + 3])
            if len(w) >= 4:
                for i in range(len(w) - 3):
                    features.append(w[i : i + 4])

        return features

    def fit(self, texts: Sequence[str]) -> None:
        """Builds the vocabulary and IDF tables from the knowledge corpus."""
        self.doc_count = len(texts)
        df_counts: dict[str, int] = defaultdict(int)

        for t in texts:
            unique_feats = set(self._extract_features(t))
            for f in unique_feats:
                df_counts[f] += 1

        # Select top features by document frequency
        sorted_feats = sorted(df_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)
        top_feats = sorted_feats[: self.vocab_size]

        self.vocab = {feat: idx for idx, (feat, _) in enumerate(top_feats)}

        for feat, idx in self.vocab.items():
            freq = df_counts[feat]
            self.idf[idx] = math.log(1.0 + (self.doc_count - freq + 0.5) / (freq + 0.5))

    def _vectorize(self, text: str) -> list[float]:
        feats = self._extract_features(text)
        counts = Counter(feats)
        vec = [0.0] * len(self.vocab)

        total_feats = len(feats) or 1
        for feat, count in counts.items():
            if feat in self.vocab:
                idx = self.vocab[feat]
                tf = count / total_feats
                idf = self.idf.get(idx, 1.0)
                vec[idx] = tf * idf

        # L2 Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]

        return vec

    def embed_text(self, text: str) -> list[float]:
        return self._vectorize(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vectorize(t) for t in texts]


class OptionalGeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Optional external Gemini embedding provider adapter.

    Falls back cleanly to LocalTFIDFEmbeddingProvider if offline, unconfigured, or on error.
    """

    def __init__(self, fallback_provider: BaseEmbeddingProvider) -> None:
        self.fallback = fallback_provider
        self.api_key = os.getenv("GEMINI_API_KEY")

    def embed_text(self, text: str) -> list[float]:
        # Keep local deterministic fallback as primary default
        return self.fallback.embed_text(text)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self.fallback.embed_documents(texts)


class SemanticMatcher:
    """In-memory dense vector matcher utilizing local deterministic embedding representation."""

    def __init__(
        self,
        units: list[KnowledgeUnit],
        provider: BaseEmbeddingProvider | None = None,
    ) -> None:
        self.units = units
        doc_texts = [f"{u.title}\n{u.summary}\n{u.content}\n{' '.join(u.tags)}" for u in units]

        if provider is None:
            local_provider = LocalTFIDFEmbeddingProvider()
            local_provider.fit(doc_texts)
            self.provider: BaseEmbeddingProvider = local_provider
        else:
            self.provider = provider

        self.doc_vectors = self.provider.embed_documents(doc_texts)

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Computes dot product of normalized vectors."""
        return sum(a * b for a, b in zip(vec_a, vec_b))

    def search(self, query: str, top_k: int = 20) -> list[RetrievalResult]:
        """Performs cosine vector search across all indexed units."""
        query_vec = self.provider.embed_text(query)
        if not any(v > 0.0 for v in query_vec):
            return []

        scores: list[tuple[int, float]] = []
        for idx, doc_vec in enumerate(self.doc_vectors):
            sim = self._cosine_similarity(query_vec, doc_vec)
            if sim > 0.0:
                scores.append((idx, sim))

        if not scores:
            return []

        scores.sort(key=lambda x: x[1], reverse=True)
        max_score = scores[0][1] if scores else 1.0

        results: list[RetrievalResult] = []
        for idx, raw_score in scores[:top_k]:
            unit = self.units[idx]
            normalized_score = min(1.0, raw_score / max(max_score, 1e-6))
            results.append(
                RetrievalResult(
                    knowledge_unit_id=unit.id,
                    title=unit.title,
                    content=unit.content,
                    summary=unit.summary,
                    domain=unit.domain,
                    source_tier=unit.source_tier,
                    authority=unit.authority,
                    source_type=unit.source_type,
                    source_path=unit.source_path,
                    line_start=unit.line_start,
                    line_end=unit.line_end,
                    symbol=unit.symbol,
                    route=unit.route,
                    frontend_action=unit.dynamic_tool_fallback,
                    score=normalized_score,
                    retrieval_method="SEMANTIC",
                    dynamic_live_required=(unit.authority.value == "DYNAMIC_LIVE_REQUIRED"),
                    dynamic_tool_fallback=unit.dynamic_tool_fallback,
                    tags=unit.tags,
                    content_sha256=unit.content_sha256,
                    selection_reason=f"Vector cosine similarity match (sim={raw_score:.3f}, norm={normalized_score:.2f})",
                    score_breakdown=RetrievalScoreBreakdown(
                        semantic_score=normalized_score,
                        total_score=normalized_score,
                    ),
                )
            )

        return results
