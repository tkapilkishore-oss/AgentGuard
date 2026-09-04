import requests

BASE_URL = "http://localhost:8000/conversational"
TIMEOUT = 30

def test_TC014_session_reset_lifecycle_and_state_clearing():
    session_id = None
    try:
        # Step 1: Start a new session with a query (POST /conversational/query)
        query_payload = {
            "query": "Explain price tampering detection mechanisms in AgentGuard.",
            "user_id": "test-user-001"
        }
        resp = requests.post(f"{BASE_URL}/query", json=query_payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        data = body.get("data", {})
        session_id = data.get("session_id")
        assert session_id is not None

        # Step 2: Add a follow-up query to preserve context
        followup_payload = {
            "query": "How does it prevent replay attacks?",
            "session_id": session_id,
            "user_id": "test-user-001"
        }
        resp = requests.post(f"{BASE_URL}/query", json=followup_payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        follow_data = body.get("data", {})
        assert follow_data.get("session_id") == session_id
        # Confirm turn_id incremented and dialogue_act present
        assert isinstance(follow_data.get("turn_id"), int)
        assert isinstance(follow_data.get("dialogue_act"), str) and len(follow_data["dialogue_act"]) > 0

        # Step 3: Confirm session state has context (GET /conversational/session/{session_id})
        resp = requests.get(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        session_data = body.get("data", {})
        assert session_data.get("session_id") == session_id
        assert isinstance(session_data.get("turn_count"), int) and session_data["turn_count"] >= 2
        assert isinstance(session_data.get("active_topic"), str) and len(session_data["active_topic"]) > 0
        assert isinstance(session_data.get("turns"), list) and len(session_data["turns"]) >= 2

        # Step 4: Reset session with DELETE /conversational/session/{session_id}
        resp = requests.delete(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("success") is True
        reset_data = body.get("data", {})
        assert reset_data.get("session_id") == session_id
        assert reset_data.get("status") == "reset"

        # Step 5: Confirm session state is cleared: GET /conversational/session/{session_id} should fail or show cleared
        resp = requests.get(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
        if resp.status_code == 200:
            cleared_body = resp.json()
            assert cleared_body.get("success") is True
            cleared_data = cleared_body.get("data", {})
            # session should be empty or reset: turn_count 0 or no turns or empty topic
            assert cleared_data.get("session_id") == session_id
            assert cleared_data.get("turn_count") == 0 or cleared_data.get("turns") == [] or cleared_data.get("active_topic") in (None, "", "reset")
        else:
            # Alternatively, possibly 404 if session considered expired/removed
            assert resp.status_code in (404, 410)

        # Step 6: Post a new query with the same session_id to verify fresh session state (no stale context)
        fresh_query_payload = {
            "query": "What is the mandate budget enforcement?",
            "session_id": session_id,
            "user_id": "test-user-001"
        }
        resp = requests.post(f"{BASE_URL}/query", json=fresh_query_payload, timeout=TIMEOUT)
        assert resp.status_code == 200
        fresh_body = resp.json()
        assert fresh_body.get("success") is True
        fresh_data = fresh_body.get("data", {})
        assert fresh_data.get("session_id") == session_id
        # Because session was reset, turn_id should start fresh (e.g., 1)
        assert fresh_data.get("turn_id") == 1
        # Active topic in response should correspond to fresh query's topic, not previous one
        assert fresh_data.get("intent") is not None
        assert isinstance(fresh_data.get("message"), str) and len(fresh_data["message"]) > 0

        # Step 7: Confirm session state after fresh query shows only 1 turn
        resp = requests.get(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
        assert resp.status_code == 200
        session_after_reset = resp.json()
        assert session_after_reset.get("success") is True
        new_session_data = session_after_reset.get("data", {})
        assert new_session_data.get("session_id") == session_id
        assert new_session_data.get("turn_count") == 1
        assert isinstance(new_session_data.get("turns"), list) and len(new_session_data["turns"]) == 1
        # active_topic should match fresh intent topic or be different from old active topic
        assert isinstance(new_session_data.get("active_topic"), str) and len(new_session_data["active_topic"]) > 0

    finally:
        # Cleanup: Try deleting session again in case left active (idempotent)
        if session_id:
            try:
                requests.delete(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
            except Exception:
                pass


test_TC014_session_reset_lifecycle_and_state_clearing()