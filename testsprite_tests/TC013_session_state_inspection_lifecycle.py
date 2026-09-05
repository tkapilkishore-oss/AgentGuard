import requests

BASE_URL = "http://localhost:8000/conversational"

def test_session_state_inspection_lifecycle():
    headers = {"Content-Type": "application/json"}
    timeout = 30

    # Step 1: Create a new session with multiple turns via POST /conversational/query
    session_id = None
    try:
        # Initial query to create session
        payload1 = {"query": "Tell me about price tampering in AgentGuard", "user_id": "test_user"}
        resp1 = requests.post(f"{BASE_URL}/query", json=payload1, headers=headers, timeout=timeout)
        assert resp1.status_code == 200, f"Unexpected status code on first query: {resp1.status_code}"
        json1 = resp1.json()
        assert json1.get("success") is True, "Initial query did not succeed"
        session_id = json1["data"]["session_id"]
        turn_id1 = json1["data"]["turn_id"]
        assert isinstance(session_id, str) and len(session_id) > 0, "Invalid session_id returned"
        assert isinstance(turn_id1, int) and turn_id1 == 1, "First turn_id should be 1"

        # Follow-up query to preserve multi-turn context
        payload2 = {"query": "And what about replay attacks?", "session_id": session_id, "user_id": "test_user"}
        resp2 = requests.post(f"{BASE_URL}/query", json=payload2, headers=headers, timeout=timeout)
        assert resp2.status_code == 200, f"Unexpected status code on second query: {resp2.status_code}"
        json2 = resp2.json()
        assert json2.get("success") is True, "Second query did not succeed"
        turn_id2 = json2["data"]["turn_id"]
        assert turn_id2 == turn_id1 + 1, "Turn count did not increment on second query"

        # Step 2: Retrieve session state via GET /conversational/session/{session_id}
        resp_get = requests.get(f"{BASE_URL}/session/{session_id}", headers=headers, timeout=timeout)
        assert resp_get.status_code == 200, f"Unexpected status code on session GET: {resp_get.status_code}"
        json_get = resp_get.json()
        assert json_get.get("success") is True, "Session GET did not succeed"
        data = json_get.get("data")
        assert data, "No data found in session GET response"
        assert data.get("session_id") == session_id, "Returned session_id mismatch"
        assert isinstance(data.get("turn_count"), int) and data["turn_count"] >= 2, "Turn count missing or incorrect"
        assert isinstance(data.get("active_topic"), str) and len(data["active_topic"]) > 0, "Active topic missing or empty"
        assert isinstance(data.get("dialogue_state"), dict), "Dialogue state missing or not an object"
        turns = data.get("turns")
        assert isinstance(turns, list) and len(turns) >= 2, "Turns list missing or not multi-turn"
        for turn in turns:
            assert "turn_id" in turn, "Turn missing turn_id"
            assert "message" in turn or "query" in turn, "Turn missing message or query"

        # Step 3: Try to get non-existent session, expect 404
        fake_session_id = "nonexistent-session-id-1234567890"
        resp_404 = requests.get(f"{BASE_URL}/session/{fake_session_id}", headers=headers, timeout=timeout)
        assert resp_404.status_code == 404, f"Expected 404 for non-existent session but got {resp_404.status_code}"

    finally:
        # Cleanup: Delete the session to reset state if it was created
        if session_id:
            try:
                requests.delete(f"{BASE_URL}/session/{session_id}", headers=headers, timeout=timeout)
            except Exception:
                pass

test_session_state_inspection_lifecycle()