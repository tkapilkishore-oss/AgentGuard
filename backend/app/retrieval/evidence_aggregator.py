"""Minimal Sufficient Multi-Source Evidence Aggregator."""

from backend.app.knowledge.models import SourceTier
from backend.app.retrieval.models import (
    EvidenceSet,
    QueryCategory,
    QueryClassification,
    RetrievalResult,
)


class EvidenceAggregator:
    """Aggregates and filters candidate results into a concise, minimal sufficient evidence set."""

    @staticmethod
    def aggregate(
        query: str,
        classification: QueryClassification,
        candidates: list[RetrievalResult],
        total_candidates: int = 0,
        latency_ms: float = 0.0,
    ) -> EvidenceSet:
        """Constructs an EvidenceSet containing the minimum sufficient sources for the query category."""
        if not candidates:
            return EvidenceSet(
                query=query,
                classification=classification,
                all_results=[],
                total_candidates=total_candidates,
                latency_ms=latency_ms,
            )

        primary_result = candidates[0]
        code_ev: RetrievalResult | None = None
        api_ev: RetrievalResult | None = None
        test_ev: RetrievalResult | None = None
        fe_ev: RetrievalResult | None = None
        concept_ev: RetrievalResult | None = None

        cat = classification.category

        # Partition top candidates by role
        for c in candidates:
            if c.source_tier == SourceTier.TIER_2_SOURCE_CODE and c.source_type == "PYTHON_AST" and not code_ev:
                code_ev = c
            elif c.source_tier == SourceTier.TIER_3_API_SCHEMA or c.source_type == "API_ROUTE":
                if not api_ev:
                    api_ev = c
            elif c.source_tier == SourceTier.TIER_4_AUTOMATED_TESTS or c.source_type == "PYTEST":
                if not test_ev:
                    test_ev = c
            elif c.source_type == "TSX_COMPONENT" or c.frontend_action:
                if not fe_ev:
                    fe_ev = c
            elif c.source_tier in (SourceTier.TIER_5_SPEC_DOCS, SourceTier.TIER_6_HISTORICAL) or c.source_type in (
                "DOC",
                "CANONICAL_FACT",
            ):
                if not concept_ev:
                    concept_ev = c

        # Filter according to Minimal Sufficient Evidence Principle
        if cat == QueryCategory.CONCEPTUAL_PROJECT:
            # Only conceptual explanation needed (no spurious test/code dump)
            code_ev = None
            api_ev = None
            test_ev = None
            fe_ev = None
            if not concept_ev:
                concept_ev = primary_result

        elif cat == QueryCategory.CODE_SYMBOL:
            # Code symbol + test case if relevant
            fe_ev = None
            concept_ev = None
            if not code_ev:
                code_ev = primary_result

        elif cat == QueryCategory.API_ROUTE:
            # Route + handler code
            test_ev = None
            fe_ev = None
            concept_ev = None
            if not api_ev:
                api_ev = primary_result

        elif cat == QueryCategory.FRONTEND_ACTION:
            # Frontend component + target API route
            test_ev = None
            concept_ev = None
            if not fe_ev:
                fe_ev = primary_result

        elif cat == QueryCategory.TEST_VERIFICATION:
            # Test case + code symbol under test
            api_ev = None
            fe_ev = None
            concept_ev = None
            if not test_ev:
                test_ev = primary_result

        elif cat == QueryCategory.SECURITY_SCENARIO:
            # Policy logic + test verification + conceptual explanation
            fe_ev = None  # unless UI explicitly mentioned
            if not code_ev and primary_result.source_tier == SourceTier.TIER_2_SOURCE_CODE:
                code_ev = primary_result

        elif cat == QueryCategory.DYNAMIC_LIVE_DATA:
            # Sentinel + explanatory static concept
            code_ev = None
            test_ev = None
            fe_ev = None

        # Build final aggregated list
        minimal_results: list[RetrievalResult] = []
        for ev in [primary_result, code_ev, api_ev, test_ev, fe_ev, concept_ev]:
            if ev and ev not in minimal_results:
                minimal_results.append(ev)

        return EvidenceSet(
            query=query,
            classification=classification,
            primary_result=primary_result,
            code_evidence=code_ev,
            api_evidence=api_ev,
            test_evidence=test_ev,
            frontend_evidence=fe_ev,
            conceptual_evidence=concept_ev,
            all_results=minimal_results,
            total_candidates=total_candidates,
            latency_ms=latency_ms,
        )
