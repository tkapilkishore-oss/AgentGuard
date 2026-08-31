"""Unit tests for Conversational Brain Pydantic v2 data models and contracts."""

import pytest
from pydantic import ValidationError

from backend.app.conversational.models import (
    AssistantResponse,
    BrainTrace,
    ConversationAction,
    ConversationSession,
    ConversationTurn,
    DialogueAct,
    EvidenceContext,
    FollowUpSuggestion,
    LiveToolRequest,
    LiveToolResult,
    LiveToolType,
    ProgressiveDisclosureOffer,
    ResponsePlan,
    TopicContext,
    UserIntentCategory,
)


def test_intent_category_enum_values():
    """Verify intent categories are comprehensive and match taxonomy."""
    assert UserIntentCategory.CONCEPT_EXPLANATION.value == "CONCEPT_EXPLANATION"
    assert UserIntentCategory.SECURITY_SCENARIO.value == "SECURITY_SCENARIO"
    assert UserIntentCategory.CODE_REFERENCE.value == "CODE_REFERENCE"
    assert UserIntentCategory.FRONTEND_NAVIGATION.value == "FRONTEND_NAVIGATION"
    assert UserIntentCategory.LIVE_DATA_QUERY.value == "LIVE_DATA_QUERY"
    assert UserIntentCategory.ADVERSARIAL_INJECTION.value == "ADVERSARIAL_INJECTION"


def test_conversation_turn_model_instantiation():
    """Verify ConversationTurn model fields and serialization."""
    turn = ConversationTurn(
        turn_id=1,
        user_query="What is AgentGuard?",
        assistant_response="AgentGuard is an Agentic Commerce Firewall...",
        intent=UserIntentCategory.CONCEPT_EXPLANATION,
        dialogue_act=DialogueAct.INFORM,
        resolved_entities={"mandate_id": "mandate-001"},
        retrieved_evidence_ids=["unit-001", "unit-002"],
        latency_ms=12.5,
    )
    assert turn.turn_id == 1
    assert turn.user_query == "What is AgentGuard?"
    data = turn.model_dump()
    assert data["intent"] == "CONCEPT_EXPLANATION"
    assert data["dialogue_act"] == "INFORM"


def test_live_tool_request_and_result_contracts():
    """Verify live tool request/result models."""
    req = LiveToolRequest(
        tool_type=LiveToolType.MANDATE_BUDGET,
        parameters={"mandate_id": "mandate-001"},
        reason="User requested current budget balance",
    )
    assert req.tool_type == LiveToolType.MANDATE_BUDGET

    res = LiveToolResult(
        tool_type=LiveToolType.MANDATE_BUDGET,
        success=True,
        data={"budget_remaining": "3000.00"},
        execution_latency_ms=1.5,
    )
    assert res.success is True
    assert res.data["budget_remaining"] == "3000.00"


def test_assistant_response_contract_serialization():
    """Verify AssistantResponse envelope with trace and followups."""
    resp = AssistantResponse(
        session_id="sess_123",
        turn_id=1,
        message="Valid response text",
        intent=UserIntentCategory.SECURITY_SCENARIO,
        dialogue_act=DialogueAct.INFORM,
        evidence_citations=[{"unit_id": "u1", "authority": "AUTHORITATIVE"}],
        live_data_used=False,
        suggested_followups=[
            FollowUpSuggestion(
                label="View Code",
                query="Where is this implemented?",
                intent_target=UserIntentCategory.CODE_REFERENCE,
                rationale="Inspect codebase.",
            )
        ],
        action=ConversationAction(action_type="NAVIGATE_TAB", ui_tab_target="DEFENSE"),
        trace=BrainTrace(
            session_id="sess_123",
            turn_id=1,
            raw_query="How does price tampering work?",
            resolved_query="How does price tampering work?",
            intent=UserIntentCategory.SECURITY_SCENARIO,
            is_dynamic_live=False,
            safety_verdict="SAFE",
            latency_total_ms=45.2,
        ),
    )
    dumped = resp.model_dump()
    assert dumped["session_id"] == "sess_123"
    assert dumped["action"]["ui_tab_target"] == "DEFENSE"
    assert len(dumped["suggested_followups"]) == 1
