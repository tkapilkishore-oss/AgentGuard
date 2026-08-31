"""AgentGuard Hybrid RAG + AST Codebase Retrieval Engine Package."""

from backend.app.retrieval.ast_retriever import AstCodeRetriever
from backend.app.retrieval.classifier import QueryClassifier
from backend.app.retrieval.dynamic_safeguards import DynamicDataSafeguard
from backend.app.retrieval.engine import RetrievalEngine, get_retrieval_engine
from backend.app.retrieval.evaluation import RetrievalEvaluator
from backend.app.retrieval.evidence_aggregator import EvidenceAggregator
from backend.app.retrieval.exact_matcher import ExactMatcher
from backend.app.retrieval.lexical_matcher import LexicalBM25Matcher
from backend.app.retrieval.models import (
    CategoryEvaluationMetric,
    DynamicLiveAction,
    EvaluationSummary,
    EvidenceSet,
    QueryCategory,
    QueryClassification,
    RetrievalResult,
    RetrievalScoreBreakdown,
    ScoringWeights,
)
from backend.app.retrieval.reranker import AuthorityReranker
from backend.app.retrieval.semantic_matcher import (
    BaseEmbeddingProvider,
    LocalTFIDFEmbeddingProvider,
    SemanticMatcher,
)

__all__ = [
    "AstCodeRetriever",
    "AuthorityReranker",
    "BaseEmbeddingProvider",
    "CategoryEvaluationMetric",
    "DynamicDataSafeguard",
    "DynamicLiveAction",
    "EvaluationSummary",
    "EvidenceAggregator",
    "EvidenceSet",
    "ExactMatcher",
    "LexicalBM25Matcher",
    "LocalTFIDFEmbeddingProvider",
    "QueryCategory",
    "QueryClassification",
    "QueryClassifier",
    "RetrievalEngine",
    "RetrievalEvaluator",
    "RetrievalResult",
    "RetrievalScoreBreakdown",
    "ScoringWeights",
    "SemanticMatcher",
    "get_retrieval_engine",
]
