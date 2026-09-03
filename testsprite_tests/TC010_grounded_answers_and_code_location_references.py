import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_grounded_answers_and_code_location_references():
    query_text = (
        "Where are the security checks and protections implemented in the AgentGuard system? "
        "Please provide accurate code location references including file paths like backend/app/policy/engine.py, "
        "backend/app/api/execute.py, and backend/app/services/audit_log.py."
    )
    user_id = str(uuid.uuid4())

    payload = {
        "query": query_text,
        "user_id": user_id,
    }

    response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
    assert response.status_code == 200, f"Expected status 200 but got {response.status_code}"

    resp_json = response.json()

    assert "success" in resp_json, "Response missing 'success' field"
    assert resp_json["success"] is True, f"API reported failure: {resp_json.get('error')}"

    data = resp_json.get("data")
    assert data is not None, "Response missing 'data' section"

    # Validate presence of expected fields
    expected_fields = [
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
        "trace",
    ]
    for field in expected_fields:
        assert field in data, f"Response data missing expected field '{field}'"

    # Check that the message contains at least one known code location reference
    message = data["message"]
    assert any(
        path in message
        for path in [
            "backend/app/policy/engine.py",
            "backend/app/api/execute.py",
            "backend/app/services/audit_log.py",
        ]
    ), "Response message does not contain expected code location references"

    # evidence_citations should be a list and contain relevant citations
    citations = data["evidence_citations"]
    assert isinstance(citations, list), "'evidence_citations' is not a list"
    assert len(citations) > 0, "No evidence citations provided in response"

    # Check intent is a string and non-empty
    intent = data["intent"]
    assert isinstance(intent, str) and intent != "", f"Invalid intent field value: {intent}"

    # dialogue_act should be non-empty string
    dialogue_act = data["dialogue_act"]
    assert isinstance(dialogue_act, str) and dialogue_act != "", "Invalid dialogue_act field"

    # live_data_used is boolean
    assert isinstance(data["live_data_used"], bool), "'live_data_used' is not boolean"

    # suggested_followups should be a list (can be empty)
    assert isinstance(data["suggested_followups"], list), "'suggested_followups' is not a list"

    # error field should be None or empty object on success
    assert (
        resp_json.get("error") is None or resp_json.get("error") == {}
    ), f"Error found in success response: {resp_json.get('error')}"


test_grounded_answers_and_code_location_references()