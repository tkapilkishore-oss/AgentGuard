import requests

BASE_URL = "http://localhost:8000/conversational"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def test_TC014_session_reset_lifecycle_and_state_clearing():
    session_id = None
    try:
        # Step 1: Create a new session by posting a query without session_id
        query_payload = {
            "query": "Explain the concept of price tampering in AgentGuard.",
            "user_id": "test_user"
        }
        response = requests.post(
            f"{BASE_URL}/query", json=query_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json.get("success") is True, "Initial query did not succeed"
        data = resp_json.get("data")
        assert data and "session_id" in data and data["session_id"], "No session_id received"
        session_id = data["session_id"]

        # Step 2: Post a follow-up query with the session_id to build context
        followup_payload = {
            "query": "What are the detection mechanisms for it?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        response = requests.post(
            f"{BASE_URL}/query", json=followup_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json.get("success") is True, "Follow-up query did not succeed"
        data_followup = resp_json.get("data")
        assert data_followup and data_followup.get("session_id") == session_id

        # Step 3: Confirm session state before deletion with GET
        response = requests.get(
            f"{BASE_URL}/session/{session_id}", headers=HEADERS, timeout=TIMEOUT
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json.get("success") is True, "Session retrieval before reset failed"
        session_data = resp_json.get("data")
        assert session_data and session_data.get("turn_count", 0) >= 2, "Session turn count missing or insufficient"
        assert session_data.get("active_topic"), "Active topic missing before reset"

        # Step 4: Reset the session using DELETE
        response = requests.delete(
            f"{BASE_URL}/session/{session_id}", headers=HEADERS, timeout=TIMEOUT
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json.get("success") is True, "Session reset did not succeed"
        reset_data = resp_json.get("data")
        assert reset_data and reset_data.get("session_id") == session_id
        assert reset_data.get("status") and "reset" in reset_data.get("status").lower()

        # Step 5: Inspect session state after reset with GET
        response = requests.get(
            f"{BASE_URL}/session/{session_id}", headers=HEADERS, timeout=TIMEOUT
        )
        # According to PRD, after reset the session should be clean - expect not found or a cleared session
        if response.status_code == 200:
            resp_json = response.json()
            assert resp_json.get("success") is True, "Session retrieval after reset returned error"
            session_data_after_reset = resp_json.get("data")
            # After reset, turn_count should be 0 or minimal and no active topic
            assert session_data_after_reset is not None
            assert session_data_after_reset.get("turn_count") == 0 or session_data_after_reset.get("turns") == [], "Session turns not cleared after reset"
            # active_topic should be empty or None
            active_topic = session_data_after_reset.get("active_topic")
            assert active_topic in (None, "", {}), "Active topic not cleared after reset"
        else:
            # If 404 or other error for missing session is returned, that is acceptable
            assert response.status_code in (404, 410), f"Unexpected status code after session reset: {response.status_code}"

        # Step 6: Perform a new conversation query with the same session_id, should start fresh without old context
        new_query_payload = {
            "query": "Define replay attacks.",
            "session_id": session_id,
            "user_id": "test_user"
        }
        response = requests.post(
            f"{BASE_URL}/query", json=new_query_payload, headers=HEADERS, timeout=TIMEOUT
        )
        assert response.status_code == 200
        resp_json = response.json()
        assert resp_json.get("success") is True, "New query after reset did not succeed"
        new_data = resp_json.get("data")
        assert new_data and new_data.get("session_id") == session_id
        # New conversation should start at turn_id 1 or 0 (fresh)
        assert new_data.get("turn_id") == 1 or new_data.get("turn_id") == 0

        # Optional: Check that new response does not reference previous topic "price tampering"
        message = new_data.get("message", "").lower()
        assert "price tampering" not in message, "Old topic context leaked after reset"

    finally:
        # Cleanup: Delete session if still exists
        if session_id:
            try:
                requests.delete(
                    f"{BASE_URL}/session/{session_id}", headers=HEADERS, timeout=TIMEOUT
                )
            except Exception:
                pass


test_TC014_session_reset_lifecycle_and_state_clearing()