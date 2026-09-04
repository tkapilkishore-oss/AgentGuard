import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_ui_and_navigation_surface_recommendations():
    payload = {
        "query": (
            "Can you provide recommendations for UI navigation and action hints for "
            "application surfaces such as Forensic Ledger, Threat Lab, and Live Protection?"
        ),
        # Not providing session_id or user_id to simulate a fresh query as per PRD user flows.
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"

    resp_json = response.json()
    assert "success" in resp_json, "Response missing 'success' field"
    assert resp_json["success"] is True, f"API reported failure: {resp_json.get('error')}"

    data = resp_json.get("data")
    assert data, "Response data is empty or missing"

    # Validate that session_id and turn_id are present
    assert isinstance(data.get("session_id"), str) and data.get("session_id"), "Missing or invalid session_id"
    assert isinstance(data.get("turn_id"), int), "Missing or invalid turn_id"

    # Validate that message is a non-empty string
    assert isinstance(data.get("message"), str) and data.get("message").strip(), "Missing or empty message"

    # Validate intent and dialogue_act presence and are strings
    assert isinstance(data.get("intent"), str) and data.get("intent").strip(), "Missing or empty intent"
    assert isinstance(data.get("dialogue_act"), str) and data.get("dialogue_act").strip(), "Missing or empty dialogue_act"

    # Validate presence of UI/navigation related fields: suggested_followups and action with expected structure
    assert isinstance(data.get("suggested_followups"), list), "Missing or invalid suggested_followups"
    assert isinstance(data.get("action"), dict), "Missing or invalid action hint"

    # Since the test focuses on UI navigation recommendations for specific surfaces,
    # Validate that action hint contains keys or hints related to Forensic Ledger, Threat Lab, or Live Protection
    action = data["action"]
    action_str = str(action).lower()
    relevant_keywords = ["forensic ledger", "threat lab", "live protection", "navigation", "ui", "surface", "action hint"]
    assert any(keyword in action_str for keyword in relevant_keywords), (
        "Action hints do not reference expected application surfaces or navigation suggestions"
    )

    # Validate evidence_citations is a list (can be empty or populated)
    assert isinstance(data.get("evidence_citations"), list), "Missing or invalid evidence_citations"

    # Validate live_data_used is a boolean
    assert isinstance(data.get("live_data_used"), bool), "Missing or invalid live_data_used"

    # Validate progressive_disclosure_offer is a string (may be empty)
    assert isinstance(data.get("progressive_disclosure_offer"), str), "Missing or invalid progressive_disclosure_offer"

    # Validate trace is an object/dict (may be empty)
    assert isinstance(data.get("trace"), dict), "Missing or invalid trace"

test_ui_and_navigation_surface_recommendations()