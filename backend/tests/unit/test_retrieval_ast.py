"""Unit tests for AstCodeRetriever."""

import pytest
from backend.app.knowledge.models import (
    AuthorityType,
    CodeRelationship,
    DomainCategory,
    KnowledgeUnit,
    SourceTier,
)
from backend.app.retrieval.ast_retriever import AstCodeRetriever


@pytest.fixture
def sample_units() -> list[KnowledgeUnit]:
    return [
        KnowledgeUnit(
            id="unit_policy_check_price",
            domain=DomainCategory.I_POLICY_ENGINE,
            title="_check_price",
            summary="Validates proposal price against verified catalog price.",
            content="def _check_price(proposal, catalog_item):\n    if proposal.amount != catalog_item.price:\n        raise PolicyViolation('PRICE_MISMATCH')",
            source_type="PYTHON_AST",
            source_path="backend/app/policy/engine.py",
            source_tier=SourceTier.TIER_2_SOURCE_CODE,
            line_start=45,
            line_end=55,
            symbol="_check_price",
            authority=AuthorityType.AUTHORITATIVE,
            content_sha256="sha_ast1",
            relationships=[
                CodeRelationship(
                    source_symbol="_check_price",
                    target_symbol="test_price_tampering_detection",
                    relationship_type="TESTED_BY",
                )
            ],
        ),
        KnowledgeUnit(
            id="unit_test_price",
            domain=DomainCategory.Y_TEST_SUITES,
            title="test_price_tampering_detection",
            summary="Tests that altered price generates PRICE_MISMATCH denial.",
            content="def test_price_tampering_detection(client):\n    res = client.post('/transaction/propose', json={'claimed_price': 10})\n    assert res.json()['data']['verdict'] == 'DENY'",
            source_type="PYTEST",
            source_path="backend/tests/unit/test_policy_engine.py",
            source_tier=SourceTier.TIER_4_AUTOMATED_TESTS,
            line_start=100,
            line_end=120,
            symbol="test_price_tampering_detection",
            authority=AuthorityType.AUTHORITATIVE,
            content_sha256="sha_ast2",
        ),
    ]


def test_ast_find_symbol_evidence(sample_units: list[KnowledgeUnit]) -> None:
    ast_retriever = AstCodeRetriever(sample_units)
    results = ast_retriever.find_symbol_evidence("_check_price")

    assert len(results) == 1
    res = results[0]
    assert res.symbol == "_check_price"
    assert res.source_path == "backend/app/policy/engine.py"
    assert res.line_start == 45
    assert res.line_end == 55
    assert "TESTED_BY" in res.selection_reason


def test_ast_find_code_trace(sample_units: list[KnowledgeUnit]) -> None:
    ast_retriever = AstCodeRetriever(sample_units)
    trace = ast_retriever.find_code_trace(symbol_name="_check_price")

    assert len(trace["logic"]) == 1
    assert trace["logic"][0].symbol == "_check_price"
    assert len(trace["tests"]) >= 1
