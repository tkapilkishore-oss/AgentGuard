from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.models import RetrievalResult, RetrievalScoreBreakdown
from backend.app.retrieval.reranker import AuthorityReranker


def test_authority_precedence_source_code_over_historical_docs() -> None:
    reranker = AuthorityReranker()
    classifier = QueryClassifier()
    qc = classifier.classify("Which function validates price in policy engine?")

    # Candidate 1: Authoritative Code Symbol
    code_cand = RetrievalResult(
        knowledge_unit_id="unit_code_check_price",
        title="_check_price",
        content="def _check_price(): pass",
        summary="Price check function.",
        domain=DomainCategory.I_POLICY_ENGINE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="PYTHON_AST",
        source_path="backend/app/policy/engine.py",
        score=0.80,
        retrieval_method="EXACT",
        content_sha256="sha1",
        score_breakdown=RetrievalScoreBreakdown(
            exact_score=1.0,
            lexical_bm25_score=0.7,
            semantic_score=0.7,
        ),
    )

    # Candidate 2: Historical doc with high semantic score
    doc_cand = RetrievalResult(
        knowledge_unit_id="unit_doc_historical",
        title="Historical Architecture Notes",
        content="In previous versions we checked prices differently.",
        summary="Historical notes on price validation.",
        domain=DomainCategory.I_POLICY_ENGINE,
        source_tier=SourceTier.TIER_6_HISTORICAL,
        authority=AuthorityType.HISTORICAL,
        source_type="DOC",
        source_path="docs/historical/OLD_ARCH.md",
        score=0.90,
        retrieval_method="SEMANTIC",
        content_sha256="sha2",
        score_breakdown=RetrievalScoreBreakdown(
            semantic_score=0.95,
        ),
    )

    ranked = reranker.rerank([doc_cand, code_cand], qc, top_k=2)

    # Assert that code candidate wins top-1 due to authority and tier constraints
    assert ranked[0].knowledge_unit_id == "unit_code_check_price"
    assert ranked[0].source_tier == SourceTier.TIER_2_SOURCE_CODE
    assert ranked[1].knowledge_unit_id == "unit_doc_historical"


def test_reranker_policy_engine_vs_retrieval_engine_collision() -> None:
    reranker = AuthorityReranker()
    classifier = QueryClassifier()
    qc = classifier.classify("Where in the Python codebase is the policy engine verification logic implemented?")

    policy_unit = RetrievalResult(
        knowledge_unit_id="unit_policy_engine_module",
        title="Module: backend/app/policy/engine.py",
        content="PolicyEngine evaluate_policy verify_proposal",
        summary="Policy engine implementation.",
        domain=DomainCategory.I_POLICY_ENGINE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="PYTHON_AST",
        source_path="backend/app/policy/engine.py",
        score=0.70,
        retrieval_method="LEXICAL_BM25",
        content_sha256="sha_policy",
        score_breakdown=RetrievalScoreBreakdown(lexical_bm25_score=0.75, semantic_score=0.75),
    )

    retrieval_unit = RetrievalResult(
        knowledge_unit_id="unit_retrieval_engine_module",
        title="Module: backend/app/retrieval/engine.py",
        content="RetrievalEngine orchestrates exact lexical semantic matchers",
        summary="Retrieval engine implementation.",
        domain=DomainCategory.G_BACKEND_ARCHITECTURE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="PYTHON_AST",
        source_path="backend/app/retrieval/engine.py",
        score=0.75,
        retrieval_method="LEXICAL_BM25",
        content_sha256="sha_retrieval",
        score_breakdown=RetrievalScoreBreakdown(lexical_bm25_score=0.85, semantic_score=0.80),
    )

    ranked = reranker.rerank([retrieval_unit, policy_unit], qc, top_k=2)
    assert ranked[0].knowledge_unit_id == "unit_policy_engine_module", "Policy engine unit must outrank retrieval engine unit for policy queries"


def test_reranker_frontend_views_prefer_physical_components() -> None:
    reranker = AuthorityReranker()
    classifier = QueryClassifier()
    qc = classifier.classify("What are the main frontend views in AgentGuard?")

    view_unit = RetrievalResult(
        knowledge_unit_id="unit_view_home",
        title="UI Component: HomeView (frontend/src/views/HomeView.tsx)",
        content="export const HomeView = () => ...",
        summary="Home view component.",
        domain=DomainCategory.R_FRONTEND_ARCHITECTURE,
        source_tier=SourceTier.TIER_2_SOURCE_CODE,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="TSX_COMPONENT",
        source_path="frontend/src/views/HomeView.tsx",
        score=0.65,
        retrieval_method="LEXICAL_BM25",
        content_sha256="sha_view",
        score_breakdown=RetrievalScoreBreakdown(lexical_bm25_score=0.70, semantic_score=0.70),
    )

    doc_unit = RetrievalResult(
        knowledge_unit_id="unit_prd_doc",
        title="AgentGuard System Definition",
        content="AgentGuard is the deterministic authorization firewall...",
        summary="PRD document.",
        domain=DomainCategory.A_PRODUCT_IDENTITY,
        source_tier=SourceTier.TIER_5_SPEC_DOCS,
        authority=AuthorityType.AUTHORITATIVE,
        source_type="DOC",
        source_path="docs/PRD.md",
        score=0.70,
        retrieval_method="LEXICAL_BM25",
        content_sha256="sha_doc",
        score_breakdown=RetrievalScoreBreakdown(lexical_bm25_score=0.75, semantic_score=0.75),
    )

    ranked = reranker.rerank([doc_unit, view_unit], qc, top_k=2)
    assert ranked[0].knowledge_unit_id == "unit_view_home", "Physical TSX view component must outrank generic PRD doc for frontend views query"
