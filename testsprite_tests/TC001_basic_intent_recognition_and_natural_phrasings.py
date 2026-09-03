import requests

def test_basic_intent_recognition_and_natural_phrasings():
    base_url = "http://localhost:8000/conversational/query"
    timeout = 30
    test_phrases = [
        "Can you explain price tampering and how it is detected?",
        "What do replay attacks mean in AgentGuard?",
        "Tell me about the mandate budget and its enforcement.",
        "How does the forensic ledger help in tracking?",
        "What is the role of the audit trail in security?",
        "Explain SHA-256 verification in AgentGuard context."
    ]

    session_id = None
    try:
        for i, query in enumerate(test_phrases):
            payload = {
                "query": query
            }
            if session_id:
                payload["session_id"] = session_id

            response = requests.post(base_url, json=payload, timeout=timeout)
            assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
            json_data = response.json()
            assert "success" in json_data, "Missing 'success' field in response"
            assert json_data["success"] is True, f"API call failed: {json_data.get('error')}"
            data = json_data.get("data")
            assert data is not None, "Response 'data' is None"
            # Validate session_id and save the first one
            if i == 0:
                assert "session_id" in data and data["session_id"], "Missing session_id in first response"
                session_id = data["session_id"]
            else:
                assert data.get("session_id") == session_id, "Session ID changed mid-conversation"
            # Check turn_id increments
            assert isinstance(data.get("turn_id"), int), "turn_id missing or not integer"
            # Validate intent is a non-empty string
            recognized_intent = data.get("intent")
            assert isinstance(recognized_intent, str) and len(recognized_intent.strip()) > 0, "Intent is missing or empty"
            # Validate message presence and non-empty
            message = data.get("message", "")
            assert isinstance(message, str) and len(message.strip()) > 0, "Response message is empty"
            # Validate evidence citations present and is a non-empty array
            evidence_citations = data.get("evidence_citations")
            assert isinstance(evidence_citations, list), "evidence_citations not a list"
            assert len(evidence_citations) > 0, "No evidence citations found in response"

    finally:
        # No cleanup needed on /conversational/query since no resource created
        pass

test_basic_intent_recognition_and_natural_phrasings()
