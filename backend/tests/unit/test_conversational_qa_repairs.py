"""Focused QA regression test suite verifying all 8 repaired conversational defects in AgentGuard."""

import pytest
from sqlalchemy.orm import Session

from backend.app.conversational.models import (
    ConversationalPurpose,
    DialogueAct,
    LiveToolType,
    UserIntentCategory,
)
from backend.app.conversational.orchestrator import ConversationalBrain
from backend.app.db.session import SessionLocal


@pytest.fixture
def brain() -> ConversationalBrain:
    return ConversationalBrain()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_issue_1_project_walkthrough_judge_demo(brain: ConversationalBrain, db: Session):
    """Issue #1: Project walkthrough queries return structured 2-min breakdown with navigation."""
    queries = [
        "Give me a 2-minute project walkthrough for a hackathon judge.",
        "Can you give me a project walkthrough of what you've built?",
        "Explain the whole AgentGuard system for a judge evaluating the project.",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_walkthrough", db=db)
        assert resp.intent == UserIntentCategory.PROJECT_WALKTHROUGH
        assert resp.dialogue_act == DialogueAct.INFORM
        msg = resp.message
        # Verify 5 structured sections
        assert "What is AgentGuard" in msg or "Agentic Commerce Firewall" in msg
        assert "Problem" in msg or "untrusted client" in msg
        assert "Dual-Loop" in msg or "Loop 1" in msg
        assert "Claim Diff" in msg or "Replay" in msg
        assert "Recommended UI Demo Path" in msg or "Cockpit" in msg
        # Verify suggested action navigates to Cockpit
        assert resp.action is not None
        action_type = resp.action.action_type if hasattr(resp.action, "action_type") else resp.action.get("action_type")
        ui_tab = resp.action.ui_tab_target if hasattr(resp.action, "ui_tab_target") else resp.action.get("ui_tab_target")
        assert action_type == "NAVIGATE_TAB"
        assert ui_tab == "COCKPIT"


def test_issue_2_live_product_catalog_query(brain: ConversationalBrain, db: Session):
    """Issue #2: Live product queries query PostgreSQL catalog and return active items."""
    queries = [
        "What products are currently available?",
        "What products are available and what are their prices?",
        "Show available products",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_products", db=db)
        assert resp.intent == UserIntentCategory.LIVE_DATA_QUERY
        assert resp.live_data_used is True
        msg = resp.message
        assert "Wireless Earbuds" in msg
        assert "Bluetooth Speaker" in msg
        assert "Studio Headphones" in msg
        assert "3,499" in msg or "3499" in msg
        assert "2,799" in msg or "2799" in msg
        assert "5,999" in msg or "5999" in msg


def test_issue_3_live_merchant_catalog_query(brain: ConversationalBrain, db: Session):
    """Issue #3: Live merchant queries query PostgreSQL merchants and return active registered merchants."""
    queries = [
        "What merchants are currently active?",
        "Show active merchants",
        "Which merchants are currently active?",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_merchants", db=db)
        assert resp.intent == UserIntentCategory.LIVE_DATA_QUERY
        assert resp.live_data_used is True
        msg = resp.message
        assert "AudioHub" in msg
        assert "merchant-001" in msg
        assert "ShadyGoods" in msg or "active" in msg


def test_issue_4_recent_transactions_query(brain: ConversationalBrain, db: Session):
    """Issue #4: Recent transaction history queries query PostgreSQL transaction ledger and approvals."""
    queries = [
        "Show me what happened in the recent transactions.",
        "What happened in the recent transactions?",
        "Show recent transactions",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_txns", db=db)
        assert resp.intent == UserIntentCategory.LIVE_DATA_QUERY
        assert resp.live_data_used is True
        msg = resp.message
        assert "recorded transactions" in msg.lower() or "transaction ledger" in msg.lower()
        assert "Bluetooth Speaker" in msg or "Earbuds" in msg
        assert "SUCCESS" in msg or "DENIED" in msg


def test_issue_5_compound_multi_intent_completeness(brain: ConversationalBrain, db: Session):
    """Issue #5: Compound queries answer all requested facets (price verification + merchant scope + replay protection)."""
    q = "Explain price verification and merchant scope authorization and replay protection in AgentGuard."
    resp = brain.process_query(q, session_id="test_qa_compound", db=db)
    msg = resp.message
    # Check that price, merchant, and replay are all discussed
    assert "Price" in msg or "Claim Diff" in msg
    assert "Merchant" in msg or "merchant" in msg
    assert "Replay" in msg or "idempotency" in msg or "REPLAY_DETECTED" in msg


def test_issue_6_manual_approval_context(brain: ConversationalBrain, db: Session):
    """Issue #6: Manual approval context resolves and explains human-in-the-loop workflow."""
    sess_id = "test_qa_manual_approval"
    # Turn 1: Price mismatch context
    r1 = brain.process_query("What happens if the agent claims the earbuds cost ₹1,999?", session_id=sess_id, db=db)
    assert "PRICE_MISMATCH" in r1.message or "DENY" in r1.message

    # Turn 2: Manual approval follow-up
    r2 = brain.process_query("And what if I approve it manually?", session_id=sess_id, db=db)
    assert r2.intent != UserIntentCategory.ADVERSARIAL_INJECTION
    msg = r2.message
    assert "human" in msg.lower() or "supervisor" in msg.lower() or "approval" in msg.lower()
    assert "ESCALATE" in msg or "escalat" in msg.lower()
    assert "Loop 2" in msg or "Cockpit" in msg or "mandate" in msg.lower() or "DENY" in msg


def test_issue_7_destructive_audit_guardrail_refusal(brain: ConversationalBrain, db: Session):
    """Issue #7: Destructive audit history deletion attempts are refused explaining SHA-256 immutability."""
    queries = [
        "Delete the audit history.",
        "Clear all transaction logs from the forensic ledger.",
        "Wipe the audit chain records.",
        "Purge the forensic ledger.",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_destructive", db=db)
        assert resp.intent == UserIntentCategory.ADVERSARIAL_INJECTION
        assert resp.dialogue_act == DialogueAct.REFUSE_ADVERSARIAL
        msg = resp.message
        assert "immutable" in msg.lower() or "append-only" in msg.lower()
        assert "SHA-256" in msg or "sha-256" in msg.lower()
        assert "denied" in msg.lower() or "cannot" in msg.lower()


def test_issue_8_repeat_payment_paraphrases(brain: ConversationalBrain, db: Session):
    """Issue #8: Repeat payment / duplicate transaction paraphrases map to replay attack prevention."""
    queries = [
        "How do you prevent a repeat payment?",
        "What happens if there's a duplicate transaction?",
        "Tell me about repeat payment protection.",
    ]

    for q in queries:
        resp = brain.process_query(q, session_id="test_qa_replay_paraphrases", db=db)
        assert resp.intent in (UserIntentCategory.SECURITY_SCENARIO, UserIntentCategory.CONCEPT_EXPLANATION, UserIntentCategory.CODE_REFERENCE)
        msg = resp.message
        assert "replay" in msg.lower() or "idempotency" in msg.lower() or "duplicate" in msg.lower()
        assert "execute.py" in msg or "REPLAY_DETECTED" in msg or "Razorpay" in msg or "double" in msg.lower()
