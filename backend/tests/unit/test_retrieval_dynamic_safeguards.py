"""Unit tests for DynamicDataSafeguard."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.dynamic_safeguards import DynamicDataSafeguard
from backend.app.retrieval.models import RetrievalResult


def test_dynamic_safeguard_emits_sentinel_for_budget() -> None:
    classifier = QueryClassifier()
    qc = classifier.classify("What is the current remaining budget balance?")

    sentinel = DynamicDataSafeguard.create_live_required_result(qc)
    assert sentinel is not None
    assert sentinel.dynamic_live_required is True
    assert sentinel.authority == AuthorityType.DYNAMIC_LIVE_REQUIRED
    assert sentinel.source_tier == SourceTier.TIER_1_LIVE_TOOL
    assert sentinel.dynamic_tool_fallback == "GET /mandate/{id}"
    assert "LIVE_QUERY_REQUIRED" in sentinel.content
    assert sentinel.score == 1.0


def test_dynamic_safeguard_sanitizes_static_results() -> None:
    static_res = RetrievalResult(
        knowledge_unit_id="unit_static_fact",
        title="Mandate Baseline Budget",
        content="Mandate default baseline budget is 3000.",
        summary="Baseline info.",
        domain=DomainCategory.K_BUDGETS,
        source_tier=SourceTier.TIER_5_SPEC_DOCS,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="CANONICAL_FACT",
        source_path="knowledge/canonical/facts.json",
        score=0.9,
        retrieval_method="SEMANTIC",
        content_sha256="sha_static",
    )

    sanitized = DynamicDataSafeguard.sanitize_dynamic_results([static_res], is_dynamic=True)
    assert len(sanitized) == 1
    assert "Explanatory static architecture context only" in sanitized[0].selection_reason
