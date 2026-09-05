import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_conversational_filler_and_noise_filtering():
    # Input query containing conversational fillers, colloquialisms, hesitation and informal preamble
    query_with_fillers = (
        "Uh, so like, I was wondering, you know, um, can you tell me how the budget update from 3,000 "
        "to 2,799 then 2,201 actually works? Also, I mean, what about the forensic ledger verification, "
        "and like, how does the demo completion reset to 3,000 happen? Just curious..."
    )

    payload = {
        "query": query_with_fillers,
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Unexpected HTTP status {response.status_code}"
    json_resp = response.json()

    assert "success" in json_resp and json_resp["success"] is True, "API did not return success=True"
    assert "data" in json_resp, "Missing data in response"

    data = json_resp["data"]

    # Validate presence and types of required fields in the response
    assert isinstance(data.get("session_id"), str) and data["session_id"], "Missing or invalid session_id"
    assert isinstance(data.get("turn_id"), int), "Missing or invalid turn_id"
    assert isinstance(data.get("message"), str) and data["message"].strip(), "Missing or empty message"
    assert isinstance(data.get("intent"), str) and data["intent"].strip(), "Missing or empty intent"
    assert isinstance(data.get("dialogue_act"), str) and data["dialogue_act"].strip(), "Missing or empty dialogue_act"
    assert isinstance(data.get("evidence_citations"), list), "evidence_citations should be a list"
    assert isinstance(data.get("live_data_used"), bool), "live_data_used should be boolean"
    assert isinstance(data.get("live_readings"), dict), "live_readings should be an object"
    assert isinstance(data.get("suggested_followups"), list), "suggested_followups should be a list"
    assert isinstance(data.get("action"), dict), "action should be an object"
    assert "trace" in data, "trace field is missing from data"

    # Content-specific assertions to verify conversational filler was filtered:
    # The message should contain references to budget update amounts 3000, 2799, 201 and forensic ledger verification and demo completion reset
    lower_message = data["message"].lower()
    # Remove any punctuation and currency symbols before checking
    normalized_message = lower_message.replace(',', '').replace('\u00a3', '').replace('\u20b9', '')
    assert any(x in normalized_message for x in ["3000", "2799", "201"]), "Response message missing budget update references"
    assert "forensic ledger" in lower_message or "ledger verification" in lower_message, "Response message missing forensic ledger verification reference"
    assert "demo completion reset" in lower_message or "reset to" in lower_message or "reset" in lower_message, "Response message missing demo completion reset reference"

    # The intent should reflect that the core technical request was identified (e.g. budget update, forensic ledger, or demo reset)
    # We expect the intent string to include at least one of these keywords.
    intent_lower = data["intent"].lower()
    assert ("budget" in intent_lower or "ledger" in intent_lower or "demo" in intent_lower), \
        "Intent does not reflect core technical topics of the query"

    # The error object should be null or empty if present
    error = json_resp.get("error")
    assert error is None or error == {}, f"Unexpected error content returned: {error}"


test_conversational_filler_and_noise_filtering()
