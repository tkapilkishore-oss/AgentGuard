"""Unit tests for ExactMatcher."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, KnowledgeUnit, SourceTier
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.exact_matcher import ExactMatcher


@pytest.fixture
def sample_units() -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            id="unit_policy_verify",
            domain=DomainCategory.I_POLICY_ENGINE,
            title="PolicyEngine.verify_proposal",
            summary="Evaluates transaction proposals against mandate rules.",
            content="class PolicyEngine:\n    def verify_proposal(self, req): pass",
            source_type="PYTHON_AST",
            source_path="backend/app/policy/engine.py",
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            line_start=25,
            line_end=80,
            symbol="PolicyEngine.verify_proposal",
            route=None,
            content_sha256="sha_verify",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["policy", "verification", "engine"],
        ),
        KnowledgeUnit(
            id="unit_route_propose",
            domain=DomainCategory.G_BACKEND_ARCHITECTURE,
            title="FastAPI Route: POST /transaction/propose",
            summary="Endpoint to submit a purchase proposal.",
            content="@router.post('/transaction/propose')\ndef propose(): pass",
            source_type="API_ROUTE",
            source_path="backend/app/api/propose.py",
            source_tier=SourceTier.TIER_3_API_SCHEMA,
            line_start=15,
            line_end=40,
            symbol="propose_transaction",
            route="POST /transaction/propose",
            content_sha256="sha_route",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["api", "propose", "route"],
        ),
    ]


def test_exact_matcher_symbol_lookup(sample_units: list[KnowledgeUnit]) -> None:
    matcher = ExactMatcher(sample_units)
    classifier = QueryClassifier()

    qc = classifier.classify("Where is PolicyEngine.verify_proposal defined?")
    results = matcher.match(qc)

    assert len(results) > 0
    assert results[0].knowledge_unit_id == "unit_policy_verify"
    assert results[0].symbol == "PolicyEngine.verify_proposal"
    assert results[0].retrieval_method == "EXACT"
    assert results[0].score == 1.0


def test_exact_matcher_route_lookup(sample_units: list[KnowledgeUnit]) -> None:
    matcher = ExactMatcher(sample_units)
    classifier = QueryClassifier()

    qc = classifier.classify("What is POST /transaction/propose?")
    results = matcher.match(qc)

    assert len(results) > 0
    assert results[0].knowledge_unit_id == "unit_route_propose"
    assert results[0].route == "POST /transaction/propose"
    assert results[0].score == 1.0
