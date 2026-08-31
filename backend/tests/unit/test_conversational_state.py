"""Unit tests for DialogueManager session state, memory sliding window, and topic tracking."""

import pytest

from backend.app.conversational.dialogue_manager import DialogueManager
from backend.app.conversational.models import DialogueAct, ProgressiveDisclosureOffer, UserIntentCategory


@pytest.fixture
def manager():
    return DialogueManager(max_history_turns=5)


def test_session_lifecycle(manager):
    """Verify session creation, retrieval, reset, and deletion."""
    sess = manager.get_or_create_session("sess_alpha")
    assert sess.session_id == "sess_alpha"
    assert len(sess.history) == 0

    manager.record_turn(
        session_id="sess_alpha",
        user_query="Hello",
        assistant_response="Hi! How can I help?",
        intent=UserIntentCategory.GREETING_OR_META,
        dialogue_act=DialogueAct.INFORM,
    )
    assert len(sess.history) == 1

    # Reset session
    reset_ok = manager.reset_session("sess_alpha")
    assert reset_ok is True
    sess_after_reset = manager.get_session("sess_alpha")
    assert len(sess_after_reset.history) == 0

    # Delete session
    del_ok = manager.delete_session("sess_alpha")
    assert del_ok is True
    assert manager.get_session("sess_alpha") is None


def test_history_sliding_window(manager):
    """Verify history respects max_history_turns sliding window."""
    for i in range(10):
        manager.record_turn(
            session_id="sess_window",
            user_query=f"Query {i}",
            assistant_response=f"Answer {i}",
            intent=UserIntentCategory.CONCEPT_EXPLANATION,
            dialogue_act=DialogueAct.INFORM,
        )

    sess = manager.get_session("sess_window")
    assert len(sess.history) == 5
    assert sess.history[-1].user_query == "Query 9"
    assert sess.history[0].user_query == "Query 5"


def test_topic_context_evolution(manager):
    """Verify topic evolution across turns."""
    manager.record_turn(
        session_id="sess_topic",
        user_query="How does price tampering protection work?",
        assistant_response="Price tampering check...",
        intent=UserIntentCategory.SECURITY_SCENARIO,
        dialogue_act=DialogueAct.INFORM,
    )
    sess = manager.get_session("sess_topic")
    assert sess.active_topic is not None
    assert sess.active_topic.topic_name == "Price Tampering Protection"

    # Switch to Audit
    manager.record_turn(
        session_id="sess_topic",
        user_query="Tell me about the cryptographic audit ledger.",
        assistant_response="The audit ledger...",
        intent=UserIntentCategory.CONCEPT_EXPLANATION,
        dialogue_act=DialogueAct.INFORM,
    )
    assert sess.active_topic.topic_name == "Cryptographic Audit Ledger"
    assert len(sess.topic_history) == 1
    assert sess.topic_history[0].topic_name == "Price Tampering Protection"
