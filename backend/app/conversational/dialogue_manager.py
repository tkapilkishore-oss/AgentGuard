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
        resolved_entities: dict[str, str] | None = None,
        retrieved_evidence_ids: list[str] | None = None,
        live_tool_called: LiveToolType | None = None,
        action_triggered: ConversationAction | None = None,
        progressive_offer: ProgressiveDisclosureOffer | None = None,
        latency_ms: float = 0.0,
    ) -> ConversationTurn:
        """Appends a turn to the session history, updates entity/topic state, and advances turn counter."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session = self.get_or_create_session(session_id)

            turn_id = len(session.history) + 1
            turn = ConversationTurn(
                turn_id=turn_id,
                timestamp=datetime.now(timezone.utc),
                user_query=user_query,
                assistant_response=assistant_response,
                intent=intent,
                dialogue_act=dialogue_act,
                resolved_entities=resolved_entities or {},
                retrieved_evidence_ids=retrieved_evidence_ids or [],
                live_tool_called=live_tool_called,
                action_triggered=action_triggered,
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
            self._update_topic_context(session, user_query, intent, turn_id)

            session.updated_at = datetime.now(timezone.utc)
            return turn

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
    ) -> None:
        lower = query.lower()
        new_topic_name = None

        if (
            "audit" in lower
            or "hash" in lower
            or "ledger" in lower
            or ("tamper" in lower and session.active_topic and "Audit" in session.active_topic.topic_name)
        ):
            new_topic_name = "Cryptographic Audit Ledger"
        elif "price" in lower or ("tamper" in lower and not ("audit" in lower or "ledger" in lower)):
            new_topic_name = "Price Tampering Protection"
        elif "replay" in lower:
            new_topic_name = "Replay Attack Protection"
        elif "budget" in lower or "mandate" in lower:
            new_topic_name = "Mandate Budget Management"
        elif "threat lab" in lower or "threat" in lower or "scenario" in lower:
            new_topic_name = "Threat Lab Simulation"
        elif "gemini" in lower or "agent" in lower:
            new_topic_name = "Shopping Agent Integration"
        elif "razorpay" in lower or "payment" in lower:
            new_topic_name = "Payment Gateway Execution"

        if new_topic_name:
            if not session.active_topic or session.active_topic.topic_name != new_topic_name:
                if session.active_topic:
                    session.topic_history.append(session.active_topic)
                session.active_topic = TopicContext(
                    topic_name=new_topic_name,
                    parent_topic=session.active_topic.topic_name if session.active_topic else None,
                    depth=1 if not session.active_topic else session.active_topic.depth + 1,
                    last_active_turn=turn_id,
                )
            else:
                session.active_topic.last_active_turn = turn_id
