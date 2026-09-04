"""Master Conversational Brain Orchestrator for AgentGuard."""

import time
from typing import Any

from sqlalchemy.orm import Session

from backend.app.conversational.dialogue_manager import DialogueManager
from backend.app.conversational.disclosure import ProgressiveDisclosureEngine
from backend.app.conversational.guardrails import SafetyGuardrails
from backend.app.conversational.intent_resolver import IntentResolver
from backend.app.conversational.live_bridge import LiveRuntimeBridge
from backend.app.conversational.llm_provider import BaseConversationalLLM, GeminiConversationalLLM
from backend.app.conversational.models import (
    AssistantResponse,
    BrainTrace,
    ConversationSession,
    EvidenceContext,
    UserIntentCategory,
)
from backend.app.conversational.response_generator import ResponseGenerator
from backend.app.conversational.retrieval_bridge import RetrievalBridge
from backend.app.db.session import SessionLocal


class ConversationalBrain:
    """Master orchestrator for the AgentGuard conversational intelligence system."""

    def __init__(
        self,
        dialogue_manager: DialogueManager | None = None,
        intent_resolver: IntentResolver | None = None,
        retrieval_bridge: RetrievalBridge | None = None,
        live_bridge: LiveRuntimeBridge | None = None,
        disclosure_engine: ProgressiveDisclosureEngine | None = None,
        guardrails: SafetyGuardrails | None = None,
        llm_provider: BaseConversationalLLM | None = None,
    ) -> None:
        self.dialogue_manager = dialogue_manager or DialogueManager()
        self.intent_resolver = intent_resolver or IntentResolver()
        self.retrieval_bridge = retrieval_bridge or RetrievalBridge()
        self.live_bridge = live_bridge or LiveRuntimeBridge()
        self.disclosure_engine = disclosure_engine or ProgressiveDisclosureEngine()
        self.guardrails = guardrails or SafetyGuardrails()
        self.llm = llm_provider or GeminiConversationalLLM()
        self.response_generator = ResponseGenerator(self.llm, self.guardrails)

    def process_query(
        self,
        query: str,
        session_id: str | None = None,
        user_id: str = "user-001",
        db: Session | None = None,
    ) -> AssistantResponse:
        """End-to-end processing of a user conversational turn."""
        start_time = time.perf_counter()
        t_retrieval = 0.0
        t_live = 0.0
        t_llm = 0.0

        # 1. Retrieve or initialize session state
        session = self.dialogue_manager.get_or_create_session(session_id, user_id)
        current_session_id = session.session_id
        turn_id = len(session.history) + 1

        # 2. Safety Guardrails Validation
        is_safe, violation_code = self.guardrails.validate_request(query)
        if not is_safe:
            refusal_response = self.guardrails.generate_adversarial_refusal(
                current_session_id, turn_id, violation_code, query=query
            )
            self.dialogue_manager.record_turn(
                session_id=current_session_id,
                user_query=query,
                assistant_response=refusal_response.message,
                intent=UserIntentCategory.ADVERSARIAL_INJECTION,
                dialogue_act=refusal_response.dialogue_act,
                latency_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
            )
            return refusal_response

        # 3. Intent Understanding & Contextual Resolution
        plan = self.intent_resolver.resolve(query, session)

        # Handle adversarial detected during intent resolution
        if plan.is_adversarial:
            refusal_response = self.guardrails.generate_adversarial_refusal(
                current_session_id, turn_id, "DIRECT_AUTHORIZATION_ATTEMPT", query=query
            )
            self.dialogue_manager.record_turn(
                session_id=current_session_id,
                user_query=query,
                assistant_response=refusal_response.message,
                intent=UserIntentCategory.ADVERSARIAL_INJECTION,
                dialogue_act=refusal_response.dialogue_act,
                latency_ms=round((time.perf_counter() - start_time) * 1000.0, 2),
            )
            return refusal_response

        # 4. Routing & Evidence Gathering (Static vs Live)
        evidence: EvidenceContext
        live_tool_type_used = None

        if plan.needs_live_tool and plan.live_tool_request:
            t0 = time.perf_counter()
            live_res = self.live_bridge.execute_live_tool(plan.live_tool_request, db=db)
            if plan.compound_query and live_res.success:
                lower_q = plan.resolved_query.lower()
                local_db = db or SessionLocal()
                try:
                    if "budget" in lower_q or "mandate" in lower_q:
                        mand_data = self.live_bridge._query_mandate_budget(plan.live_tool_request.parameters, db=local_db)
                        live_res.data.update(mand_data)
                    if "price" in lower_q or "product" in lower_q or "catalog" in lower_q:
                        cat_data = self.live_bridge._query_product_catalog(plan.live_tool_request.parameters, db=local_db)
                        live_res.data.update(cat_data)
                    if "merchant" in lower_q:
                        merch_data = self.live_bridge._query_merchant_catalog(plan.live_tool_request.parameters, db=local_db)
                        live_res.data.update(merch_data)
                    if "transaction" in lower_q or "ledger" in lower_q:
                        txn_data = self.live_bridge._query_transaction_status(plan.live_tool_request.parameters, db=local_db)
                        live_res.data.update(txn_data)
                    if "audit" in lower_q or "chain" in lower_q or "trail" in lower_q:
                        audit_data = self.live_bridge._verify_live_audit_chain(plan.live_tool_request.parameters, db=local_db)
                        live_res.data.update(audit_data)
                finally:
                    if db is None:
                        local_db.close()
            t_live = (time.perf_counter() - t0) * 1000.0
            evidence = self.live_bridge.create_evidence_context(live_res)
            live_tool_type_used = plan.live_tool_request.tool_type
            if plan.needs_static_retrieval:
                t0_stat = time.perf_counter()
                static_ev = self.retrieval_bridge.retrieve_evidence(plan.resolved_query)
                t_retrieval = (time.perf_counter() - t0_stat) * 1000.0
                if static_ev and static_ev.static_evidence:
                    evidence.static_evidence = static_ev.static_evidence
                    evidence.provenance_unit_ids.extend(static_ev.provenance_unit_ids)
                    evidence.authorities.extend(static_ev.authorities)
        elif plan.needs_static_retrieval:
            t0 = time.perf_counter()
            evidence = self.retrieval_bridge.retrieve_evidence(plan.resolved_query)
            t_retrieval = (time.perf_counter() - t0) * 1000.0
        else:
            evidence = EvidenceContext()

        # 5. Progressive Disclosure & Follow-up Suggestions
        offer, suggestions = self.disclosure_engine.evaluate_disclosure(plan, session)

        # 6. Evidence-Grounded Response Synthesis
        t0 = time.perf_counter()
        response = self.response_generator.generate(
            plan=plan,
            evidence=evidence,
            session=session,
            offer=offer,
            suggestions=suggestions,
        )
        t_llm = (time.perf_counter() - t0) * 1000.0

        total_latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # 7. Build Observability Trace
        trace = BrainTrace(
            session_id=current_session_id,
            turn_id=turn_id,
            raw_query=query,
            resolved_query=plan.resolved_query,
            intent=plan.intent,
            purpose=plan.purpose.value if plan.purpose else None,
            strategy=plan.strategy.value if plan.strategy else None,
            canonical_topic=plan.canonical_topic.value if plan.canonical_topic else None,
            is_dynamic_live=evidence.is_live,
            live_tool_type=live_tool_type_used,
            retrieved_unit_ids=evidence.provenance_unit_ids,
            top_authority=evidence.authorities[0] if evidence.authorities else None,
            safety_verdict="SAFE",
            progressive_action=offer.offer_type if offer else None,
            llm_provider=self.llm.__class__.__name__,
            latency_total_ms=total_latency_ms,
            latency_retrieval_ms=round(t_retrieval, 2),
            latency_live_ms=round(t_live, 2),
            latency_llm_ms=round(t_llm, 2),
        )
        response.trace = trace

        # 8. Record Turn in Dialogue Memory
        self.dialogue_manager.record_turn(
            session_id=current_session_id,
            user_query=query,
            assistant_response=response.message,
            intent=response.intent,
            dialogue_act=response.dialogue_act,
            purpose=plan.purpose,
            strategy=plan.strategy,
            canonical_topic=plan.canonical_topic,
            resolved_entities={"mandate_id": "mandate-001"},
            retrieved_evidence_ids=evidence.provenance_unit_ids,
            live_tool_called=live_tool_type_used,
            action_triggered=response.action,
            progressive_offer=offer,
            latency_ms=total_latency_ms,
        )

        return response


# Singleton Instance
_BRAIN_INSTANCE: ConversationalBrain | None = None


def get_conversational_brain(
    llm_provider: BaseConversationalLLM | None = None,
) -> ConversationalBrain:
    """Returns the cached singleton ConversationalBrain instance."""
    global _BRAIN_INSTANCE
    if _BRAIN_INSTANCE is None:
        _BRAIN_INSTANCE = ConversationalBrain(llm_provider=llm_provider)
    return _BRAIN_INSTANCE
