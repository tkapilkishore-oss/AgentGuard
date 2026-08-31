"""Retrieval Bridge interfacing with the frozen Phase 5.5B-2.1 RetrievalEngine."""

import time
from typing import Any

from backend.app.conversational.models import EvidenceContext
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.engine import RetrievalEngine, get_retrieval_engine
from backend.app.retrieval.models import EvidenceSet, RetrievalResult


class RetrievalBridge:
    """Consumes the frozen B-2.1 RetrievalEngine to retrieve authoritative static evidence,

    preserving source provenance, file paths, line ranges, and authority ranking.
    """

    def __init__(self, engine: RetrievalEngine | None = None) -> None:
        self.engine = engine or get_retrieval_engine()

    def retrieve_evidence(
        self,
        query: str,
        domain_filter: DomainCategory | None = None,
        tier_filter: SourceTier | None = None,
        top_k: int = 5,
    ) -> EvidenceContext:
        """Retrieves multi-source evidence set for conversational grounding."""
        start_time = time.perf_counter()

        # Retrieve minimal sufficient evidence set
        evidence_set = self.engine.retrieve_with_evidence(query)
        ranked_results = evidence_set.all_results[:top_k]

        unit_ids = [r.knowledge_unit_id for r in ranked_results]
        authorities = [r.authority for r in ranked_results]
        source_tiers = [r.source_tier for r in ranked_results]

        # Extract structured summary notes
        notes: list[str] = []
        for r in ranked_results:
            loc = f" ({r.source_path}:{r.line_start}-{r.line_end})" if r.line_start else f" ({r.source_path})"
            notes.append(f"[{r.authority.value} / {r.source_tier.value}] {r.title}{loc}: {r.summary}")

        confidence = 1.0 if ranked_results and ranked_results[0].score > 0.3 else 0.5

        return EvidenceContext(
            static_evidence=evidence_set,
            live_result=None,
            is_live=False,
            provenance_unit_ids=unit_ids,
            authorities=authorities,
            source_tiers=source_tiers,
            confidence=confidence,
            summary_notes=notes,
        )
