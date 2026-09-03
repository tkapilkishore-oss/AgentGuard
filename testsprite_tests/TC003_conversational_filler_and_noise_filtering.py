import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_conversational_filler_and_noise_filtering():
    # Input with conversational filler, colloquialisms, hesitation and informal preamble
    noisy_query = (
        "Uh, so like, um, I was kind of wondering if you could tell me, you know, "
        "how exactly the AgentGuard firewall detects replay attacks? "
        "I mean, what’s the core mechanism or something?"
    )
    payload = {
        "query": noisy_query,
        "user_id": "test_user_001"
    }

    try:
        response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to POST /conversational/query failed: {e}"

    resp_json = response.json()

    # Assert general success
    assert resp_json.get("success") is True, f"Expected success=True but got {resp_json.get('success')}"
    data = resp_json.get("data")
    assert data, "Response missing 'data' object"

    # Validate the session_id is returned and non-empty string
    session_id = data.get("session_id")
    assert isinstance(session_id, str) and session_id.strip(), "Invalid or missing session_id"

    # Validate turn_id is an integer >= 1
    turn_id = data.get("turn_id")
    assert isinstance(turn_id, int) and turn_id >= 1, f"Invalid turn_id: {turn_id}"

    # Message should be a non-empty string (filtered and focused answer)
    message = data.get("message")
    assert isinstance(message, str) and message.strip(), "Response message is missing or empty"

    # Intent should be a non-empty string indicating recognized core technical request
    intent = data.get("intent")
    assert isinstance(intent, str) and intent.strip(), "Intent is missing or empty"

    # Dialogue act should be a string describing the type of response (e.g. 'inform')
    dialogue_act = data.get("dialogue_act")
    assert isinstance(dialogue_act, str) and dialogue_act.strip(), "Dialogue act is missing or empty"

    # Evidence citations should be a list (may be empty but validate type)
    evidence_citations = data.get("evidence_citations")
    assert isinstance(evidence_citations, list), f"Expected list for evidence_citations but got {type(evidence_citations)}"

    # live_data_used should be a boolean as per schema
    live_data_used = data.get("live_data_used")
    assert isinstance(live_data_used, bool), f"Expected boolean for live_data_used but got {type(live_data_used)}"

    # Trace should be a dict or None (error details), verify type if present
    trace = data.get("trace")
    if trace is not None:
        assert isinstance(trace, dict), f"Trace should be dict if present but got {type(trace)}"

    # Error object should be None or empty on success
    error = resp_json.get("error")
    assert error in (None, {}, []), f"Unexpected error present in response: {error}"

    # Check that message does not contain filler words and addresses core question
    filler_terms = ["uh", "um", "like", "you know", "I mean", "kind of", "so", "actually", "basically"]
    message_lower = message.lower()
    assert not any(filler in message_lower for filler in filler_terms), "Response message contains conversational filler terms"

    # Check that the response message mentions key technical terms about replay attack detection
    key_topics = ["replay attack", "detection", "mechanism", "identify", "agentguard", "firewall"]
    assert any(topic in message_lower for topic in key_topics), "Response message does not address the core technical request about replay attacks"

test_conversational_filler_and_noise_filtering()