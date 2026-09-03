"""Pydantic v2 Models and Contracts for AgentGuard Conversational Brain."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_serializer

from backend.app.knowledge.models import AuthorityType, DomainCategory, SourceTier
from backend.app.retrieval.models import EvidenceSet, QueryCategory, QueryClassification, RetrievalResult


class CanonicalTopic(str, Enum):
    """Canonical topics taxonomy across the AgentGuard security system."""

    GENERAL_ARCHITECTURE = "GENERAL_ARCHITECTURE"  # Identity, trust boundaries, dual-loop model
    PRICE_TAMPERING = "PRICE_TAMPERING"  # Price manipulation, catalog check, claim diff, mismatch
    REPLAY_ATTACK = "REPLAY_ATTACK"  # Idempotency, duplicate execution, 409 rejection
    AUDIT_CHAIN = "AUDIT_CHAIN"  # Append-only SHA-256 forward hash chain, tamper detection
    MANDATE_BUDGET = "MANDATE_BUDGET"  # Spending limits, mandate budgets, shortfall, escalation
    MERCHANT_SCOPE = "MERCHANT_SCOPE"  # Authorized merchant validation
    CLAIM_DIFF = "CLAIM_DIFF"  # Proposal claim vs authoritative catalog diff
    TRANSACTION_EXECUTION = "TRANSACTION_EXECUTION"  # Loop 2 payment execution via Razorpay
    THREAT_LAB = "THREAT_LAB"  # Interactive demonstration of 4 attack vectors
    FORENSIC_LEDGER = "FORENSIC_LEDGER"  # Forensic audit ledger inspection UI


class UserIntentCategory(str, Enum):
    """High-level conversational intent taxonomy."""

    CONCEPT_EXPLANATION = "CONCEPT_EXPLANATION"  # Architecture, trust boundary, philosophy, identity
    PROJECT_WALKTHROUGH = "PROJECT_WALKTHROUGH"  # End-to-end judge demo, architecture overview, and UI tour
    SECURITY_SCENARIO = "SECURITY_SCENARIO"  # Threat analysis, price tampering, replay, escalation
    PRICE_TAMPERING = "PRICE_TAMPERING"  # Price tampering detection and Claim Diff
    REPLAY_ATTACK = "REPLAY_ATTACK"  # Replay attack prevention and idempotency
    AUDIT_CHAIN = "AUDIT_CHAIN"  # Append-only cryptographic audit trail
    MANDATE_BUDGET = "MANDATE_BUDGET"  # Mandate budget and spending limits
    LIVE_PROTECTION = "LIVE_PROTECTION"  # Live protection firewall invariants
    CODE_REFERENCE = "CODE_REFERENCE"  # Implementation lookup, symbol definition, file location
    FRONTEND_NAVIGATION = "FRONTEND_NAVIGATION"  # UI navigation, component inspection, live demo pages
    LIVE_DATA_QUERY = "LIVE_DATA_QUERY"  # Authoritative runtime state (mandate balance, inventory, tx status)
    PROGRESSIVE_FOLLOWUP = "PROGRESSIVE_FOLLOWUP"  # Affirmative ("yes", "show code", "explain more", "why?")
    TOPIC_SWITCH = "TOPIC_SWITCH"  # User changes topic or rejects previous offer ("no", "forget that")
    ADVERSARIAL_INJECTION = "ADVERSARIAL_INJECTION"  # Prompt injection, policy override, secret exfiltration
    TRANSACTION_INQUIRY = "TRANSACTION_INQUIRY"  # Specific transaction details or audit ledger check
    OUT_OF_SCOPE = "OUT_OF_SCOPE"  # Off-topic questions outside AgentGuard
    GREETING_OR_META = "GREETING_OR_META"  # Greetings, help, capabilities overview



class ConversationalPurpose(str, Enum):
    """Specific communicative purpose of the user's current turn."""

    INFORMATION_REQUEST = "INFORMATION_REQUEST"  # Definition / Identity / "What is AgentGuard?"
    PROJECT_WALKTHROUGH = "PROJECT_WALKTHROUGH"  # End-to-end judge walkthrough and system overview
    FUNCTIONAL_EXPLANATION = "FUNCTIONAL_EXPLANATION"  # Operational role / "What does AgentGuard actually do?"
    WHY_QUESTION = "WHY_QUESTION"  # Rationale / "Why was AgentGuard built?" / "Why is that dangerous?"
    HOW_QUESTION = "HOW_QUESTION"  # Mechanism / "How does the dual-loop firewall work?" / "How is that prevented?"
    HUMAN_APPROVAL_INQUIRY = "HUMAN_APPROVAL_INQUIRY"  # Manual human supervisor approval flow and policy escalation
    VALUE_PROPOSITION = "VALUE_PROPOSITION"  # Problem / Benefit / "Why would anyone need this?"
    COMPARISON = "COMPARISON"  # Differentiation / "How is this different from a normal gateway?"
    EXAMPLE_REQUEST = "EXAMPLE_REQUEST"  # Concrete demonstration / "Give me a real example"
    COUNTERFACTUAL = "COUNTERFACTUAL"  # "What happens if AgentGuard wasn't there?" / "What if the price changes?"
    TIMING_CHECK = "TIMING_CHECK"  # "Is that check done before payment?" / "When does this occur?"
    CLARIFICATION = "CLARIFICATION"  # Simplification / "Explain without code"
    FOLLOW_UP = "FOLLOW_UP"  # Continuation / "Tell me more about that"
    DEEP_DIVE = "DEEP_DIVE"  # In-depth architectural analysis
    SUMMARY_REQUEST = "SUMMARY_REQUEST"  # Synthesis / "Summarize the key points"
    CODE_LOCATION_REQUEST = "CODE_LOCATION_REQUEST"  # Implementation lookup / "Where is that coded?"
    UI_NAVIGATION_REQUEST = "UI_NAVIGATION_REQUEST"  # Surface navigation / "Which tab/page?"
    LIVE_STATE_REQUEST = "LIVE_STATE_REQUEST"  # Runtime balance / catalog check
    TOPIC_SWITCH = "TOPIC_SWITCH"  # Natural context change / "Forget that, tell me about X"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"  # Unrelated query / weather, astronomy, cooking
    ADVERSARIAL = "ADVERSARIAL"  # Injection, secret leak, or financial execution attempt


