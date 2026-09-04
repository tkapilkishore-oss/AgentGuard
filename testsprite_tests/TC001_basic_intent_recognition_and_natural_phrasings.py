import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_TC001_basic_intent_recognition_and_natural_phrasings():
    # Test inputs covering core AgentGuard topics with different natural phrasings
    test_queries = [
        # Price tampering
        "Can you explain how price tampering is detected in the system?",
        "What mechanisms prevent replay attacks?",
        "How does the mandate budget enforce spending limits?",
        "Tell me about the forensic ledger and its purpose.",
        "Describe the audit trail and how it is maintained.",
        "Explain SHA-256 verification for data integrity.",
        # Variations / paraphrases
        "How does the system protect against someone changing prices illegally?",
        "What is done to stop repeated transaction submissions?",
        "How is the spending cap enforced by the mandate?",
        "Give me details on the forensic ledger used here.",
        "What records are kept in the audit trail?",
        "Why is SHA-256 hash verification important in AgentGuard?"
    ]

    for query in test_queries:
        payload = {
            "query": query,
            "user_id": "test_user_001"
        }
        try:
            response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"Unexpected status code: {response.status_code} for query: {query}"
            resp_json = response.json()
            
            # Validate top level keys
            assert "success" in resp_json, "Missing 'success' field in response"
            assert resp_json["success"] is True, f"API indicated failure for query: {query}"
            assert "data" in resp_json and isinstance(resp_json["data"], dict), "Missing or invalid 'data' object in response"

            data = resp_json["data"]

            # Validate required response fields
            keys = ["session_id", "turn_id", "message", "intent", "dialogue_act", "evidence_citations", "live_data_used", "suggested_followups"]
            for key in keys:
                assert key in data, f"Missing '{key}' in response data for query: {query}"

            # session_id should be a non-empty string
            assert isinstance(data["session_id"], str) and len(data["session_id"]) > 0, "Invalid session_id"

            # turn_id should be int >= 1
            assert isinstance(data["turn_id"], int) and data["turn_id"] >= 1, "Invalid turn_id"

            # message should be a non-empty string
            assert isinstance(data["message"], str) and len(data["message"].strip()) > 0, "Empty message in response"

            # intent should be a non-empty string
            assert isinstance(data["intent"], str) and len(data["intent"]) > 0, "Empty intent in response"

            # dialogue_act should be a non-empty string
            assert isinstance(data["dialogue_act"], str) and len(data["dialogue_act"]) > 0, "Empty dialogue_act in response"

            # evidence_citations should be a non-empty list
            assert isinstance(data["evidence_citations"], list), "evidence_citations is not a list"
            assert len(data["evidence_citations"]) > 0, "No evidence citations found, expected at least one"

            # suggested_followups should be a list (can be empty)
            assert isinstance(data["suggested_followups"], list), "suggested_followups not a list"

            # Check live_data_used is boolean
            assert isinstance(data["live_data_used"], bool), "live_data_used is not boolean"

            # action and trace should be present as objects (they may be empty)
            assert "action" in data and isinstance(data["action"], dict), "Missing or invalid 'action' field"
            assert "trace" in data and isinstance(data["trace"], dict), "Missing or invalid 'trace' field"

            # No error object or error should be null/empty
            assert "error" in resp_json, "Missing 'error' field in response"
            error = resp_json["error"]
            assert error is None or error == {} or error == [], f"Unexpected error in response for query: {query}"

        except requests.exceptions.RequestException as e:
            assert False, f"Request failed for query '{query}': {e}"
        except AssertionError as ae:
            raise ae

test_TC001_basic_intent_recognition_and_natural_phrasings()
