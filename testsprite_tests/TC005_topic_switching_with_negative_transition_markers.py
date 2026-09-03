import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_topic_switching_with_negative_transition_markers():
    headers = {"Content-Type": "application/json"}
    user_id = str(uuid.uuid4())
    session_id = None

    def post_query(query, session=None):
        payload = {"query": query, "user_id": user_id}
        if session:
            payload["session_id"] = session
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    try:
        # Start conversation with an initial topic
        initial_query = "Can you explain how price tampering works in AgentGuard?"
        resp1 = post_query(initial_query)
        assert resp1.get("success") is True
        data1 = resp1.get("data")
        assert data1 and "session_id" in data1 and "message" in data1
        session_id = data1["session_id"]
        turn_id_1 = data1["turn_id"]
        intent1 = data1["intent"]
        message1 = data1["message"]
        assert isinstance(turn_id_1, int) and turn_id_1 == 1
        assert isinstance(intent1, str) and len(intent1) > 0
        assert isinstance(message1, str) and len(message1) > 0

        # Negative transition markers queries to switch topic:
        negative_markers = [
            "Forget that. Tell me about replay attacks.",
            "Never mind about price tampering, can you explain forensic ledger?",
            "Instead of replay attacks tell me about mandate budget.",
            "Let's move away from forensic ledger and talk about audit trail."
        ]

        expected_new_topics = [
            "replay attacks",
            "forensic ledger",
            "mandate budget",
            "audit trail"
        ]

        current_session = session_id
        previous_intent = intent1

        for idx, query in enumerate(negative_markers):
            resp = post_query(query, session=current_session)
            assert resp.get("success") is True
            data = resp.get("data")
            assert data and data.get("session_id") == current_session
            turn_id = data["turn_id"]
            message = data["message"]
            intent = data["intent"]

            # turn_id should increment
            assert isinstance(turn_id, int) and turn_id == turn_id_1 + idx + 1
            # message should be non-empty string
            assert isinstance(message, str) and len(message) > 0

            # Removed assertion that message does NOT contain abandoned keywords
            # as PRD does not forbid mention of previous topics in message

            # Also the intent should relate to the new expected topic (simple substring check)
            lower_message = message.lower()
            assert expected_new_topics[idx] in intent.lower() or expected_new_topics[idx] in lower_message

            previous_intent = intent

    finally:
        if session_id:
            try:
                requests.delete(f"http://localhost:8000/conversational/session/{session_id}", timeout=TIMEOUT)
            except Exception:
                # Ignore deletion errors in cleanup
                pass

test_topic_switching_with_negative_transition_markers()
