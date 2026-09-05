import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_multi_turn_context_and_coreference_resolution():
    headers = {"Content-Type": "application/json"}
    user_id = "test-user-001"

    # Start a new conversation (turn 1) - initial question to establish an active topic
    initial_query = "Can you explain the price tampering detection mechanism?"
    payload_1 = {"query": initial_query, "user_id": user_id}
    response_1 = requests.post(BASE_URL, json=payload_1, headers=headers, timeout=TIMEOUT)
    assert response_1.status_code == 200, f"Unexpected status code: {response_1.status_code}"
    resp_json_1 = response_1.json()
    assert resp_json_1.get("success") is True, "API response success flag is False"
    data_1 = resp_json_1.get("data")
    assert data_1 is not None, "Response data missing in initial query"
    session_id = data_1.get("session_id")
    turn_id_1 = data_1.get("turn_id")
    first_intent = data_1.get("intent")
    first_message = data_1.get("message")
    assert isinstance(session_id, str) and session_id.strip() != "", "Invalid session_id returned"
    assert isinstance(turn_id_1, int) and turn_id_1 == 1, "Turn ID for first turn should be 1"
    assert isinstance(first_intent, str) and first_intent != "", "Intent missing or empty in first response"
    assert isinstance(first_message, str) and first_message != "", "Message missing or empty in first response"

    # Prepare follow-up queries using pronouns/coreferences
    follow_ups = [
        "Can you give an example of how it could be exploited?",
        "How does that check protect the system?",
        "Explain this in relation to replay attacks.",
        "What is the difference between the check and the attack?",
        "How should the attack be mitigated?"
    ]

    prior_turn_id = turn_id_1
    for idx, query in enumerate(follow_ups, start=2):
        payload_follow = {"query": query, "session_id": session_id, "user_id": user_id}
        response_follow = requests.post(BASE_URL, json=payload_follow, headers=headers, timeout=TIMEOUT)
        assert response_follow.status_code == 200, f"Unexpected status code on turn {idx}: {response_follow.status_code}"
        resp_json = response_follow.json()
        assert resp_json.get("success") is True, f"API response success flag is False on turn {idx}"
        data = resp_json.get("data")
        assert data is not None, f"Response data missing on turn {idx}"
        # Validate turn_id increments
        turn_id = data.get("turn_id")
        assert turn_id == idx, f"Turn ID expected {idx} but got {turn_id}"

        # Confirm session_id remains the same
        assert data.get("session_id") == session_id, f"Session ID changed on turn {idx}"
        # Validate that the message is a non-empty string
        message = data.get("message")
        assert isinstance(message, str) and message.strip() != "", f"Empty or missing message in turn {idx}"

        prior_turn_id = turn_id


test_multi_turn_context_and_coreference_resolution()