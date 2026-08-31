"""Pydantic v2 Models and Enums for the AgentGuard Knowledge Pipeline."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceTier(str, Enum):
    """Deterministic Source Precedence Hierarchy."""

    TIER_1_LIVE_TOOL = "TIER_1_LIVE_TOOL"  # PostgreSQL state / live gateway tool
    TIER_2_SOURCE_CODE = "TIER_2_SOURCE_CODE"  # Executable Python / TSX code
    TIER_3_API_SCHEMA = "TIER_3_API_SCHEMA"  # Pydantic models & FastAPI schemas
    TIER_4_AUTOMATED_TESTS = "TIER_4_AUTOMATED_TESTS"  # Pytest test cases
    TIER_5_SPEC_DOCS = "TIER_5_SPEC_DOCS"  # Current docs/*.md specifications
    TIER_6_HISTORICAL = "TIER_6_HISTORICAL"  # Historical notes / background docs


class AuthorityType(str, Enum):
    """Authority Classification for Knowledge Units."""

    AUTHORITATIVE = "AUTHORITATIVE"  # Ground truth derived from executable code / schema
    SOURCE_DERIVED = "SOURCE_DERIVED"  # Extracted from source comments or test descriptions
    HISTORICAL = "HISTORICAL"  # High-level architecture text
    DYNAMIC_LIVE_REQUIRED = "DYNAMIC_LIVE_REQUIRED"  # Must be queried live via backend tool
    CONFLICTING = "CONFLICTING"  # Discrepancy detected across sources
    UNKNOWN = "UNKNOWN"  # Information cannot be determined from verified evidence


class FreshnessStatus(str, Enum):
    """Freshness of Knowledge Unit against current repository state."""

    VERIFIED = "VERIFIED"  # Fingerprint matches active repository state
    CURRENT = "CURRENT"  # Current verified knowledge
    STALE = "STALE"  # Source code has drifted from indexed content
    HISTORICAL = "HISTORICAL"  # Retained historical reference
    CONFLICTING = "CONFLICTING"  # Conflicts with a higher-priority source


class DomainCategory(str, Enum):
    """The 31 Comprehensive Project Knowledge Domains (A through AE)."""

    A_PRODUCT_IDENTITY = "A_PRODUCT_IDENTITY"
    B_PROBLEM_STATEMENT = "B_PROBLEM_STATEMENT"
    C_PURPOSE = "C_PURPOSE"
    D_ARCHITECTURE = "D_ARCHITECTURE"
    E_TRUST_MODEL = "E_TRUST_MODEL"
    F_SECURITY_INVARIANTS = "F_SECURITY_INVARIANTS"
    G_BACKEND_ARCHITECTURE = "G_BACKEND_ARCHITECTURE"
    H_DATABASE_ARCHITECTURE = "H_DATABASE_ARCHITECTURE"
    I_POLICY_ENGINE = "I_POLICY_ENGINE"
    J_MANDATES = "J_MANDATES"
    K_BUDGETS = "K_BUDGETS"
    L_TRANSACTIONS = "L_TRANSACTIONS"
    M_RAZORPAY_INTEGRATION = "M_RAZORPAY_INTEGRATION"
    N_AGENT_BEHAVIOR = "N_AGENT_BEHAVIOR"
    O_ATTACK_SCENARIOS = "O_ATTACK_SCENARIOS"
    P_AUDIT_TRAIL = "P_AUDIT_TRAIL"
    Q_SHA256_HASH_CHAIN = "Q_SHA256_HASH_CHAIN"
    R_FRONTEND_ARCHITECTURE = "R_FRONTEND_ARCHITECTURE"
    S_NAVIGATION = "S_NAVIGATION"
    T_THREAT_SIMULATION_LAB = "T_THREAT_SIMULATION_LAB"
    U_LIVE_PROTECTION = "U_LIVE_PROTECTION"
    V_FORENSIC_LEDGER = "V_FORENSIC_LEDGER"
    W_DEVELOPER_WIRE_TELEMETRY = "W_DEVELOPER_WIRE_TELEMETRY"
    X_CONVERSATIONAL_INTERFACE = "X_CONVERSATIONAL_INTERFACE"
    Y_TEST_SUITES = "Y_TEST_SUITES"
    Z_DESIGN_DECISIONS = "Z_DESIGN_DECISIONS"
    AA_TECHNOLOGY_CHOICES = "AA_TECHNOLOGY_CHOICES"
    AB_LIMITATIONS = "AB_LIMITATIONS"
    AC_FUTURE_ROADMAP = "AC_FUTURE_ROADMAP"
    AD_HACKATHON_DEMO_WORKFLOW = "AD_HACKATHON_DEMO_WORKFLOW"
    AE_CODE_IMPLEMENTATION = "AE_CODE_IMPLEMENTATION"


class DomainCoverageStatus(str, Enum):
    """Domain coverage verification status."""

    COVERED = "COVERED"
    PARTIALLY_COVERED = "PARTIALLY_COVERED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"


class QAStatus(str, Enum):
    """QA Build / Validation Status."""

    BUILDING = "BUILDING"
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    INVALID = "INVALID"


class QASeverity(str, Enum):
    """Severity of a QA Issue."""

    ERROR = "ERROR"  # Critical violation that halts VALID status
    WARNING = "WARNING"  # Discrepancy or stale item that permits build with warnings
    INFO = "INFO"  # Informational observation or gap notice


class QAIssue(BaseModel):
    """QA finding or validation discrepancy."""

    severity: QASeverity
    code: str
    message: str
    source_path: str | None = None
    line_number: int | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class CodeRelationship(BaseModel):
    """Lightweight cross-reference edge between symbols."""

    source_symbol: str
    target_symbol: str
    relationship_type: str  # "CALLS", "HANDLES_ROUTE", "USES_MODEL", "TRIGGERS_API", "TESTS_SYMBOL"
    target_path: str | None = None

    model_config = ConfigDict(extra="ignore")


class KnowledgeUnit(BaseModel):
    """Canonical Atomic Knowledge Unit for RAG grounding and reasoning."""

    id: str  # Deterministic SHA-256 derived identifier
    domain: DomainCategory
    title: str
    summary: str
    content: str
    source_type: str  # "DOC", "PYTHON_AST", "TSX_COMPONENT", "API_ROUTE", "PYTEST", "CANONICAL_FACT"
    source_path: str
    source_tier: SourceTier
    line_start: int | None = None
    line_end: int | None = None
    symbol: str | None = None
    route: str | None = None
    content_sha256: str
    authority: AuthorityType
    freshness: FreshnessStatus = FreshnessStatus.VERIFIED
    relationships: list[CodeRelationship] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    dynamic_tool_fallback: str | None = None  # Tool name to call if dynamic state is requested

    model_config = ConfigDict(extra="ignore")


class CodeSymbolRecord(BaseModel):
    """AST-extracted code symbol metadata."""

    id: str
    name: str
    symbol_type: str  # "module", "class", "function", "method", "pydantic_model", "route_handler"
    file_path: str
    line_start: int
    line_end: int
    docstring: str | None = None
    signature: str | None = None
    decorators: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    content_sha256: str

    model_config = ConfigDict(extra="ignore")


class ApiRouteRecord(BaseModel):
    """Introspected FastAPI route metadata."""

    id: str
    method: str  # "GET", "POST", "PUT", "DELETE"
    path: str
    handler_name: str
    source_file: str
    source_line: int
    request_model: str | None = None
    response_model: str | None = None
    is_mutation: bool
    safety_level: str  # "READ_ONLY", "PROPOSE_ONLY", "REQUIRES_CONFIRMATION", "SUPERVISOR_ONLY"
    security_significance: str

    model_config = ConfigDict(extra="ignore")


class FrontendActionRecord(BaseModel):
    """Extracted Frontend UI surface and action metadata."""

    id: str
    view_name: str
    view_path: str
    component_name: str
    action_label: str
    action_type: str  # "NAVIGATION", "PROPOSAL", "EXECUTION", "SIMULATION", "INSPECTION"
    api_endpoint: str | None = None
    safety_level: str
    description: str

    model_config = ConfigDict(extra="ignore")


class TestKnowledgeRecord(BaseModel):
    """Pytest test case knowledge metadata."""

    id: str
    test_file: str
    test_function: str
    docstring: str | None = None
    test_category: str  # "unit_policy", "unit_endpoint", "integration_e2e", "security_adversarial"
    target_symbols: list[str] = Field(default_factory=list)
    invariants_proven: list[str] = Field(default_factory=list)
    content_sha256: str

    model_config = ConfigDict(extra="ignore")


class CanonicalFactRecord(BaseModel):
    """Hand-curated, authoritative fact record for Domains A-AE."""

    id: str
    domain: DomainCategory
    title: str
    fact_statement: str
    authority: AuthorityType
    source_tier: SourceTier
    rationale: str
    verified_sources: list[str]
    is_dynamic_tool_required: bool = False
    required_tool: str | None = None

    model_config = ConfigDict(extra="ignore")


class CoverageMetrics(BaseModel):
    """Detailed coverage statistics for the Knowledge Base."""

    total_units: int = 0
    docs_chunks: int = 0
    python_symbols: int = 0
    tsx_components: int = 0
    api_routes: int = 0
    test_cases: int = 0
    canonical_facts: int = 0
    domains_covered: int = 0
    domains_gap: int = 0
    unresolved_references: int = 0
    conflicts_detected: int = 0
    stale_records: int = 0

    model_config = ConfigDict(extra="ignore")


class QAReport(BaseModel):
    """Complete Knowledge QA Validation Report."""

    status: QAStatus
    generated_at: str
    commit_fingerprint: str
    metrics: CoverageMetrics
    issues: list[QAIssue] = Field(default_factory=list)
    domain_coverage: dict[str, DomainCoverageStatus] = Field(default_factory=dict)
    secret_scan_clean: bool = False

    model_config = ConfigDict(extra="ignore")


class KnowledgeManifest(BaseModel):
    """Manifest for generated knowledge assets."""

    version: str = "5.5B-1.0.0"
    status: QAStatus
    built_at: str
    commit_sha: str
    content_sha256: str
    metrics: CoverageMetrics
    dataset_files: dict[str, str] = Field(default_factory=dict)  # filename -> sha256

    model_config = ConfigDict(extra="ignore")
