"""Unit tests for Retrieval Engine Models and Result Contract."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.models import (
    CategoryEvaluationMetric,
    DynamicLiveAction,
    EvaluationSummary,
    EvidenceSet,
    QueryCategory,
    QueryClassification,
    RetrievalResult,
    RetrievalScoreBreakdown,
    ScoringWeights,
)


def test_query_classification_model() -> None:
    qc = QueryClassification(
        raw_query="What is AgentGuard?",
        normalized_query="what is agentguard?",
        category=QueryCategory.CONCEPTUAL_PROJECT,
        extracted_symbols=[],
        extracted_routes=[],
        domain_hints=[DomainCategory.A_PRODUCT_IDENTITY],
        is_dynamic_live=False,
    )
    assert qc.category == QueryCategory.CONCEPTUAL_PROJECT
    assert qc.domain_hints == [DomainCategory.A_PRODUCT_IDENTITY]
    assert qc.is_dynamic_live is False


def test_retrieval_result_contract() -> None:
    res = RetrievalResult(
        knowledge_unit_id="unit_123",
        title="Policy Engine Verification",
        content="def verify_proposal(): pass",
        summary="Verifies proposals against 5 rules.",
        domain=DomainCategory.I_POLICY_ENGINE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="PYTHON_AST",
        source_path="backend/app/policy/engine.py",
        line_start=10,
        line_end=50,
        symbol="PolicyEngine.verify_proposal",
        score=0.98,
        retrieval_method="EXACT",
        content_sha256="abc123sha",
        selection_reason="Exact symbol match",
        score_breakdown=RetrievalScoreBreakdown(
            exact_score=1.0,
            authority_score=0.95,
            total_score=0.98,
        ),
    )
    assert res.knowledge_unit_id == "unit_123"
    assert res.source_tier == SourceTier.TIER_2_SOURCE_CODE
    assert res.authority == AuthorityType.AUTHORITATIVE
    assert res.score_breakdown.exact_score == 1.0


def test_evidence_set_contract() -> None:
    qc = QueryClassification(
        raw_query="How does price tampering work?",
        normalized_query="how does price tampering work?",
        category=QueryCategory.SECURITY_SCENARIO,
    )
    r1 = RetrievalResult(
        knowledge_unit_id="u1",
        title="Check Price Function",
        content="def _check_price(): pass",
        summary="Price check rule.",
        domain=DomainCategory.I_POLICY_ENGINE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="PYTHON_AST",
        source_path="backend/app/policy/engine.py",
        score=0.95,
        retrieval_method="HYBRID_RERANKED",
        content_sha256="sha1",
    )
    ev_set = EvidenceSet(
        query="How does price tampering work?",
        classification=qc,
        primary_result=r1,
        code_evidence=r1,
        all_results=[r1],
        total_candidates=5,
        latency_ms=1.25,
    )
    assert ev_set.primary_result == r1
    assert ev_set.code_evidence == r1
    assert ev_set.total_candidates == 5
    assert ev_set.latency_ms == 1.25


def test_category_evaluation_metric_properties() -> None:
    m = CategoryEvaluationMetric(
        category="Code Retrieval",
        total_queries=10,
        top1_hits=9,
        top3_hits=10,
        top5_hits=10,
    )
    assert m.top1_accuracy == 90.0
    assert m.top3_accuracy == 100.0
    assert m.top5_accuracy == 100.0
