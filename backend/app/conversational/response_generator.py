"""Evidence-Grounded Response Generation Engine for AgentGuard Conversational Brain."""

import logging
import re
from typing import Any

from backend.app.conversational.guardrails import SafetyGuardrails
from backend.app.conversational.llm_provider import BaseConversationalLLM
from backend.app.conversational.models import (
    AssistantResponse,
    BrainTrace,
    ConversationSession,
    ConversationalPurpose,
    DialogueAct,
    EvidenceContext,
    FollowUpSuggestion,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    ResponseStrategy,
    UserIntentCategory,
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Synthesizes evidence-grounded, natural, and non-repetitive assistant responses

    adapted dynamically to the user's communicative purpose and response strategy.
    """

    SYSTEM_INSTRUCTION = (
        "You are the AgentGuard Conversational Brain — an intelligent, authoritative security specialist "
        "who deeply understands the AgentGuard Agentic Commerce Firewall.\n\n"
        "CORE CONVERSATIONAL PRINCIPLES:\n"
        "1. Absolute Grounding: All statements must be 100% grounded in the provided Evidence and Live PostgreSQL state. "
        "Never hallucinate architecture, features, statistics, or capabilities not in evidence.\n"
        "2. Dynamic Adaptability: Match the user's specific conversational purpose. If the user asks for purpose/differentiation, "
        "explain the autonomous-agent trust problem and value proposition instead of repeating the basic definition. "
        "If they ask for code, provide the exact file and function name. If they ask for an example, walk through a concrete scenario.\n"
        "3. Avoid Rigid Templates: Do NOT use a mechanical WHAT/WHY/HOW/WHERE bullet template on every turn. Write like a human "
        "security engineer in direct, natural, and engaging prose.\n"
        "4. Non-Repetition: Do not repeatedly recite identical sentences or structures across consecutive turns.\n"
        "5. AgentGuard Scope: You are strictly an AgentGuard specialist. For off-topic questions (weather, astronomy, recipes, sports), "
        "politely refuse and redirect to AgentGuard's architecture and capabilities.\n"
        "6. Zero Financial Authority: You cannot execute or approve payments. Maintain strict zero-trust neutrality.\n"
        "7. Secret Protection: Never reveal API keys, credentials, or .env tokens.\n"
        "8. Professional, Direct Phrasing: Do not use informal conversational fillers (e.g. 'like', 'um', 'uh', 'you know', 'I mean', 'so'). "
        "For comparisons, use 'such as' or 'as' rather than 'like'."
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

        # 1. Format prompt with evidence, strategy, and conversational state
        user_prompt = self._build_prompt(plan, evidence, session)

        # 2. Call LLM provider
        raw_text = self.llm.generate_response(
            system_instruction=self.SYSTEM_INSTRUCTION,
            user_prompt=user_prompt,
        )

        # 3. Sanitize output for secret protection
        clean_text = self.guardrails.sanitize_output(raw_text)

        # 4. Check for Semantic Repetition against recent responses
        repetition_detected = False
        if session and session.history and len(session.history) > 0:
            is_repeat_request = any(
                w in plan.resolved_query.lower() for w in ["repeat", "say that again", "what did you say"]
            )
            if not is_repeat_request:
                repetition_detected = self._detect_excessive_repetition(clean_text, session)
                if repetition_detected:
                    # Bounded single re-generation attempt with explicit negative guidance
                    retry_prompt = self._build_retry_prompt(plan, evidence, session, clean_text)
                    retry_text = self.llm.generate_response(
                        system_instruction=self.SYSTEM_INSTRUCTION,
                        user_prompt=retry_prompt,
                    )
                    clean_text = self.guardrails.sanitize_output(retry_text)

        # 5. Handle missing live records explicitly
        if evidence.is_live and evidence.live_result and evidence.live_result.data.get("found") is False:
            if "not found" not in clean_text.lower():
                entity_id = evidence.live_result.data.get("id") or evidence.live_result.data.get("product_id") or "requested"
                clean_text = f"The requested record `{entity_id}` was not found in live PostgreSQL database records."

        # 6. Append progressive offer if present
        offer_text = ""
        if offer and offer.prompt_text:
            offer_text = offer.prompt_text
            if offer_text.lower() not in clean_text.lower():
                clean_text = f"{clean_text.rstrip()}\n\n{offer_text}"

        # 7. Extract structured citations
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

        live_readings = (
            evidence.live_result.data
            if (evidence.live_result and evidence.live_result.data is not None)
            else {}
        )

        response = AssistantResponse(
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
            action=plan.suggested_action if plan.suggested_action is not None else {},
        )

        return response

    def _detect_excessive_repetition(self, text: str, session: ConversationSession) -> bool:
        """Calculates 3-gram word set overlap against the last 2 assistant responses in history."""
        if not session.history:
            return False

        current_words = self._tokenize(text)
        if len(current_words) < 8:
            return False

        current_3grams = set(zip(current_words[:-2], current_words[1:-1], current_words[2:]))
        if not current_3grams:
            return False

        for turn in session.history[-2:]:
            prev_words = self._tokenize(turn.assistant_response)
            if len(prev_words) < 8:
                continue
            prev_3grams = set(zip(prev_words[:-2], prev_words[1:-1], prev_words[2:]))
            if not prev_3grams:
                continue

            intersection = current_3grams.intersection(prev_3grams)
            overlap_ratio = len(intersection) / min(len(current_3grams), len(prev_3grams))
            if overlap_ratio > 0.55:
                logger.info(f"Excessive repetition detected (overlap={overlap_ratio:.2f})")
                return True

        return False

    def _tokenize(self, text: str) -> list[str]:
        """Simple alphanumeric tokenizer for n-gram calculation."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return [w for w in cleaned.split() if w]

    def _build_prompt(
        self,
        plan: ResponsePlan,
        evidence: EvidenceContext,
        session: ConversationSession | None,
    ) -> str:
        parts: list[str] = []

        # 1. Strategy and Conversational Goal Instruction
        parts.append(f"### STRATEGY & GOAL: {plan.strategy.value}")
        parts.append(f"Target Purpose: {plan.purpose.value}")
        if plan.canonical_topic:
            parts.append(f"Canonical Topic: {plan.canonical_topic.value}")
        if plan.strategy_rationale:
            parts.append(f"Rationale: {plan.strategy_rationale}")
        if plan.compound_query and plan.sub_intents:
            clauses = [s.get("clause", s.get("topic", "")) for s in plan.sub_intents if s.get("clause") or s.get("topic")]
            if clauses:
                parts.append(
                    f"Compound Multi-Topic Goals: The user coordinated multiple topics in this single turn: {', '.join(clauses)}. "
                    f"You MUST explicitly address each coordinated topic in your synthesized response."
                )

        # 2. Evidence / Live Readings
        if evidence.is_live and evidence.live_result:
            parts.append("\n### AUTHORITATIVE LIVE RUNTIME DATA (PostgreSQL):")
            for note in evidence.summary_notes:
                parts.append(f"- {note}")
        elif evidence.summary_notes:
            parts.append("\n### AUTHORITATIVE KNOWLEDGE EVIDENCE (Hybrid RAG + AST):")
            for note in evidence.summary_notes[:5]:
                parts.append(f"- {note}")

        # 3. Conversational Context & State Tracking
        if session:
            parts.append(f"\nTurn Count: {len(session.history) + 1}")
            if session.facts_already_explained:
                parts.append(f"Facts Already Explained in this conversation: {', '.join(session.facts_already_explained)}")
            if session.previous_response_summaries:
                parts.append("Previous Response Summaries:")
                for summary in session.previous_response_summaries[-3:]:
                    parts.append(f"- {summary}")
            if session.active_topic:
                parts.append(f"Active Topic: {session.active_topic.topic_name} (canonical: {session.active_topic.canonical_topic.value}, depth: {session.conversation_depth})")

        # 4. User Question
        parts.append(f"\nUser Query: {plan.resolved_query}")

        return "\n".join(parts)

    def _build_retry_prompt(
        self,
        plan: ResponsePlan,
        evidence: EvidenceContext,
        session: ConversationSession,
        repetitive_candidate: str,
    ) -> str:
        """Builds an adjusted prompt with explicit negative constraints to break repetitive phrasing."""
        first_line = repetitive_candidate.split(".")[0] if "." in repetitive_candidate else repetitive_candidate[:100]
        base_prompt = self._build_prompt(plan, evidence, session)
        guidance = (
            f"\n\n[REPETITION PREVENTION WARNING]\n"
            f"Your previous draft started with: '{first_line}...'\n"
            f"Preserve the current semantic intent ({plan.purpose.value}) and all grounded facts. "
            f"Do not repeat the previous explanation. Use a different explanatory angle appropriate "
            f"to the user's wording (e.g., simple mental-model checkpoint, non-technical safety layer, or concise elevator pitch). "
            f"Do not introduce unrelated claims or change the user's intent."
        )
        return base_prompt + guidance
