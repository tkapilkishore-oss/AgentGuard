import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_topic_switching_with_negative_transition_markers():
    headers = {"Content-Type": "application/json"}

    # Start a new conversation with a topic related to price tampering
    initial_query = "Can you explain price tampering in the AgentGuard system?"
    initial_payload = {
        "query": initial_query,
        "user_id": str(uuid.uuid4()),
    }

    # POST initial query to create session and topic
    response = requests.post(BASE_URL, json=initial_payload, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, f"Initial query failed: {response.text}"
    result = response.json()
    assert result.get("success") is True, f"Initial response failed: {result}"
    data = result.get("data", {})
    session_id = data.get("session_id")
    assert session_id, "No session_id returned in initial response"
    assert "price tampering" in data.get("message", "").lower() or "price" in data.get("intent", "").lower()

    try:
        # Define transitions with negative pivot markers
        negative_transitions = [
            "Forget that, tell me about replay attacks.",
            "Never mind about price tampering, what can you say about the forensic ledger?",
            "Instead of price tampering tell me about mandate budgets.",
            "Let's move away from price tampering and talk about audit trails."
        ]

        for query in negative_transitions:
            payload = {
                "query": query,
                "session_id": session_id,
                "user_id": initial_payload["user_id"],
            }
            resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
            assert resp.status_code == 200, f"Failed to post query: {query} Response: {resp.text}"
            resp_json = resp.json()
            assert resp_json.get("success") is True, f"Unsuccessful response for query: {query}"
            resp_data = resp_json.get("data", {})
            msg = resp_data.get("message", "").lower()
            intent = (resp_data.get("intent") or "").lower()
            dialogue_act = (resp_data.get("dialogue_act") or "").lower()

            # Check that the message or intent relates to the new topic and not the old keywords
            # Keywords to abandon (old topic keywords)
            abandoned_keywords = ["price tampering"]
            # Ensure none of abandoned_keywords are clung to in the response message or intent
            for kw in abandoned_keywords:
                assert kw not in msg, f"Response clings to abandoned keyword '{kw}' in message"
                assert kw not in intent, f"Response clings to abandoned keyword '{kw}' in intent"
                assert kw not in dialogue_act, f"Response clings to abandoned keyword '{kw}' in dialogue_act"

            # Also assert session_id remains the same (same ongoing session)
            assert resp_data.get("session_id") == session_id, "Session ID changed unexpectedly"

            # Suggested followups and evidence citations should be present for new topic
            assert isinstance(resp_data.get("suggested_followups"), list), "Suggested followups missing or invalid"
            assert isinstance(resp_data.get("evidence_citations"), list), "Evidence citations missing or invalid"

    finally:
        # Clear the session to clean up
        delete_url = f"http://localhost:8000/conversational/session/{session_id}"
        try:
            del_resp = requests.delete(delete_url, timeout=TIMEOUT)
            # Accept 200 or if already cleaned, ensure no error
            assert del_resp.status_code == 200, f"Failed to delete session: {del_resp.text}"
            del_json = del_resp.json()
            assert del_json.get("success") is True, f"Session delete reported failure: {del_json}"
        except Exception:
            # If delete call fails, log but do not raise to not mask test results
            pass


test_topic_switching_with_negative_transition_markers()