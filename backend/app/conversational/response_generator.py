"""Evidence-Grounded Response Generation Engine for AgentGuard Conversational Brain."""

import logging
from typing import Any

from backend.app.conversational.guardrails import SafetyGuardrails
from backend.app.conversational.llm_provider import BaseConversationalLLM
from backend.app.conversational.models import (
    AssistantResponse,
    BrainTrace,
    ConversationSession,
    EvidenceContext,
    FollowUpSuggestion,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    UserIntentCategory,
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Synthesizes evidence-grounded, natural, and concise assistant responses

    following WHAT -> WHY -> HOW -> WHERE principles with explicit provenance tracking.
    """

    SYSTEM_INSTRUCTION = (
        "You are the AgentGuard Conversational Brain — an intelligent security and product expert "
        "who deeply understands the AgentGuard Agentic Commerce Firewall.\n\n"
        "CORE PRINCIPLES:\n"
        "1. Grounding: Answer strictly using the provided Evidence and Live Runtime readings. "
        "Do NOT hallucinate or assume facts not in evidence.\n"
        "2. Technical Clarity: For technical/architectural questions, explain concisely: WHAT it is, "
        "WHY it is designed that way, HOW the firewall enforces it, and WHERE in the code it is implemented.\n"
        "3. Zero Financial Authority: You have ZERO authority to approve, reject, or execute transactions. "
        "Explain rules and live status neutrally.\n"
        "4. Conciseness: Keep responses direct and punchy by default. Do not dump unnecessary code unless asked.\n"
        "5. Safety: Never reveal secrets, API keys, or .env tokens."
    )

    def __init__(
        self,
        llm: BaseConversationalLLM,
        guardrails: SafetyGuardrails | None = None,
    ) -> None:
        self.llm = llm
        self.guardrails = guardrails or SafetyGuardrails()

    def generate(
        self,
        plan: ResponsePlan,
        evidence: EvidenceContext,
        session: ConversationSession | None,
        offer: ProgressiveDisclosureOffer | None = None,
        suggestions: list[FollowUpSuggestion] | None = None,
    ) -> AssistantResponse:
        """Generates grounded response and wraps it in a complete AssistantResponse contract."""
        session_id = session.session_id if session else "sess_anon"
        turn_id = (len(session.history) + 1) if session else 1

        # Format prompt with evidence and context
        user_prompt = self._build_prompt(plan, evidence, session)

        # Call LLM provider
        raw_text = self.llm.generate_response(
            system_instruction=self.SYSTEM_INSTRUCTION,
            user_prompt=user_prompt,
        )

        # Sanitize output for secret protection
        clean_text = self.guardrails.sanitize_output(raw_text)

        # Handle missing live records explicitly
        if evidence.is_live and evidence.live_result and evidence.live_result.data.get("found") is False:
            if "not found" not in clean_text.lower():
                entity_id = evidence.live_result.data.get("id") or evidence.live_result.data.get("product_id") or "requested"
                clean_text = f"The requested record `{entity_id}` was not found in live PostgreSQL database records."

        # Append progressive offer if present
        offer_text = None
        if offer and offer.prompt_text:
            offer_text = offer.prompt_text
            # Append cleanly to response if not already present
            if offer_text.lower() not in clean_text.lower():
                clean_text = f"{clean_text.rstrip()}\n\n{offer_text}"

        # Extract structured citations
        citations: list[dict[str, Any]] = []
        if evidence.static_evidence:
            for r in evidence.static_evidence.all_results[:3]:
                citations.append(
                    {
                        "unit_id": r.knowledge_unit_id,
                        "title": r.title,
                        "source_path": r.source_path,
                        "line_start": r.line_start,
                        "line_end": r.line_end,
                        "authority": r.authority.value,
                        "source_tier": r.source_tier.value,
                    }
                )

        live_readings = evidence.live_result.data if evidence.live_result else None

        return AssistantResponse(
            session_id=session_id,
            turn_id=turn_id,
            message=clean_text,
            intent=plan.intent,
            dialogue_act=plan.dialogue_act,
            evidence_citations=citations,
            live_data_used=evidence.is_live,
            live_readings=live_readings,
            progressive_disclosure_offer=offer_text,
            suggested_followups=suggestions or [],
            action=plan.suggested_action,
        )

    def _build_prompt(
        self,
        plan: ResponsePlan,
        evidence: EvidenceContext,
        session: ConversationSession | None,
    ) -> str:
        parts: list[str] = []

        # 1. Evidence / Live Readings
        if evidence.is_live and evidence.live_result:
            parts.append("### AUTHORITATIVE LIVE RUNTIME DATA (PostgreSQL):")
            for note in evidence.summary_notes:
                parts.append(f"- {note}")
        elif evidence.summary_notes:
            parts.append("### AUTHORITATIVE KNOWLEDGE EVIDENCE (Hybrid RAG + AST):")
            for note in evidence.summary_notes[:5]:
                parts.append(f"- {note}")

        # 2. Conversation History Context (last 3 turns)
        if session and session.history:
            parts.append("\n### RECENT CONVERSATION HISTORY:")
            for t in session.history[-3:]:
                parts.append(f"User: {t.user_query}")
                parts.append(f"Assistant: {t.assistant_response[:150]}...")

        # 3. Active Topic & Intent
        if session and session.active_topic:
            parts.append(f"\nActive Topic: {session.active_topic.topic_name}")
        parts.append(f"Detected Intent: {plan.intent.value}")

        # 4. User Question
        parts.append(f"\nUser Query: {plan.resolved_query}")

        return "\n".join(parts)