class ResponseStrategy(str, Enum):
    """Dynamic response strategy tailoring the explanation angle to avoid repetition."""

    INTRODUCE = "INTRODUCE"  # Concise definition & system identity
    WALKTHROUGH = "WALKTHROUGH"  # Structured 2-minute judge walkthrough covering problem, architecture, and demo path
    EXPLAIN_FUNCTION = "EXPLAIN_FUNCTION"  # Operational role & step-by-step transaction interception flow
    EXPLAIN_WHY = "EXPLAIN_WHY"  # Problem context & value proposition / risk analysis
    EXPLAIN_HOW = "EXPLAIN_HOW"  # Mechanism, verification flow & math/rules
    EXPLAIN_HUMAN_APPROVAL = "EXPLAIN_HUMAN_APPROVAL"  # Human approval workflow for policy escalation vs hard denials
    DIFFERENTIATE = "DIFFERENTIATE"  # Explicit contrast between traditional gateways and AgentGuard
    GIVE_EXAMPLE = "GIVE_EXAMPLE"  # Concrete shopping scenario (e.g. price tampering walkthrough)
    EXPLAIN_COUNTERFACTUAL = "EXPLAIN_COUNTERFACTUAL"  # Counterfactual risk and behavior without protections
    EXPLAIN_TIMING = "EXPLAIN_TIMING"  # Verification timing (Loop 1 proposal before Loop 2 payment)
    DEEPEN = "DEEPEN"  # Deeper technical mechanics & invariants
    CLARIFY = "CLARIFY"  # High-level conceptual explanation without technical jargon
    SUMMARIZE = "SUMMARIZE"  # Bulleted summary of previously explained components
    PROVIDE_CODE_LOCATION = "PROVIDE_CODE_LOCATION"  # Exact file path & function name
    PROVIDE_UI_LOCATION = "PROVIDE_UI_LOCATION"  # Interactive surface & navigation action
    REPORT_LIVE_STATE = "REPORT_LIVE_STATE"  # Server-authoritative database readings
    REPORT_TRANSACTION_HISTORY = "REPORT_TRANSACTION_HISTORY"  # Authoritative summary of recorded transactions
    REPORT_MERCHANT_CATALOG = "REPORT_MERCHANT_CATALOG"  # Authoritative list of active merchants
    CHANGE_TOPIC = "CHANGE_TOPIC"  # Clean transition to a new subject
    REFUSE_OUT_OF_SCOPE = "REFUSE_OUT_OF_SCOPE"  # Polite, dynamic refusal with AgentGuard redirection
    REFUSE_ADVERSARIAL = "REFUSE_ADVERSARIAL"  # Zero-financial-authority enforcement notice


class DialogueAct(str, Enum):
    """Conversational speech act classification."""

    INFORM = "INFORM"  # Providing factual information
    CLARIFY = "CLARIFY"  # Asking for clarification on ambiguous input
    NAVIGATE = "NAVIGATE"  # Recommending or triggering a UI surface
    REFUSE_ADVERSARIAL = "REFUSE_ADVERSARIAL"  # Rejecting prompt injection or secret exfiltration
    REFUSE_OUT_OF_SCOPE = "REFUSE_OUT_OF_SCOPE"  # Polite redirection for off-topic query
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

    canonical_topic: CanonicalTopic = CanonicalTopic.GENERAL_ARCHITECTURE
    topic_name: str  # Display name e.g. "Price Tampering Protection", "Cryptographic Audit Ledger"
    parent_topic: str | None = None
    depth: int = 1
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active_turn: int = 1
    key_symbols: list[str] = Field(default_factory=list)
    key_entities: dict[str, str] = Field(default_factory=dict)
    last_mechanism: str | None = None

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
    MERCHANT_CATALOG = "MERCHANT_CATALOG"
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
    purpose: ConversationalPurpose | None = None
    strategy: ResponseStrategy | None = None
    canonical_topic: CanonicalTopic | None = None
    resolved_entities: dict[str, str] = Field(default_factory=dict)
    retrieved_evidence_ids: list[str] = Field(default_factory=list)
    live_tool_called: LiveToolType | None = None
    action_triggered: ConversationAction | None = None
    progressive_offer: ProgressiveDisclosureOffer | None = None
    latency_ms: float = 0.0

    @computed_field  # type: ignore[misc]
    @property
    def query(self) -> str:
        return self.user_query

    @computed_field  # type: ignore[misc]
    @property
    def message(self) -> str:
        return self.assistant_response

    model_config = ConfigDict(extra="ignore")


