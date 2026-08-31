"""Unit tests for EvidenceAggregator."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.evidence_aggregator import EvidenceAggregator
from backend.app.retrieval.models import QueryCategory, RetrievalResult


@pytest.fixture
def sample_candidates() -> list[RetrievalResult]:
    return [
        RetrievalResult(
            knowledge_unit_id="code_verify",
            title="PolicyEngine.verify_proposal",
            content="def verify_proposal(): pass",
            summary="Policy verification logic.",
            domain=DomainCategory.I_POLICY_ENGINE,
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            authority=AuthorityType.AUTHORITATIVE,
            source_type="PYTHON_AST",
            source_path="backend/app/policy/engine.py",
            symbol="PolicyEngine.verify_proposal",
            score=0.98,
            retrieval_method="EXACT",
            content_sha256="sha1",
        ),
        RetrievalResult(
            knowledge_unit_id="route_propose",
            title="POST /transaction/propose",
            content="@router.post('/transaction/propose')",
            summary="Proposal API route.",
            domain=DomainCategory.G_BACKEND_ARCHITECTURE,
            source_tier=SourceTier.TIER_3_API_SCHEMA,
            authority=AuthorityType.AUTHORITATIVE,
            source_type="API_ROUTE",
            source_path="backend/app/api/propose.py",
            route="POST /transaction/propose",
            score=0.92,
            retrieval_method="EXACT",
            content_sha256="sha2",
        ),
        RetrievalResult(
            knowledge_unit_id="test_price",
            title="test_price_tampering_detection",
            content="def test_price_tampering_detection(): pass",
            summary="Pytest test case for price tampering.",
            domain=DomainCategory.Y_TEST_SUITES,
            source_tier=SourceTier.TIER_4_AUTOMATED_TESTS,
            authority=AuthorityType.AUTHORITATIVE,
            source_type="PYTEST",
            source_path="backend/tests/unit/test_policy_engine.py",
            score=0.88,
            retrieval_method="HYBRID_RERANKED",
            content_sha256="sha3",
        ),
    ]


def test_evidence_aggregator_code_query(sample_candidates: list[RetrievalResult]) -> None:
    classifier = QueryClassifier()
    qc = classifier.classify("Which function verifies transaction proposals in code?")

    ev_set = EvidenceAggregator.aggregate(
        query="Which function verifies transaction proposals in code?",
        classification=qc,
        candidates=sample_candidates,
    )

    assert ev_set.primary_result is not None
    assert ev_set.code_evidence is not None
    assert ev_set.code_evidence.symbol == "PolicyEngine.verify_proposal"
    # For code symbol query, ensure minimal evidence does not dump unnecessary doc chunks
    assert ev_set.conceptual_evidence is None
