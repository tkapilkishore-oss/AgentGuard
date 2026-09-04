import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_typo_and_informal_language_robustness():
    url = f"{BASE_URL}/conversational/query"
    user_id = "test-user-typo-informal"
    # Various typo, informal abbreviations, punctuation irregularities, ungrammatical questions
    test_queries = [
        "Wht is tht price tamporing?",
        "How do I stp replay atacks?",
        "Tell me 'bout mandate budget pls!",
        "is the audit trail workin correctly?",
        "What's tha SHA256 verificashun process?",
        "doe's the system protect aginst doubel payments?",
        "Explain replay attacks, mkay?",
        "Price tamporing?? how 2 detect?",
        "Mandate budget - how it workz?",
        "audit trail: is it reliable??",
        "forgve me, but how does replays works",
        "can u explane the forensics ledger pls?",
        "hey, what about the secutiry boundary?",
        "how to prevnt replay attackss?",
        "is the system stop double spending?",
    ]

    session_id = None
    try:
        for i, query in enumerate(test_queries):
            payload = {
                "query": query,
                "session_id": session_id,
                "user_id": user_id
            }
            response = requests.post(url, json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"Status code {response.status_code} unexpected for query '{query}'"
            resp_json = response.json()
            assert resp_json.get("success") is True, f"API did not succeed for query '{query}'"
            data = resp_json.get("data", {})
            # Validate required fields present and non-empty
            assert "session_id" in data and isinstance(data["session_id"], str) and data["session_id"], "Missing or empty session_id"
            assert "turn_id" in data and isinstance(data["turn_id"], int) and data["turn_id"] >= 1, "Invalid turn_id"
            assert "message" in data and isinstance(data["message"], str) and data["message"].strip() != "", "Empty message in response"
            assert "intent" in data and isinstance(data["intent"], str) and data["intent"].strip() != "", "Missing or empty intent"
            assert "dialogue_act" in data and isinstance(data["dialogue_act"], str), "Missing dialogue_act"
            # evidence_citations can be empty list but must be present
            assert "evidence_citations" in data and isinstance(data["evidence_citations"], list), "Missing evidence_citations"
            # Check no unhelpful fallback (not a generic fallback message)
            fallback_indicators = ["I didn't understand","Sorry","I cannot answer","unrecognized","fallback"]
            message_lower = data["message"].lower()
            for indicator in fallback_indicators:
                assert indicator not in message_lower, f"Unhelpful fallback detected for query '{query}'"

            # Set session_id for next turn after first query that returns session_id
            if session_id is None:
                session_id = data["session_id"]

    finally:
        # Clean up: reset session by deleting it if session_id was created
        if session_id:
            del_url = f"{BASE_URL}/conversational/session/{session_id}"
            try:
                del_resp = requests.delete(del_url, timeout=TIMEOUT)
                # Accept either success or not found if already deleted
                if del_resp.status_code == 200:
                    del_json = del_resp.json()
                    assert del_json.get("success") is True, "Session reset not successful in cleanup"
                elif del_resp.status_code == 404:
                    pass
                else:
                    # Other unexpected status codes for cleanup
                    raise Exception(f"Unexpected status code {del_resp.status_code} on session cleanup")
            except Exception as e:
                # Log or raise if needed, here we just pass to avoid masking test results
                pass

test_typo_and_informal_language_robustness()