class ConversationSession(BaseModel):
    """Complete conversation session state with semantic context tracking."""

    session_id: str
    user_id: str = "user-001"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[ConversationTurn] = Field(default_factory=list)
    active_topic: TopicContext | None = None
    topic_history: list[TopicContext] = Field(default_factory=list)
    active_entities: dict[str, str] = Field(default_factory=dict)
    pending_progressive_offer: ProgressiveDisclosureOffer | None = None
    facts_already_explained: list[str] = Field(default_factory=list)
    examples_already_used: list[str] = Field(default_factory=list)
    code_locations_already_shown: list[str] = Field(default_factory=list)
    pages_already_referenced: list[str] = Field(default_factory=list)
    previous_response_summaries: list[str] = Field(default_factory=list)
    offers_already_made: list[str] = Field(default_factory=list)
    current_user_goal: str | None = None
    previous_assistant_claim: str | None = None
    conversation_depth: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_serializer("active_topic")
    def serialize_active_topic(self, v: TopicContext | None) -> str | None:
        if v is not None:
            return v.canonical_topic.value
        return None

    @computed_field  # type: ignore[misc]
    @property
    def turn_count(self) -> int:
        return len(self.history)

    @computed_field  # type: ignore[misc]
    @property
    def turns(self) -> list[ConversationTurn]:
        return self.history

    @computed_field  # type: ignore[misc]
    @property
    def dialogue_state(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_count": len(self.history),
            "active_topic": self.active_topic.canonical_topic.value if self.active_topic else "",
            "active_entities": self.active_entities,
            "depth": self.conversation_depth,
        }

    model_config = ConfigDict(extra="ignore")


class ResponsePlan(BaseModel):
    """Internal orchestration plan before response synthesis."""

    intent: UserIntentCategory
    dialogue_act: DialogueAct
    purpose: ConversationalPurpose = ConversationalPurpose.INFORMATION_REQUEST
    strategy: ResponseStrategy = ResponseStrategy.INTRODUCE
    canonical_topic: CanonicalTopic = CanonicalTopic.GENERAL_ARCHITECTURE
    strategy_rationale: str = ""
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
    compound_query: bool = False
    sub_intents: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class BrainTrace(BaseModel):
    """Structured observability and debug trace for a conversational turn."""

    session_id: str
    turn_id: int
    raw_query: str
    resolved_query: str
    intent: UserIntentCategory
    purpose: str | None = None
    strategy: str | None = None
    canonical_topic: str | None = None
    is_dynamic_live: bool
    live_tool_type: LiveToolType | None = None
    retrieved_unit_ids: list[str] = Field(default_factory=list)
    top_authority: AuthorityType | None = None
    safety_verdict: str = "SAFE"
    progressive_action: str | None = None
    llm_provider: str = "mock"
    repetition_detected: bool = False
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
    intent: str
    dialogue_act: DialogueAct
    evidence_citations: list[dict[str, Any]] = Field(default_factory=list)
    live_data_used: bool = False
    live_readings: dict[str, Any] = Field(default_factory=dict)
    progressive_disclosure_offer: str | None = ""
    suggested_followups: list[FollowUpSuggestion | str] = Field(default_factory=list)
    action: dict[str, Any] | ConversationAction = Field(default_factory=dict)
    trace: BrainTrace | None = None

    @field_serializer("suggested_followups", when_used="always")
    def serialize_suggested_followups(self, v: list[FollowUpSuggestion | str]) -> list[str]:
        result: list[str] = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, FollowUpSuggestion):
                result.append(item.query or item.label)
            elif isinstance(item, dict):
                result.append(str(item.get("query") or item.get("label") or ""))
            else:
                result.append(str(item))
        return result

    @computed_field  # type: ignore[misc]
    @property
    def structured_followups(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for item in self.suggested_followups:
            if isinstance(item, FollowUpSuggestion):
                result.append(item.model_dump())
            elif isinstance(item, dict):
                result.append(item)
            elif isinstance(item, str):
                result.append({"label": item, "query": item, "intent_target": "CONCEPT_EXPLANATION", "rationale": item})
        return result

    model_config = ConfigDict(extra="ignore")

