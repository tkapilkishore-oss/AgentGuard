import requests

BASE_URL = "http://localhost:8000/conversational"
TIMEOUT = 30


def test_session_reset_lifecycle_and_state_clearing():
    # Step 1: Create a new session by posting a query without a session_id
    query_url = f"{BASE_URL}/query"
    initial_payload = {
        "query": "What is price tampering in AgentGuard?",
        "user_id": "test_user"
    }
    try:
        response = requests.post(query_url, json=initial_payload, timeout=TIMEOUT)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        json_resp = response.json()
        assert json_resp.get("success") is True, "API did not succeed in creating session"
        data = json_resp.get("data")
        assert data is not None, "Response missing 'data' field"
        session_id = data.get("session_id")
        assert session_id, "No session_id returned"

        # Step 2: Post another query with the same session_id to ensure context exists
        followup_payload = {
            "query": "Can you explain how it works?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        followup_resp = requests.post(query_url, json=followup_payload, timeout=TIMEOUT)
        assert followup_resp.status_code == 200, f"Unexpected status code on followup: {followup_resp.status_code}"
        followup_json = followup_resp.json()
        assert followup_json.get("success") is True, "API did not succeed on followup query"
        followup_data = followup_json.get("data")
        assert followup_data.get("session_id") == session_id, "Session ID changed unexpectedly on followup"
        previous_turn_id = followup_data.get("turn_id")
        assert previous_turn_id is not None, "Missing turn_id in followup"

        # Step 3: Delete the session to reset it
        delete_url = f"{BASE_URL}/session/{session_id}"
        delete_resp = requests.delete(delete_url, timeout=TIMEOUT)
        assert delete_resp.status_code == 200, f"Unexpected status code on DELETE: {delete_resp.status_code}"
        delete_json = delete_resp.json()
        assert delete_json.get("success") is True, "Session reset failed"
        delete_data = delete_json.get("data")
        assert delete_data.get("session_id") == session_id, "Deleted session_id mismatch"
        assert delete_data.get("status") == "reset", "Session reset status not confirmed"

        # Step 4: Get session state after reset, expect error or empty/clean state
        get_session_url = f"{BASE_URL}/session/{session_id}"
        get_resp = requests.get(get_session_url, timeout=TIMEOUT)
        if get_resp.status_code == 200:
            get_json = get_resp.json()
            # Should show a clean session with no prior topic context
            assert get_json.get("success") is True, "Session state retrieval failed after reset"
            session_data = get_json.get("data")
            assert session_data.get("session_id") == session_id, "Session ID mismatch in get after reset"
            turn_count = session_data.get("turn_count")
            assert turn_count == 0 or turn_count is None, "Expected empty or reset turn count"
            active_topic = session_data.get("active_topic")
            assert not active_topic, "Expected no active topic after reset"

        else:
            # If 404 or other error status, assert it as acceptable as session is reset
            assert get_resp.status_code in [404, 410], "Unexpected status code retrieving session after reset"

        # Step 5: Post a new query with the same session_id - should be fresh with no prior context
        new_query_payload = {
            "query": "What is replay attack detection?",
            "session_id": session_id,
            "user_id": "test_user"
        }
        new_query_resp = requests.post(query_url, json=new_query_payload, timeout=TIMEOUT)
        assert new_query_resp.status_code == 200, f"Unexpected status code on new query: {new_query_resp.status_code}"
        new_query_json = new_query_resp.json()
        assert new_query_json.get("success") is True, "New query with reset session failed"
        new_data = new_query_json.get("data")
        assert new_data.get("session_id") == session_id, "Session ID mismatch on new query"
        new_turn_id = new_data.get("turn_id")
        assert new_turn_id == 1 or new_turn_id == 0, "Expected first turn after reset"
        new_message = new_data.get("message")
        assert new_message, "No message returned in new query response"

    finally:
        # Cleanup: Attempt to delete session again to ensure no residue
        if 'session_id' in locals():
            try:
                requests.delete(f"{BASE_URL}/session/{session_id}", timeout=TIMEOUT)
            except Exception:
                pass


test_session_reset_lifecycle_and_state_clearing()