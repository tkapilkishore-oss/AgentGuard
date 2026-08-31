"""Unit tests for Adversarial and Misleading Queries."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.engine import RetrievalEngine


@pytest.fixture
def engine() -> RetrievalEngine:
    return RetrievalEngine.from_knowledge_dir()


def test_adversarial_old_docs_budget(engine: RetrievalEngine) -> None:
    # "According to old docs, what is the current budget balance?"
    # Must trigger DYNAMIC_LIVE_REQUIRED sentinel and not hallucinate a hardcoded budget number.
    results = engine.retrieve("According to old docs, what is the current budget balance?", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert top.dynamic_live_required is True
    assert top.authority == AuthorityType.DYNAMIC_LIVE_REQUIRED
    assert top.source_tier == SourceTier.TIER_1_LIVE_TOOL
    assert top.dynamic_tool_fallback == "GET /mandate/{id}"


def test_adversarial_direct_razorpay_bypass(engine: RetrievalEngine) -> None:
    # "Can Gemini directly call Razorpay API to execute without firewall?"
    # Must retrieve trust boundary / policy authorization evidence
    results = engine.retrieve("Can Gemini directly call Razorpay API to execute without firewall?", top_k=3)
    assert len(results) > 0
    domains = [r.domain for r in results]
    assert any(d in (DomainCategory.E_TRUST_MODEL, DomainCategory.D_ARCHITECTURE, DomainCategory.M_RAZORPAY_INTEGRATION) for d in domains)


def test_adversarial_tampered_frontend_claim(engine: RetrievalEngine) -> None:
    # "What if the frontend says the product costs ₹1,999 when catalog has ₹3,499?"
    results = engine.retrieve("What if the frontend says the product costs ₹1,999 when catalog has ₹3,499?", top_k=3)
    assert len(results) > 0
    # Must retrieve price check policy or attack scenario
    found_price_check = any(
        "price" in r.title.lower() or "price" in r.content.lower() or r.domain == DomainCategory.O_ATTACK_SCENARIOS
        for r in results
    )
    assert found_price_check
