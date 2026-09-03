"""Thread-safe Conversation State and Dialogue Management for AgentGuard."""

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.conversational.models import (
    ConversationAction,
    ConversationSession,
    ConversationTurn,
    DialogueAct,
    LiveToolType,
    ProgressiveDisclosureOffer,
    TopicContext,
    UserIntentCategory,
)


class DialogueManager:
    """Manages active conversation sessions, turn histories, active topics,

    entity references, and progressive disclosure state in a thread-safe manner.
    """

    def __init__(self, max_sessions: int = 1000, max_history_turns: int = 20) -> None:
        self.max_sessions = max_sessions
        self.max_history_turns = max_history_turns
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = threading.RLock()

    def get_or_create_session(
        self, session_id: str | None = None, user_id: str = "user-001"
    ) -> ConversationSession:
        """Retrieves an existing session or creates a new one with a unique session ID."""
        with self._lock:
            if not session_id:
                session_id = f"sess_{uuid.uuid4().hex[:12]}"

            if session_id not in self._sessions:
                # Evict oldest session if capacity reached
                if len(self._sessions) >= self.max_sessions:
                    oldest_id = min(self._sessions.keys(), key=lambda k: self._sessions[k].updated_at)
                    del self._sessions[oldest_id]

                new_session = ConversationSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    history=[],
                    active_topic=None,
                    topic_history=[],
                    active_entities={"user_id": user_id, "mandate_id": "mandate-001"},
                    pending_progressive_offer=None,
                )
                self._sessions[session_id] = new_session

            return self._sessions[session_id]

    def get_session(self, session_id: str) -> ConversationSession | None:
        """Returns session if exists, otherwise None."""
        with self._lock:
            return self._sessions.get(session_id)

    def record_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        intent: UserIntentCategory,
        dialogue_act: DialogueAct,
        purpose: Any | None = None,
        strategy: Any | None = None,
        canonical_topic: Any | None = None,
        resolved_entities: dict[str, str] | None = None,
        retrieved_evidence_ids: list[str] | None = None,
        live_tool_called: LiveToolType | None = None,
        action_triggered: ConversationAction | None = None,
        progressive_offer: ProgressiveDisclosureOffer | None = None,
        latency_ms: float = 0.0,
    ) -> ConversationTurn:
        """Appends a turn to the session history, updates entity/topic/semantic state, and advances turn counter."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session = self.get_or_create_session(session_id)

            turn_id = len(session.history) + 1
            # Clean boundary conversion: empty dict or invalid action maps to None internally
            internal_action: ConversationAction | None = None
            if isinstance(action_triggered, ConversationAction):
                internal_action = action_triggered
            elif isinstance(action_triggered, dict) and action_triggered.get("action_type"):
                internal_action = ConversationAction(**action_triggered)

            turn = ConversationTurn(
                turn_id=turn_id,
                timestamp=datetime.now(timezone.utc),
                user_query=user_query,
                assistant_response=assistant_response,
                intent=intent,
                dialogue_act=dialogue_act,
                purpose=purpose,
                strategy=strategy,
                canonical_topic=canonical_topic,
                resolved_entities=resolved_entities or {},
                retrieved_evidence_ids=retrieved_evidence_ids or [],
                live_tool_called=live_tool_called,
                action_triggered=internal_action,
                progressive_offer=progressive_offer,
                latency_ms=latency_ms,
            )

            session.history.append(turn)
            if len(session.history) > self.max_history_turns:
                session.history = session.history[-self.max_history_turns :]

            # Update entities
            if resolved_entities:
                session.active_entities.update(resolved_entities)

            # Update progressive disclosure offer
            session.pending_progressive_offer = progressive_offer

            # Infer & update topic if appropriate
            self._update_topic_context(session, user_query, intent, turn_id, canonical_topic)

            # Update Semantic Context Tracking
            self._update_semantic_state(session, user_query, assistant_response, purpose, strategy)

            session.updated_at = datetime.now(timezone.utc)
            return turn

    def _update_semantic_state(
        self,
        session: ConversationSession,
        user_query: str,
        assistant_response: str,
        purpose: Any | None,
        strategy: Any | None,
    ) -> None:
        """Tracks explained facts, used examples, referenced code locations, and compact response summaries."""
        resp_lower = assistant_response.lower()

        # Track facts explained
        if "agentguard is an agentic commerce firewall" in resp_lower or "zero-trust" in resp_lower or "deterministic authorization firewall" in resp_lower:
            if "system_definition" not in session.facts_already_explained:
                session.facts_already_explained.append("system_definition")
        if "operationally" in resp_lower or "inline policy firewall" in resp_lower or "intercepts the claim" in resp_lower:
            if "operational_flow" not in session.facts_already_explained:
                session.facts_already_explained.append("operational_flow")
        if "untrusted client threat model" in resp_lower or "catastrophic financial risk" in resp_lower or "security gap" in resp_lower:
            if "value_proposition" not in session.facts_already_explained:
                session.facts_already_explained.append("value_proposition")
        if "traditional e-commerce flows" in resp_lower or "normal transactions assume" in resp_lower or "payment gateways like razorpay" in resp_lower:
            if "gateway_comparison" not in session.facts_already_explained:
                session.facts_already_explained.append("gateway_comparison")
        if "dual-loop" in resp_lower or "loop 1" in resp_lower or "loop 2" in resp_lower:
            if "dual_loop_architecture" not in session.facts_already_explained:
                session.facts_already_explained.append("dual_loop_architecture")
        if "price_mismatch" in resp_lower or "price tampering" in resp_lower or "claim diff" in resp_lower:
            if "price_tampering_check" not in session.facts_already_explained:
                session.facts_already_explained.append("price_tampering_check")
        if "sha-256" in resp_lower or "audit ledger" in resp_lower or "hash chain" in resp_lower:
            if "cryptographic_audit_ledger" not in session.facts_already_explained:
                session.facts_already_explained.append("cryptographic_audit_ledger")
        if "idempotency" in resp_lower or "replay" in resp_lower:
            if "replay_protection" not in session.facts_already_explained:
                session.facts_already_explained.append("replay_protection")
        if "budget_exceeded" in resp_lower or "shortfall" in resp_lower:
            if "budget_escalation" not in session.facts_already_explained:
                session.facts_already_explained.append("budget_escalation")
        if "zero financial authority" in resp_lower or "zero-trust boundary" in resp_lower:
            if "zero_financial_authority" not in session.facts_already_explained:
                session.facts_already_explained.append("zero_financial_authority")

        # Track code locations shown
        for code_path in [
            "backend/app/policy/engine.py",
            "backend/app/api/propose.py",
            "backend/app/api/execute.py",
            "backend/app/services/audit_log.py",
            "backend/app/api/routes_mandate.py",
        ]:
            if code_path in assistant_response and code_path not in session.code_locations_already_shown:
                session.code_locations_already_shown.append(code_path)

        # Track pages referenced
        for page in ["Cockpit", "Defense", "Threat Lab", "Forensics", "Telemetry"]:
            if page.lower() in resp_lower and page not in session.pages_already_referenced:
                session.pages_already_referenced.append(page)

        # Track examples
        if "earbud" in resp_lower or "earbuds" in resp_lower:
            if "earbuds_budget_shortfall" not in session.examples_already_used:
                session.examples_already_used.append("earbuds_budget_shortfall")
        if "speaker" in resp_lower:
            if "bluetooth_speaker_allow" not in session.examples_already_used:
                session.examples_already_used.append("bluetooth_speaker_allow")

        # Compact summary of the response
        first_sentence = assistant_response.split(".")[0].strip()
        if first_sentence:
            summary = (first_sentence[:120] + "...") if len(first_sentence) > 120 else first_sentence
            session.previous_response_summaries.append(summary)
            if len(session.previous_response_summaries) > 5:
                session.previous_response_summaries = session.previous_response_summaries[-5:]
            session.previous_assistant_claim = summary

        # Update user goal
        if purpose:
            session.current_user_goal = str(purpose)

    def clear_pending_offer(self, session_id: str) -> None:
        """Clears the pending progressive disclosure offer."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.pending_progressive_offer = None

    def reset_session(self, session_id: str) -> bool:
        """Resets the state and history of an existing session."""
        with self._lock:
            if session_id in self._sessions:
                user_id = self._sessions[session_id].user_id
                self._sessions[session_id] = ConversationSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    history=[],
                    active_topic=None,
                    topic_history=[],
                    active_entities={"user_id": user_id, "mandate_id": "mandate-001"},
                    pending_progressive_offer=None,
                    facts_already_explained=[],
                    examples_already_used=[],
                    code_locations_already_shown=[],
                    pages_already_referenced=[],
                    previous_response_summaries=[],
                    offers_already_made=[],
                    current_user_goal=None,
                    previous_assistant_claim=None,
                    conversation_depth=1,
                )
                return True
            return False

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session from active memory."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def _update_topic_context(
        self,
        session: ConversationSession,
        query: str,
        intent: UserIntentCategory,
        turn_id: int,
        canonical_topic: Any | None = None,
    ) -> None:
        from backend.app.conversational.models import CanonicalTopic

        lower = query.lower()

        # 1. Check Topic Reversion ("Actually, go back to price tampering", "back to price tampering")
        if any(w in lower for w in ["go back to", "back to", "return to"]):
            for past_topic in reversed(session.topic_history):
                if (
                    ("price" in past_topic.topic_name.lower() and "price" in lower)
                    or ("replay" in past_topic.topic_name.lower() and "replay" in lower)
                    or ("audit" in past_topic.topic_name.lower() and "audit" in lower)
                    or ("budget" in past_topic.topic_name.lower() and ("budget" in lower or "mandate" in lower))
                ):
                    session.active_topic = past_topic
                    session.active_topic.last_active_turn = turn_id
                    session.active_topic.depth += 1
                    session.conversation_depth = session.active_topic.depth
                    return

        # 2. Use canonical_topic if provided directly
        target_canonical: CanonicalTopic | None = None
        topic_display = None

        if isinstance(canonical_topic, CanonicalTopic):
            target_canonical = canonical_topic
            name_map = {
                CanonicalTopic.PRICE_TAMPERING: "Price Tampering Protection",
                CanonicalTopic.REPLAY_ATTACK: "Replay Attack Protection",
                CanonicalTopic.AUDIT_CHAIN: "Cryptographic Audit Ledger",
                CanonicalTopic.MANDATE_BUDGET: "Mandate Budget Management",
                CanonicalTopic.THREAT_LAB: "Threat Lab Simulation",
                CanonicalTopic.MERCHANT_SCOPE: "Merchant Scope Authorization",
                CanonicalTopic.CLAIM_DIFF: "Claim Diff Validation",
                CanonicalTopic.TRANSACTION_EXECUTION: "Transaction Execution",
                CanonicalTopic.FORENSIC_LEDGER: "Forensic Ledger",
                CanonicalTopic.GENERAL_ARCHITECTURE: "General Architecture",
            }
            topic_display = name_map.get(canonical_topic, "General Architecture")
        elif (
            "audit" in lower
            or "hash" in lower
            or "ledger" in lower
            or ("tamper" in lower and session.active_topic and session.active_topic.canonical_topic == CanonicalTopic.AUDIT_CHAIN)
        ):
            target_canonical = CanonicalTopic.AUDIT_CHAIN
            topic_display = "Cryptographic Audit Ledger"
        elif "price" in lower or ("tamper" in lower and not ("audit" in lower or "ledger" in lower)):
            target_canonical = CanonicalTopic.PRICE_TAMPERING
            topic_display = "Price Tampering Protection"
        elif "replay" in lower:
            target_canonical = CanonicalTopic.REPLAY_ATTACK
            topic_display = "Replay Attack Protection"
        elif "budget" in lower or "mandate" in lower:
            target_canonical = CanonicalTopic.MANDATE_BUDGET
            topic_display = "Mandate Budget Management"
        elif "threat lab" in lower or "threat" in lower:
            target_canonical = CanonicalTopic.THREAT_LAB
            topic_display = "Threat Lab Simulation"
        elif "forensic" in lower:
            target_canonical = CanonicalTopic.FORENSIC_LEDGER
            topic_display = "Forensic Ledger"

        if target_canonical and topic_display:
            if not session.active_topic or session.active_topic.canonical_topic != target_canonical:
                if session.active_topic:
                    session.topic_history.append(session.active_topic)
                session.active_topic = TopicContext(
                    canonical_topic=target_canonical,
                    topic_name=topic_display,
                    parent_topic=session.active_topic.topic_name if session.active_topic else None,
                    depth=1,
                    last_active_turn=turn_id,
                )
                session.conversation_depth = 1
            else:
                session.active_topic.last_active_turn = turn_id
                session.active_topic.depth += 1
                session.conversation_depth = session.active_topic.depth
        elif session.active_topic:
            # Continue current topic depth
            session.active_topic.last_active_turn = turn_id
            session.active_topic.depth += 1
            session.conversation_depth = session.active_topic.depth
