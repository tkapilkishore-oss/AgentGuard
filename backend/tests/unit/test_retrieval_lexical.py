"""Unit tests for LexicalBM25Matcher."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, KnowledgeUnit, SourceTier
from backend.app.retrieval.lexical_matcher import LexicalBM25Matcher


@pytest.fixture
def sample_units() -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            id="unit_price_tamper",
            domain=DomainCategory.O_ATTACK_SCENARIOS,
            title="Price Tampering Attack Detection",
            summary="Detects when the shopping agent changes the catalog price.",
            content="Price tampering occurs when an autonomous agent claims a different price from the catalog.",
            source_type="CANONICAL_FACT",
            source_path="knowledge/canonical/facts.json",
            source_tier=SourceTier.TIER_5_SPEC_DOCS,
            content_sha256="sha_fact1",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["price_mismatch", "tampering", "security"],
        ),
        KnowledgeUnit(
            id="unit_sha256_chain",
            domain=DomainCategory.Q_SHA256_HASH_CHAIN,
            title="Cryptographic SHA-256 Audit Trail",
            summary="Immutable hash-chained ledger of all events.",
            content="Each audit event contains prev_event_hash and event_hash computed with SHA-256.",
            source_type="DOC",
            source_path="docs/ARCHITECTURE.md",
            source_tier=SourceTier.TIER_5_SPEC_DOCS,
            content_sha256="sha_fact2",
            authority=AuthorityType.AUTHORITATIVE,
            tags=["audit", "sha-256", "ledger"],
        ),
    ]


def test_lexical_bm25_search_price_tampering(sample_units: list[KnowledgeUnit]) -> None:
    matcher = LexicalBM25Matcher(sample_units)
    results = matcher.search("price tampering attack", top_k=5)

    assert len(results) > 0
    assert results[0].knowledge_unit_id == "unit_price_tamper"
    assert results[0].retrieval_method == "LEXICAL_BM25"
    assert results[0].score > 0.0


def test_lexical_bm25_search_sha256(sample_units: list[KnowledgeUnit]) -> None:
    matcher = LexicalBM25Matcher(sample_units)
    results = matcher.search("cryptographic hash chain sha-256", top_k=5)

    assert len(results) > 0
    assert results[0].knowledge_unit_id == "unit_sha256_chain"
    assert results[0].score > 0.0


def test_lexical_bm25_empty_query(sample_units: list[KnowledgeUnit]) -> None:
    matcher = LexicalBM25Matcher(sample_units)
    results = matcher.search("", top_k=5)
    assert len(results) == 0
