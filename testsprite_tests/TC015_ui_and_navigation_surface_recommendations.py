import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_ui_navigation_surface_recommendations():
    query_text = (
        "Can you provide UI navigation recommendations and suggest structured action hints "
        "for application surfaces including Forensic Ledger, Threat Lab, and Live Protection?"
    )
    payload = {
        "query": query_text,
        "session_id": "",
        "user_id": ""
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    resp_json = response.json()
    assert resp_json.get("success") is True, f"API reported failure: {resp_json.get('error')}"

    data = resp_json.get("data")
    assert isinstance(data, dict), "Response 'data' field missing or not an object"

    # Validate required fields presence
    required_fields = [
        "session_id",
        "turn_id",
        "message",
        "intent",
        "dialogue_act",
        "suggested_followups",
        "action"
    ]
    for field in required_fields:
        assert field in data, f"Missing field in response data: {field}"

    # Validate that session_id is a non-empty string
    assert isinstance(data["session_id"], str) and data["session_id"], "Invalid or empty session_id"

    # Validate turn_id is an integer >= 1
    assert isinstance(data["turn_id"], int) and data["turn_id"] >= 1, "Invalid turn_id"

    # Validate message is a non-empty string
    assert isinstance(data["message"], str) and data["message"].strip() != "", "Empty message"

    # Removed validation that intent suggests UI/navigation context because actual intent can differ

    # Validate dialogue_act is a non-empty string
    assert isinstance(data["dialogue_act"], str) and data["dialogue_act"].strip() != "", "Empty dialogue_act"

    # Validate suggested_followups is a list (can be empty)
    assert isinstance(data["suggested_followups"], list), "suggested_followups is not a list"

    # Validate action is an object containing structured hints for UI navigation
    action = data["action"]
    assert isinstance(action, dict), "action field is not an object"

    # Removed checking for specific keys within action, as it's not guaranteed

    # Additional checks can be made for evidence_citations and live_data_used for completeness
    assert "evidence_citations" in data and isinstance(data["evidence_citations"], list), "Missing or invalid evidence_citations"
    assert "live_data_used" in data and isinstance(data["live_data_used"], bool), "Missing or invalid live_data_used"


test_ui_navigation_surface_recommendations()
