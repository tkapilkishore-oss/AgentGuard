"""Unit tests for RetrievalEngine Master End-to-End Functionality."""

import pytest
from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.engine import RetrievalEngine, get_retrieval_engine


@pytest.fixture
def engine() -> RetrievalEngine:
    return get_retrieval_engine()


def test_retrieval_engine_initialization(engine: RetrievalEngine) -> None:
    assert len(engine.units) > 400
    assert engine.classifier is not None
    assert engine.exact_matcher is not None
    assert engine.lexical_matcher is not None
    assert engine.semantic_matcher is not None
    assert engine.ast_retriever is not None
    assert engine.reranker is not None


def test_retrieve_code_symbol_provenance(engine: RetrievalEngine) -> None:
    results = engine.retrieve("Which function verifies transaction proposals in PolicyEngine?", top_k=5)
    assert len(results) > 0
    top = results[0]
    assert top.source_tier == SourceTier.TIER_2_SOURCE_CODE
    assert "PolicyEngine" in (top.symbol or "") or "verify" in (top.symbol or "") or "policy" in top.source_path
    assert top.line_start is not None
    assert top.line_end is not None
    assert top.content_sha256 != ""


def test_retrieve_with_evidence_set(engine: RetrievalEngine) -> None:
    ev_set = engine.retrieve_with_evidence("How does price tampering work?")
    assert ev_set.query == "How does price tampering work?"
    assert ev_set.primary_result is not None
    assert len(ev_set.all_results) >= 1
    assert ev_set.latency_ms > 0.0


def test_explain_interface(engine: RetrievalEngine) -> None:
    results = engine.retrieve("What is AgentGuard?", top_k=1)
    assert len(results) == 1
    explanation = engine.explain(results[0])
    assert "Retrieval Explanation for Unit" in explanation
    assert "Score Components" in explanation
    assert "Selection Reason" in explanation
