"""Pydantic v2 Models and Contracts for AgentGuard Conversational Brain."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.models import EvidenceSet, QueryCategory, QueryClassification, RetrievalResult


class UserIntentCategory(str, Enum):
    """High-level conversational intent taxonomy."""

    CONCEPT_EXPLANATION = "CONCEPT_EXPLANATION"  # Architecture, trust boundary, philosophy, identity
    SECURITY_SCENARIO = "SECURITY_SCENARIO"  # Threat analysis, price tampering, replay, escalation
    CODE_REFERENCE = "CODE_REFERENCE"  # Implementation lookup, symbol definition, file location
    FRONTEND_NAVIGATION = "FRONTEND_NAVIGATION"  # UI navigation, component inspection, live demo pages
    LIVE_DATA_QUERY = "LIVE_DATA_QUERY"  # Authoritative runtime state (mandate balance, inventory, tx status)
    PROGRESSIVE_FOLLOWUP = "PROGRESSIVE_FOLLOWUP"  # Affirmative ("yes", "show code", "explain more", "why?")
    TOPIC_SWITCH = "TOPIC_SWITCH"  # User changes topic or rejects previous offer ("no", "forget that")
    ADVERSARIAL_INJECTION = "ADVERSARIAL_INJECTION"  # Prompt injection, policy override, secret exfiltration
    TRANSACTION_INQUIRY = "TRANSACTION_INQUIRY"  # Specific transaction details or audit ledger check
    OUT_OF_SCOPE = "OUT_OF_SCOPE"  # Off-topic questions outside AgentGuard
    GREETING_OR_META = "GREETING_OR_META"  # Greetings, help, capabilities overview


class DialogueAct(str, Enum):
    """Conversational speech act classification."""

    INFORM = "INFORM"  # Providing factual information
    CLARIFY = "CLARIFY"  # Asking for clarification on ambiguous input
    NAVIGATE = "NAVIGATE"  # Recommending or triggering a UI surface
    REFUSE_ADVERSARIAL = "REFUSE_ADVERSARIAL"  # Rejecting prompt injection or secret exfiltration
    LIVE_STATUS = "LIVE_STATUS"  # Providing live runtime readings
    PROGRESSIVE_OFFER = "PROGRESSIVE_OFFER"  # Offering a deeper technical or UI layer
    AWAITING_INPUT = "AWAITING_INPUT"  # Waiting for normal user turn


class EntityReference(BaseModel):
    """Resolved entity from conversation context or query."""

    entity_type: str  # e.g., "mandate_id", "transaction_id", "product_id", "symbol_name", "scenario_id"
    value: str
    confidence: float = 1.0
    source: str = "query"  # "query", "context_history", "active_topic"

    model_config = ConfigDict(extra="ignore")


class TopicContext(BaseModel):
    """Active conversational topic and hierarchy."""

    topic_name: str  # e.g., "PRICE_TAMPERING", "AUDIT_CHAIN", "MANDATE_BUDGET", "GENERAL_ARCHITECTURE"
    parent_topic: str | None = None
    depth: int = 1
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_turn: int = 1
    key_symbols: list[str] = Field(default_factory=list)
    key_entities: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class ConversationAction(BaseModel):
    """Optional UI or navigation action accompanying an assistant response."""

    action_type: str  # e.g., "NAVIGATE_TAB", "TRIGGER_SCENARIO", "INSPECT_TRANSACTION", "HIGHLIGHT_CODE"
    payload: dict[str, Any] = Field(default_factory=dict)
    ui_tab_target: str | None = None  # e.g., "DEFENSE", "THREAT", "FORENSICS", "TELEMETRY", "COCKPIT"
    scenario_id: int | None = None  # e.g., 2, 3, 4

    model_config = ConfigDict(extra="ignore")


class FollowUpSuggestion(BaseModel):
    """Suggested follow-up question or deep-dive offer."""

    label: str  # Short button label e.g., "View Code", "Check Live Balance"
    query: str  # Full query text if clicked e.g., "Where is price tampering implemented in the code?"
    intent_target: UserIntentCategory
    rationale: str

    model_config = ConfigDict(extra="ignore")


class LiveToolType(str, Enum):
    """Types of safe, read-only live runtime state queries."""

    MANDATE_BUDGET = "MANDATE_BUDGET"
    TRANSACTION_STATUS = "TRANSACTION_STATUS"
    PRODUCT_CATALOG = "PRODUCT_CATALOG"
    AUDIT_CHAIN_INTEGRITY = "AUDIT_CHAIN_INTEGRITY"


class LiveToolRequest(BaseModel):
    """Request envelope for authoritative live runtime data."""

    tool_type: LiveToolType
    parameters: dict[str, Any] = Field(default_factory=dict)
    reason: str

    model_config = ConfigDict(extra="ignore")


class LiveToolResult(BaseModel):
    """Authoritative result envelope from live runtime backend query."""

    tool_type: LiveToolType
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    execution_latency_ms: float = 0.0
    error: str | None = None

    model_config = ConfigDict(extra="ignore")


class EvidenceContext(BaseModel):
    """Assembled evidence context combining static retrieval and/or live data."""

    static_evidence: EvidenceSet | None = None
    live_result: LiveToolResult | None = None
    is_live: bool = False
    provenance_unit_ids: list[str] = Field(default_factory=list)
    authorities: list[AuthorityType] = Field(default_factory=list)
    source_tiers: list[SourceTier] = Field(default_factory=list)
    confidence: float = 1.0
    summary_notes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class ProgressiveDisclosureOffer(BaseModel):
    """A pending offer made to the user for progressive disclosure."""

    offer_type: str  # "CODE_IMPLEMENTATION", "LIVE_STATE", "SCENARIO_SIMULATION", "DEEP_EXPLANATION"
    target_symbol: str | None = None
    target_file: str | None = None
    target_action: ConversationAction | None = None
    prompt_text: str  # e.g., "I can also show you where this is implemented in the codebase if you'd like."

    model_config = ConfigDict(extra="ignore")


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""

    turn_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_query: str
    assistant_response: str
    intent: UserIntentCategory
    dialogue_act: DialogueAct
    resolved_entities: dict[str, str] = Field(default_factory=dict)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    live_tool_called: LiveToolType | None = None
    action_triggered: ConversationAction | None = None
    progressive_offer: ProgressiveDisclosureOffer | None = None
    latency_ms: float = 0.0

    model_config = ConfigDict(extra="ignore")


class ConversationSession(BaseModel):
    """Complete conversation session state."""

    session_id: str
    user_id: str = "user-001"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[ConversationTurn] = Field(default_factory=list)
    active_topic: TopicContext | None = None
    topic_history: list[TopicContext] = Field(default_factory=list)
    active_entities: dict[str, str] = Field(default_factory=dict)
    pending_progressive_offer: ProgressiveDisclosureOffer | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")


class ResponsePlan(BaseModel):
    """Internal orchestration plan before response synthesis."""

    intent: UserIntentCategory
    dialogue_act: DialogueAct
    resolved_query: str  # Disambiguated / coreferenced query
    needs_static_retrieval: bool = False
    needs_live_tool: bool = False
    live_tool_request: LiveToolRequest | None = None
    is_adversarial: bool = False
    adversarial_reason: str | None = None
    progressive_stage: str = "INITIAL"  # "INITIAL", "FOLLOWUP_ACCEPTED", "REJECTED_SWITCH"
    offer_to_make: ProgressiveDisclosureOffer | None = None
    suggested_followups: list[FollowUpSuggestion] = Field(default_factory=list)
    suggested_action: ConversationAction | None = None

    model_config = ConfigDict(extra="ignore")


class BrainTrace(BaseModel):
    """Structured observability and debug trace for a conversational turn."""

    session_id: str
    turn_id: int
    raw_query: str
    resolved_query: str
    intent: UserIntentCategory
    is_dynamic_live: bool
    live_tool_type: LiveToolType | None = None
    retrieved_unit_ids: list[str] = Field(default_factory=list)
    top_authority: AuthorityType | None = None
    safety_verdict: str = "SAFE"
    progressive_action: str | None = None
    llm_provider: str = "mock"
    latency_total_ms: float = 0.0
    latency_retrieval_ms: float = 0.0
    latency_live_ms: float = 0.0
    latency_llm_ms: float = 0.0

    model_config = ConfigDict(extra="ignore")


class AssistantResponse(BaseModel):
    """Unified user-facing conversational response envelope."""

    session_id: str
    turn_id: int
    message: str
    intent: UserIntentCategory
    dialogue_act: DialogueAct
    evidence_citations: list[dict[str, Any]] = Field(default_factory=list)
    live_data_used: bool = False
    live_readings: dict[str, Any] | None = None
    progressive_disclosure_offer: str | None = None
    suggested_followups: list[FollowUpSuggestion] = Field(default_factory=list)
    action: ConversationAction | None = None
    trace: BrainTrace | None = None

    model_config = ConfigDict(extra="ignore")
