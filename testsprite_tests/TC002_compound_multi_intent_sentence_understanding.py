import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_compound_multi_intent_sentence_understanding():
    # Compound multi-intent query using conjunctions as described
    query_text = (
        "Can you explain the price tampering issues and also how live protection impacts detection, "
        "but while keeping the current budget constraints in mind plus details on forensic ledger verification?"
    )

    payload = {
        "query": query_text,
        # Use empty strings instead of None for optional string fields
        "session_id": "",
        "user_id": ""
    }

    try:
        # POST request to /conversational/query to start conversation with compound multi-intent sentence
        response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"

    json_resp = response.json()

    # Validate top-level success
    assert "success" in json_resp and json_resp["success"] is True, "API did not return success=True"

    data = json_resp.get("data")
    assert data is not None, "Response missing 'data' field"

    # Validate required data fields presence
    required_fields = [
        "session_id",
        "turn_id",
        "message",
        "intent",
        "dialogue_act",
        "evidence_citations",
        "live_data_used",
        "live_readings",
        "progressive_disclosure_offer",
        "suggested_followups",
        "action",
        "trace"
    ]
    for field in required_fields:
        assert field in data, f"Response data missing '{field}' field"

    # Validate session_id is returned and is non-empty string
    assert isinstance(data["session_id"], str) and data["session_id"], "Invalid session_id returned"

    # Validate turn_id is a positive integer
    assert isinstance(data["turn_id"], int) and data["turn_id"] > 0, "Invalid turn_id returned"

    # Validate that the message is a non-empty string
    assert isinstance(data["message"], str) and data["message"].strip(), "Response message is empty or not a string"

    # Validate evidence citations is a non-empty list
    assert isinstance(data["evidence_citations"], list), "evidence_citations not a list"
    assert len(data["evidence_citations"]) > 0, "evidence_citations is empty"

    # Validate no error in response
    assert "error" in json_resp and (json_resp["error"] is None or json_resp["error"] == {}), "Response has unexpected error"


test_compound_multi_intent_sentence_understanding()
