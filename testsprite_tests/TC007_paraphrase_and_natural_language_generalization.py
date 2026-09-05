import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_paraphrase_and_natural_language_generalization():
    paraphrase_queries = [
        "How does the system prevent submitting the same transaction twice?",
        "Can you explain repeat payment protection?",
        "What mechanism stops replay attacks in the payment system?",
        "Tell me about duplicate transaction submission safeguards.",
        "How is replay prevention enforced?",
        "Describe how the system handles repeated payment requests.",
        "What stops identical payments from being processed multiple times?",
        "Explain security that protects against resubmitting a payment.",
        "How does AgentGuard detect duplicate submission of transactions?",
        "What methods are in place to block replayed requests in payments?"
    ]

    session_id = None
    user_id = "test-user-tc007"

    try:
        # Create a new session by sending first query without session_id
        first_payload = {
            "query": paraphrase_queries[0],
            "user_id": user_id
        }
        resp = requests.post(BASE_URL, json=first_payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected status 200, got {resp.status_code}"
        json_resp = resp.json()
        assert json_resp.get("success") is True, "Response success flag is not True"
        data = json_resp.get("data", {})
        session_id = data.get("session_id")
        assert session_id is not None and isinstance(session_id, str) and len(session_id) > 0, "No valid session_id returned"
        assert isinstance(data.get("turn_id"), int) and data["turn_id"] == 1, "Turn ID should be 1 on first query"
        assert isinstance(data.get("message"), str) and len(data["message"]) > 0, "Empty message in response"
        intent = data.get("intent")
        assert isinstance(intent, str) and len(intent) > 0, f"Intent should be a non-empty string, got: {intent}"

        # Test subsequent paraphrases with same session to verify semantic generalization and context handling
        for turn_index, query in enumerate(paraphrase_queries[1:], start=2):
            payload = {
                "query": query,
                "session_id": session_id,
                "user_id": user_id
            }
            resp = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert resp.status_code == 200, f"Turn {turn_index}: Expected status 200, got {resp.status_code}"
            resp_json = resp.json()
            assert resp_json.get("success") is True, f"Turn {turn_index}: Response success flag is not True"
            d = resp_json.get("data", {})
            # Check session_id preserved
            assert d.get("session_id") == session_id, f"Turn {turn_index}: session_id mismatch"
            # Check turn_id increments correctly
            assert isinstance(d.get("turn_id"), int) and d["turn_id"] == turn_index, f"Turn {turn_index}: turn_id incorrect"
            message = d.get("message", "")
            assert isinstance(message, str) and len(message) > 0, f"Turn {turn_index}: empty message"
            intent = d.get("intent")
            assert isinstance(intent, str) and len(intent) > 0, f"Turn {turn_index}: intent should be a non-empty string, got: {intent}"
            citations = d.get("evidence_citations")
            assert citations is not None and isinstance(citations, list), f"Turn {turn_index}: citations missing or wrong type"
            assert resp_json.get("error") is None, f"Turn {turn_index}: unexpected error in response"

    finally:
        pass

test_paraphrase_and_natural_language_generalization()
