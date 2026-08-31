"""Master Hybrid RAG + AST Codebase Retrieval Engine."""

import json
import os
import time
from pathlib import Path
from typing import Sequence

from backend.app.knowledge.models import (
    AuthorityType,
    DomainCategory,
    KnowledgeUnit,
    SourceTier,
)
from backend.app.retrieval.ast_retriever import AstCodeRetriever
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.dynamic_safeguards import DynamicDataSafeguard
from backend.app.retrieval.evidence_aggregator import EvidenceAggregator
from backend.app.retrieval.exact_matcher import ExactMatcher
from backend.app.retrieval.lexical_matcher import LexicalBM25Matcher
from backend.app.retrieval.models import (
    EvidenceSet,
    QueryClassification,
    RetrievalResult,
    ScoringWeights,
)
from backend.app.retrieval.reranker import AuthorityReranker
from backend.app.retrieval.semantic_matcher import SemanticMatcher


class RetrievalEngine:
    """Master engine orchestrating query classification, exact, lexical, semantic, AST retrieval,

    authority-aware reranking, dynamic safeguards, and minimal sufficient evidence synthesis.
    """

    PROTECTED_PATTERNS = [
        ".env",
        "SKILLS.md",
        "BUG_FINDINGS.md",
        "node_modules",
        "dist",
        ".git",
        ".venv",
    ]

    def __init__(
        self,
        knowledge_units: list[KnowledgeUnit],
        weights: ScoringWeights | None = None,
    ) -> None:
        # Filter protected files and secrets
        self.units = self._filter_protected_units(knowledge_units)

        self.classifier = QueryClassifier()
        self.exact_matcher = ExactMatcher(self.units)
        self.lexical_matcher = LexicalBM25Matcher(self.units)
        self.semantic_matcher = SemanticMatcher(self.units)
        self.ast_retriever = AstCodeRetriever(self.units)
        self.reranker = AuthorityReranker(weights)

    @classmethod
    def from_knowledge_dir(cls, knowledge_dir: Path | str | None = None) -> "RetrievalEngine":
        """Factory initializing the engine directly from canonical knowledge directory JSON."""
        if knowledge_dir is None:
            # Default to workspace knowledge/generated/unified_knowledge.json
            base = Path(__file__).resolve().parents[3]
            json_path = base / "knowledge" / "generated" / "unified_knowledge.json"
        else:
            json_path = Path(knowledge_dir)
            if json_path.is_dir():
                json_path = json_path / "generated" / "unified_knowledge.json"

        if not json_path.exists():
            raise FileNotFoundError(f"Knowledge dataset not found at {json_path}")

        raw_data = json.loads(json_path.read_text(encoding="utf-8"))
        units = [KnowledgeUnit.model_validate(item) for item in raw_data]
        return cls(knowledge_units=units)

    def _filter_protected_units(self, units: list[KnowledgeUnit]) -> list[KnowledgeUnit]:
        """Ensures secrets and protected files are never indexed or exposed."""
        safe_units: list[KnowledgeUnit] = []
        for u in units:
            path_str = u.source_path.lower()
            if any(p.lower() in path_str for p in self.PROTECTED_PATTERNS):
                continue
            # Also ensure secret keywords are absent
            content_lower = u.content.lower()
            if "rzp_test_secret" in content_lower or "ai_za_sy" in content_lower:
                continue
            safe_units.append(u)
        return safe_units

    def classify_query(self, query: str) -> QueryClassification:
        """Classifies query intent and extracts entity hints."""
        return self.classifier.classify(query)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        domain_filter: DomainCategory | None = None,
        tier_filter: SourceTier | None = None,
    ) -> list[RetrievalResult]:
        """Performs end-to-end hybrid retrieval and returns ranked results."""
        start_time = time.perf_counter()
        classification = self.classify_query(query)

        candidates: list[RetrievalResult] = []

        # 1. Dynamic Sentinel Check (Hard Stop)
        if classification.is_dynamic_live:
            sentinel = DynamicDataSafeguard.create_live_required_result(classification)
            if sentinel:
                candidates.append(sentinel)

        # 2. Exact Matching
        exact_results = self.exact_matcher.match(classification)
        candidates.extend(exact_results)

        # 3. Lexical BM25 Search
        lexical_results = self.lexical_matcher.search(query, top_k=25)
        candidates.extend(lexical_results)

        # 4. Semantic Search
        semantic_results = self.semantic_matcher.search(query, top_k=25)
        candidates.extend(semantic_results)

        # 5. AST Symbol Lookup if symbols detected
        for sym in classification.extracted_symbols:
            ast_results = self.ast_retriever.find_symbol_evidence(sym)
            candidates.extend(ast_results)

        # 6. Apply Domain & Tier Filters if requested
        if domain_filter:
            candidates = [c for c in candidates if c.domain == domain_filter]
        if tier_filter:
            candidates = [c for c in candidates if c.source_tier == tier_filter]

        # 7. Authority-Aware Constrained Reranking
        ranked = self.reranker.rerank(candidates, classification, top_k=top_k)

        # 8. Dynamic Data Sanitization
        sanitized = DynamicDataSafeguard.sanitize_dynamic_results(ranked, classification.is_dynamic_live)

        return sanitized

    def retrieve_with_evidence(self, query: str) -> EvidenceSet:
        """Performs retrieval and synthesizes the minimal sufficient multi-source EvidenceSet."""
        start_time = time.perf_counter()
        classification = self.classify_query(query)

        ranked = self.retrieve(query, top_k=15)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return EvidenceAggregator.aggregate(
            query=query,
            classification=classification,
            candidates=ranked,
            total_candidates=len(ranked),
            latency_ms=round(elapsed_ms, 2),
        )

    def query(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Convenience alias for retrieve."""
        return self.retrieve(query, top_k=top_k)

    def explain(self, result: RetrievalResult) -> str:
        """Provides human-readable explainability breakdown for a retrieval result."""
        b = result.score_breakdown
        return (
            f"=== Retrieval Explanation for Unit: {result.knowledge_unit_id} ===\n"
            f"Title:       {result.title}\n"
            f"Source Path: {result.source_path} (Lines: {result.line_start}-{result.line_end})\n"
            f"Domain:      {result.domain.value}\n"
            f"Source Tier: {result.source_tier.value}\n"
            f"Authority:   {result.authority.value}\n"
            f"Final Score: {result.score:.4f}\n"
            f"Method:      {result.retrieval_method}\n"
            f"Score Components:\n"
            f"  - Exact Match Score:     {b.exact_score:.4f}\n"
            f"  - BM25 Lexical Score:    {b.lexical_bm25_score:.4f}\n"
            f"  - Semantic Cosine Score: {b.semantic_score:.4f}\n"
            f"  - Domain Bonus:          {b.domain_bonus:.4f}\n"
            f"  - Authority Weight:      {b.authority_score:.4f}\n"
            f"  - Source Tier Weight:    {b.source_tier_score:.4f}\n"
            f"  - Query Alignment Bonus: {b.query_alignment_bonus:.4f}\n"
            f"Selection Reason: {result.selection_reason}\n"
        )


# Global Engine Singleton Cache
_ENGINE_INSTANCE: RetrievalEngine | None = None


def get_retrieval_engine(knowledge_dir: Path | str | None = None) -> RetrievalEngine:
    """Returns the cached singleton RetrievalEngine instance."""
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = RetrievalEngine.from_knowledge_dir(knowledge_dir)
    return _ENGINE_INSTANCE
