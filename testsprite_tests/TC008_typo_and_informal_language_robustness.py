import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_typo_and_informal_language_robustness():
    # Examples of typos, informal abbreviations, punctuation and ungrammatical questions to test robustness
    test_queries = [
        "wht is the prce tamperin mechansm?",               # typos: what, price, tampering, mechanism
        "pls expln replay attcks!!",                        # informal abbreviation, punctuation irregularity
        "how dose it detct fraud?",                         # typo: does, detect + ungrammatical
        "whats th forensic ledger sumry",                  # contraction, typo, no question mark
        "can u tell me bout budget ₹2799?",                 # informal "u", abbreviation "bout"
        "why price tamperin happening???",                  # typo and multiple question marks
        "forgve me, how r audit trails wrked?",             # informal "r", typos forgive, worked
        "pls, hows demo completin reset done",              # informal pls, typo completion
        "wht iz live data's role in detectn?",              # typo and informal language, apostrophes
        "explain sha256 verifcation pls"                     # informal pls, typo verification
    ]

    # Prepare headers and user_id (optional in schema, but good to send)
    headers = {"Content-Type": "application/json"}
    user_id = str(uuid.uuid4())

    session_id = None
    try:
        # We will create one session and send multiple queries as new conversations or under same session
        # But since the test is about POST /conversational/query handling typos etc, can test independently

        for query in test_queries:
            payload = {
                "query": query,
                "user_id": user_id,
            }
            if session_id:
                payload["session_id"] = session_id

            resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
            assert resp.status_code == 200, f"Unexpected status code {resp.status_code} for query: {query}"

            resp_json = resp.json()

            # Validate response schema essentials
            # success boolean must be True or False (but should not fail or fallback unhelpfully)
            assert "success" in resp_json, "'success' field missing in response"
            assert isinstance(resp_json["success"], bool), "'success' field is not boolean"

            # error field exists and is None or empty object if success True
            assert "error" in resp_json, "'error' field missing in response"

            # Basic check: it should not be an unhelpful fallback response,
            # so success should be True and message should be non-empty string
            if resp_json["success"]:
                data = resp_json.get("data")
                assert data is not None, "'data' missing when success is True"
                # session_id should be present and non-empty string
                assert "session_id" in data and isinstance(data["session_id"], str) and data["session_id"], "Invalid or missing session_id"
                # turn_id should be integer >= 1
                assert "turn_id" in data and isinstance(data["turn_id"], int) and data["turn_id"] >= 1, "Invalid or missing turn_id"
                # message should be a meaningful string with some content
                message = data.get("message")
                assert isinstance(message, str) and message.strip(), "Empty or invalid message in response"
                # intent should be a non-empty string
                intent = data.get("intent")
                assert isinstance(intent, str) and intent.strip(), "Invalid or missing intent"
                # dialogue_act should be present as string
                dialogue_act = data.get("dialogue_act")
                assert isinstance(dialogue_act, str) and dialogue_act.strip(), "Invalid or missing dialogue_act"
                # evidence_citations should be a list (may be empty or populated)
                evidence = data.get("evidence_citations")
                assert isinstance(evidence, list), "evidence_citations must be a list"
            else:
                # If success is False, error field should contain details
                error = resp_json.get("error")
                assert error and isinstance(error, dict), "Expected error details when success is False"

            # On first successful query, capture session_id for subsequent queries
            if not session_id and resp_json.get("success") and resp_json.get("data", {}).get("session_id"):
                session_id = resp_json["data"]["session_id"]

    finally:
        # Cleanup: If a session was created, reset it via DELETE to clear test data
        if session_id:
            reset_url = f"http://localhost:8000/conversational/session/{session_id}"
            try:
                reset_resp = requests.delete(reset_url, timeout=TIMEOUT)
                assert reset_resp.status_code == 200
                reset_json = reset_resp.json()
                assert reset_json.get("success") is True
                assert reset_json.get("data", {}).get("session_id") == session_id
            except Exception:
                # Best effort cleanup, ignore errors here
                pass

test_typo_and_informal_language_robustness()