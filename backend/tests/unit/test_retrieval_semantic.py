"""Unit tests for SemanticMatcher and LocalTFIDFEmbeddingProvider."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, KnowledgeUnit, SourceTier
from backend.app.retrieval.semantic_matcher import LocalTFIDFEmbeddingProvider, SemanticMatcher


@pytest.fixture
def sample_units() -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            id="unit_budget_lock",
            domain=DomainCategory.K_BUDGETS,
            title="Mandate Budget Lock Mechanism",
            summary="Pre-allocates and deducts authorized funds from mandate spending limits.",
            content="When a transaction executes, the mandate remaining balance is decremented deterministically.",
            source_type="CANONICAL_FACT",
            source_path="knowledge/canonical/facts.json",
            source_tier=SourceTier.TIER_5_SPEC_DOCS,
            content_sha256="sha_budget",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["budget", "mandate", "limits"],
        ),
        KnowledgeUnit(
            id="unit_razorpay_gateway",
            domain=DomainCategory.M_RAZORPAY_INTEGRATION,
            title="Razorpay Test Mode Client",
            summary="Executes mock and test-mode payment captures with Razorpay APIs.",
            content="RazorpayClient handles order creation and payment authorization in test mode.",
            source_type="PYTHON_AST",
            source_path="backend/app/integrations/razorpay.py",
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            symbol="RazorpayClient",
            content_sha256="sha_rzp",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["razorpay", "payment", "gateway"],
        ),
    ]


def test_local_tfidf_embedding_provider() -> None:
    provider = LocalTFIDFEmbeddingProvider(vocab_size=100)
    texts = [
        "Mandate budget lock mechanism pre-allocates funds",
        "Razorpay test mode client executes payment orders",
    ]
    provider.fit(texts)

    v1 = provider.embed_text("spending limit balance")
    v2 = provider.embed_text("gateway payment orders")

    assert len(v1) == len(provider.vocab)
    assert len(v2) == len(provider.vocab)


def test_semantic_matcher_search(sample_units: list[KnowledgeUnit]) -> None:
    matcher = SemanticMatcher(sample_units)

    results = matcher.search("spending limits and mandate funds", top_k=5)
    assert len(results) > 0
    assert results[0].knowledge_unit_id == "unit_budget_lock"
    assert results[0].retrieval_method == "SEMANTIC"
    assert results[0].score > 0.0


def test_semantic_matcher_determinism(sample_units: list[KnowledgeUnit]) -> None:
    matcher = SemanticMatcher(sample_units)

    r1 = matcher.search("payment gateway capture", top_k=2)
    r2 = matcher.search("payment gateway capture", top_k=2)

    assert [r.knowledge_unit_id for r in r1] == [r.knowledge_unit_id for r in r2]
    assert [r.score for r in r1] == [r.score for r in r2]
