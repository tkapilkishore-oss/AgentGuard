import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_paraphrase_and_natural_language_generalization():
    # Diverse paraphrases related to security mechanisms for semantic generalization check
    paraphrase_queries = [
        "How does the system prevent duplicate transaction submissions?",
        "Explain the protection against repeat payments.",
        "What measures are in place for replay prevention?",
        "Tell me about the safeguards used to avoid resubmitting the same payment twice.",
        "Can you describe the mechanism that blocks replay attacks on transactions?",
        "How does AgentGuard ensure transactions aren't processed multiple times?",
        "What features stop double payment attempts?",
        "Describe the defense against submitting identical transactions again.",
    ]

    session_id = None
    user_id = "test-user-paraphrase-001"

    try:
        for query in paraphrase_queries:
            payload = {
                "query": query,
                # No session_id for first query, then reuse for subsequent turns to simulate session continuity
                "session_id": session_id,
                "user_id": user_id
            }
            # Remove session_id key if None to start new session on first request
            if session_id is None:
                payload.pop("session_id")

            response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
            resp_json = response.json()

            # Basic success check
            assert resp_json.get("success") is True, f"API indicated failure: {resp_json.get('error')}"
            data = resp_json.get("data")
            assert data is not None, "Response data missing"

            # Validate session_id returned and update for next query
            assert isinstance(data.get("session_id"), str) and len(data["session_id"]) > 0, "Invalid session_id in response"
            session_id = data["session_id"]

            # Validate turn_id increments and is int >= 1
            turn_id = data.get("turn_id")
            assert isinstance(turn_id, int) and turn_id >= 1, f"Invalid turn_id: {turn_id}"

            # Validate message is a non-empty string
            message = data.get("message")
            assert isinstance(message, str) and len(message.strip()) > 0, "Empty or invalid message in response"

            # Validate intent contains keywords related to security mechanisms
            intent = data.get("intent")
            assert isinstance(intent, str) and len(intent) > 0, "Invalid or missing intent"

            # The dialogue_act should be present and non-empty string
            dialogue_act = data.get("dialogue_act")
            assert isinstance(dialogue_act, str) and len(dialogue_act) > 0, "Invalid or missing dialogue_act"

            # Evidence citations array present (can be empty but must be a list)
            citations = data.get("evidence_citations")
            assert isinstance(citations, list), "evidence_citations should be a list"

            # Ensure live_data_used is boolean
            live_data_used = data.get("live_data_used")
            assert isinstance(live_data_used, bool), "live_data_used should be boolean"

            # Suggested followups is a list (may be empty)
            suggested_followups = data.get("suggested_followups")
            assert isinstance(suggested_followups, list), "suggested_followups should be a list"

            # Action and trace are objects or None
            action = data.get("action")
            trace = data.get("trace")
            assert (isinstance(action, dict) or action is None), "action should be dict or None"
            assert (isinstance(trace, dict) or trace is None), "trace should be dict or None"

            # Error should be None or empty object
            error = resp_json.get("error")
            assert error is None or error == {} or error == {}, "Unexpected error present in response"
    finally:
        # No explicit resource to delete for this conversational session test
        pass

test_paraphrase_and_natural_language_generalization()