import requests

BASE_URL = "http://localhost:8000/conversational"

def test_session_state_inspection_lifecycle():
    timeout = 30
    headers = {
        'Content-Type': 'application/json'
    }
    session_id = None

    try:
        # Step 1: Create a new session with multiple turns via POST /conversational/query
        user_id = "test-user-tc013"
        query_1 = {
            "query": "Explain price tampering detection.",
            "user_id": user_id
        }
        resp1 = requests.post(
            f"{BASE_URL}/query",
            json=query_1,
            headers=headers,
            timeout=timeout
        )
        assert resp1.status_code == 200, f"Unexpected status code on initial query: {resp1.status_code}"
        init_data = resp1.json()
        assert init_data.get("success") is True, "Initial query response success flag not true"
        session_id = init_data["data"].get("session_id")
        assert session_id, "session_id missing from initial query response"

        # Make a second turn in the session to create multi-turn context
        query_2 = {
            "query": "How does it detect replay attacks?",
            "session_id": session_id,
            "user_id": user_id
        }
        resp2 = requests.post(
            f"{BASE_URL}/query",
            json=query_2,
            headers=headers,
            timeout=timeout
        )
        assert resp2.status_code == 200, f"Unexpected status code on second query: {resp2.status_code}"
        data2 = resp2.json()
        assert data2.get("success") is True, "Second query response success flag not true"
        assert data2["data"].get("turn_id", 0) > 1, "Expected turn_id greater than 1 on second turn"

        # Step 2: GET /conversational/session/{session_id} to inspect session state
        resp_get = requests.get(
            f"{BASE_URL}/session/{session_id}",
            headers=headers,
            timeout=timeout
        )
        assert resp_get.status_code == 200, f"Unexpected status code on session get: {resp_get.status_code}"
        session_data = resp_get.json()
        assert session_data.get("success") is True, "Session get response success flag not true"

        data = session_data.get("data")
        assert data, "Missing data field in session get response"
        # Validate returned fields according to PRD
        assert data.get("session_id") == session_id, "Mismatch session_id in session data"
        assert isinstance(data.get("turn_count"), int) and data.get("turn_count") >= 2, "turn_count missing or incorrect"
        assert isinstance(data.get("active_topic"), str) and data.get("active_topic"), "active_topic missing or empty"
        assert isinstance(data.get("dialogue_state"), dict), "dialogue_state missing or not a dict"
        turns = data.get("turns")
        assert isinstance(turns, list), "turns missing or not a list"
        assert len(turns) >= 2, "turns list does not contain multiple turns"

        # Step 3: GET /conversational/session/{session_id} for a non-existent session_id returns 404
        fake_session_id = "nonexistent-session-1234567890"
        resp_404 = requests.get(
            f"{BASE_URL}/session/{fake_session_id}",
            headers=headers,
            timeout=timeout
        )
        assert resp_404.status_code == 404, f"Expected 404 for non-existent session_id but got {resp_404.status_code}"

    finally:
        if session_id:
            # Clean up session by deleting it to not leave test residue
            try:
                requests.delete(
                    f"{BASE_URL}/session/{session_id}",
                    headers=headers,
                    timeout=timeout
                )
            except Exception:
                pass

test_session_state_inspection_lifecycle()