"""Pydantic v2 Models and Enums for the AgentGuard Hybrid Retrieval Engine."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.knowledge.models import (
    AuthorityType,
    DomainCategory,
    KnowledgeUnit,
    SourceTier,
)


class QueryCategory(str, Enum):
    """Retrieval Query Intent Classification."""

    CONCEPTUAL_PROJECT = "CONCEPTUAL_PROJECT"  # Architecture, trust boundary, philosophy, identity
    SECURITY_SCENARIO = "SECURITY_SCENARIO"  # Attack simulation, threat defense, invariant enforcement
    CODE_SYMBOL = "CODE_SYMBOL"  # Python function, class, model, signature lookup
    API_ROUTE = "API_ROUTE"  # FastAPI endpoints, payload schemas, HTTP status codes
    FRONTEND_ACTION = "FRONTEND_ACTION"  # UI components, buttons, views, Claim Diff
    TEST_VERIFICATION = "TEST_VERIFICATION"  # Pytest suites, test cases, invariant proofs
    DYNAMIC_LIVE_DATA = "DYNAMIC_LIVE_DATA"  # Runtime balance, transaction state, live stock
    MULTI_SOURCE_SYSTEM = "MULTI_SOURCE_SYSTEM"  # Cross-cutting queries (Policy + API + UI + Test)


class DynamicLiveAction(BaseModel):
    """Action requirement for dynamic runtime state queries."""

    live_query_required: bool = True
    target_resource: str  # e.g., "mandate_budget", "transaction_status", "product_stock", "audit_chain"
    required_endpoint: str  # e.g., "GET /mandate/{id}", "GET /transaction/{id}"
    reason: str
    static_provenance_unit_id: str | None = None

    model_config = ConfigDict(extra="ignore")


class QueryClassification(BaseModel):
    """Lightweight retrieval-oriented query classification."""

    raw_query: str
    normalized_query: str
    category: QueryCategory
    extracted_symbols: list[str] = Field(default_factory=list)
    extracted_routes: list[str] = Field(default_factory=list)
    extracted_actions: list[str] = Field(default_factory=list)
    extracted_components: list[str] = Field(default_factory=list)
    extracted_scenario: str | None = None
    domain_hints: list[DomainCategory] = Field(default_factory=list)
    is_dynamic_live: bool = False
    dynamic_action: DynamicLiveAction | None = None
    preferred_tiers: list[SourceTier] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class RetrievalScoreBreakdown(BaseModel):
    """Detailed score breakdown for explainability."""

    exact_score: float = 0.0
    lexical_bm25_score: float = 0.0
    semantic_score: float = 0.0
    domain_bonus: float = 0.0
    authority_score: float = 0.0
    source_tier_score: float = 0.0
    query_alignment_bonus: float = 0.0
    total_score: float = 0.0

    model_config = ConfigDict(extra="ignore")


class RetrievalResult(BaseModel):
    """Unified retrieval result contract preserving complete provenance."""

    knowledge_unit_id: str
    title: str
    content: str
    summary: str
    domain: DomainCategory
    source_tier: SourceTier
    authority: AuthorityType
    source_type: str
    source_path: str
    line_start: int | None = None
    line_end: int | None = None
    symbol: str | None = None
    route: str | None = None
    frontend_action: str | None = None
    score: float
    retrieval_method: str  # "EXACT", "LEXICAL_BM25", "SEMANTIC", "HYBRID_RERANKED", "DYNAMIC_SAFEGUARD"
    dynamic_live_required: bool = False
    dynamic_tool_fallback: str | None = None
    tags: list[str] = Field(default_factory=list)
    content_sha256: str
    selection_reason: str = ""
    score_breakdown: RetrievalScoreBreakdown = Field(default_factory=RetrievalScoreBreakdown)

    model_config = ConfigDict(extra="ignore")


class EvidenceSet(BaseModel):
    """Minimal sufficient multi-source evidence set for a query."""

    query: str
    classification: QueryClassification
    primary_result: RetrievalResult | None = None
    code_evidence: RetrievalResult | None = None
    api_evidence: RetrievalResult | None = None
    test_evidence: RetrievalResult | None = None
    frontend_evidence: RetrievalResult | None = None
    conceptual_evidence: RetrievalResult | None = None
    all_results: list[RetrievalResult] = Field(default_factory=list)
    total_candidates: int = 0
    latency_ms: float = 0.0

    model_config = ConfigDict(extra="ignore")


class ScoringWeights(BaseModel):
    """Deterministic reranking weights configuration."""

    w_exact: float = 0.35
    w_lexical: float = 0.25
    w_semantic: float = 0.15
    w_authority: float = 0.15
    w_domain: float = 0.10
    bonus_alignment: float = 0.15

    model_config = ConfigDict(extra="ignore")


class CategoryEvaluationMetric(BaseModel):
    """Metrics for a specific evaluation category."""

    category: str
    total_queries: int = 0
    top1_hits: int = 0
    top3_hits: int = 0
    top5_hits: int = 0
    domain_correct: int = 0
    authority_correct: int = 0
    dynamic_correct: int = 0

    @property
    def top1_accuracy(self) -> float:
        return (self.top1_hits / self.total_queries * 100.0) if self.total_queries > 0 else 0.0

    @property
    def top3_accuracy(self) -> float:
        return (self.top3_hits / self.total_queries * 100.0) if self.total_queries > 0 else 0.0

    @property
    def top5_accuracy(self) -> float:
        return (self.top5_hits / self.total_queries * 100.0) if self.total_queries > 0 else 0.0


class EvaluationSummary(BaseModel):
    """Overall benchmark evaluation metrics."""

    total_queries: int = 0
    overall_top1_accuracy: float = 0.0
    overall_top3_accuracy: float = 0.0
    overall_top5_accuracy: float = 0.0
    overall_domain_accuracy: float = 0.0
    overall_authority_accuracy: float = 0.0
    dynamic_classification_accuracy: float = 0.0
    code_symbol_retrieval_accuracy: float = 0.0
    frontend_action_retrieval_accuracy: float = 0.0
    secret_leakage_detected: bool = False
    determinism_verified: bool = False
    categories: dict[str, CategoryEvaluationMetric] = Field(default_factory=dict)
    latency_cold_ms: float = 0.0
    latency_warm_ms: float = 0.0
    latency_repeated_ms: float = 0.0

    model_config = ConfigDict(extra="ignore")
