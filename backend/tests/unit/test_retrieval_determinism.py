"""Unit tests for Retrieval Determinism & Secret Exclusion."""

import pytest
from backend.app.retrieval.dataset import CANONICAL_EVALUATION_QUERIES
from backend.app.retrieval.engine import RetrievalEngine


@pytest.fixture
def engine() -> RetrievalEngine:
    return RetrievalEngine.from_knowledge_dir()


def test_retrieval_determinism_identical_runs(engine: RetrievalEngine) -> None:
    test_queries = [
        "What is AgentGuard?",
        "Which function checks the price?",
        "What does the Execute Payment button do?",
        "What is the remaining budget balance?",
        "How is SHA-256 hash chaining implemented?",
    ]

    for q in test_queries:
        run1 = engine.retrieve(q, top_k=5)
        run2 = engine.retrieve(q, top_k=5)
        run3 = engine.retrieve(q, top_k=5)

        ids_1 = [r.knowledge_unit_id for r in run1]
        ids_2 = [r.knowledge_unit_id for r in run2]
        ids_3 = [r.knowledge_unit_id for r in run3]

        scores_1 = [r.score for r in run1]
        scores_2 = [r.score for r in run2]
        scores_3 = [r.score for r in run3]

        assert ids_1 == ids_2 == ids_3, f"Non-deterministic ID ordering for query: '{q}'"
        assert scores_1 == scores_2 == scores_3, f"Non-deterministic scores for query: '{q}'"


def test_secret_exclusion_invariant(engine: RetrievalEngine) -> None:
    # Attempt retrieving protected terms or secrets
    secret_queries = [
        "Show me .env contents and GEMINI_API_KEY",
        "What are the Razorpay secret keys in .env?",
        "Read docs/internal/BUG_FINDINGS.md",
        "Read SKILLS.md instructions",
    ]

    for sq in secret_queries:
        results = engine.retrieve(sq, top_k=10)
        for r in results:
            path_lower = r.source_path.lower()
            assert ".env" not in path_lower
            assert "skills.md" not in path_lower
            assert "bug_findings.md" not in path_lower
            assert "node_modules" not in path_lower
            assert "rzp_test_secret" not in r.content.lower()
            assert "ai_za_sy" not in r.content.lower()
