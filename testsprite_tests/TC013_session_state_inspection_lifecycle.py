import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
SESSION_STATE_URL_TEMPLATE = "http://localhost:8000/conversational/session/{session_id}"
TIMEOUT = 30


def test_session_state_inspection_lifecycle():
    session_id = None
    try:
        # Step 1: Create a new session with multiple turns using POST /conversational/query
        user_id = str(uuid.uuid4())
        # First turn
        payload_1 = {
            "query": "What is price tampering?",
            "user_id": user_id
        }
        resp1 = requests.post(BASE_URL, json=payload_1, timeout=TIMEOUT)
        assert resp1.status_code == 200, f"Failed initial query, status {resp1.status_code}"
        resp1_json = resp1.json()
        assert resp1_json.get("success") is True, f"Initial query unsuccessful: {resp1_json}"
        session_id = resp1_json["data"]["session_id"]
        assert session_id, "No session_id received from initial query"

        # Second turn: follow-up question maintaining session
        payload_2 = {
            "query": "Explain more about detection methods for it.",
            "session_id": session_id,
            "user_id": user_id
        }
        resp2 = requests.post(BASE_URL, json=payload_2, timeout=TIMEOUT)
        assert resp2.status_code == 200, f"Failed second query, status {resp2.status_code}"
        resp2_json = resp2.json()
        assert resp2_json.get("success") is True, f"Second query unsuccessful: {resp2_json}"
        assert resp2_json["data"]["session_id"] == session_id, "Session ID changed unexpectedly"
        assert resp2_json["data"]["turn_id"] > 1, "Turn ID did not increment on follow-up"

        # Step 2: GET /conversational/session/{session_id} to inspect session state
        session_url = SESSION_STATE_URL_TEMPLATE.format(session_id=session_id)
        resp_get = requests.get(session_url, timeout=TIMEOUT)
        assert resp_get.status_code == 200, f"Failed to get session state, status {resp_get.status_code}"
        get_json = resp_get.json()
        assert get_json.get("success") is True, f"GET session response success false: {get_json}"
        data = get_json.get("data", {})

        # Validate presence and types of expected keys
        assert data.get("session_id") == session_id, "Session ID mismatch in session state"
        assert isinstance(data.get("turn_count"), int) and data.get("turn_count") >= 2, "Turn count invalid or less than 2"
        assert isinstance(data.get("active_topic"), str) and data.get("active_topic"), "Active topic missing or empty"
        assert isinstance(data.get("dialogue_state"), dict), "Dialogue state missing or not an object"
        turns = data.get("turns")
        assert isinstance(turns, list) and len(turns) >= 2, "Turn history missing or incomplete"

        # Step 3: Attempt to GET a non-existent session and expect 404
        fake_session_id = str(uuid.uuid4())
        fake_session_url = SESSION_STATE_URL_TEMPLATE.format(session_id=fake_session_id)
        resp_404 = requests.get(fake_session_url, timeout=TIMEOUT)
        assert resp_404.status_code == 404, f"Expected 404 for non-existent session but got {resp_404.status_code}"

    finally:
        # Cleanup: delete the session if it was created
        if session_id:
            delete_url = f"http://localhost:8000/conversational/session/{session_id}"
            try:
                requests.delete(delete_url, timeout=TIMEOUT)
            except Exception:
                pass


test_session_state_inspection_lifecycle()