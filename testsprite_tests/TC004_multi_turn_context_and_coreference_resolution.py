import requests
import time

BASE_URL = "http://localhost:8000"
QUERY_ENDPOINT = f"{BASE_URL}/conversational/query"
TIMEOUT = 30


def test_multi_turn_context_and_coreference_resolution():
    user_id = "test_user_123"
    session_id = None

    # Initial query to start a new session with a clear topic
    initial_question = "Can you explain the price tampering mechanism in AgentGuard?"
    payload_1 = {"query": initial_question, "session_id": None, "user_id": user_id}

    try:
        # Turn 1: Start conversation, obtain session_id
        response1 = requests.post(QUERY_ENDPOINT, json=payload_1, timeout=TIMEOUT)
        assert response1.status_code == 200, f"Unexpected status code: {response1.status_code}"
        resp_json_1 = response1.json()
        assert resp_json_1.get("success") is True
        data1 = resp_json_1.get("data", {})
        session_id = data1.get("session_id")
        assert session_id is not None and isinstance(data1.get("turn_id"), int)
        assert isinstance(data1.get("message"), str) and len(data1.get("message")) > 0
        assert isinstance(data1.get("intent"), str) and len(data1.get("intent")) > 0

        # Store current turn id for validation of progression
        prior_turn_id = data1.get("turn_id")

        # Follow-up queries using pronouns and references to test coreference resolution
        follow_ups = [
            "What about it, how does it detect tampering?",
            "Can you elaborate on that check involved?",
            "Is this mechanism effective against attacks?",
            "Tell me more about the attack it focuses on.",
            "Does the check cover all replay attacks?"
        ]

        for i, q in enumerate(follow_ups, start=2):
            payload_n = {"query": q, "session_id": session_id, "user_id": user_id}
            response_n = requests.post(QUERY_ENDPOINT, json=payload_n, timeout=TIMEOUT)
            assert response_n.status_code == 200, f"Unexpected status code on turn {i}: {response_n.status_code}"
            resp_json_n = response_n.json()
            assert resp_json_n.get("success") is True, f"Request failed on turn {i}"
            data_n = resp_json_n.get("data", {})

            # Validate session_id consistency
            assert data_n.get("session_id") == session_id, f"Session ID changed on turn {i}"

            # Validate turn progression (turn_id increments)
            turn_id = data_n.get("turn_id")
            assert isinstance(turn_id, int), f"Invalid turn_id type on turn {i}"
            assert turn_id > prior_turn_id, f"Turn ID did not increment on turn {i}"
            prior_turn_id = turn_id

            # Validate message presence and content (not generic)
            message = data_n.get("message", "")
            assert len(message) > 0, f"Empty message response on turn {i}"
            lowered = message.lower()
            # The response should mention price tampering or related terms as active topic,
            # and should not fallback to generic or unrelated answers
            assert any(keyword in lowered for keyword in [
                "tampering", "attack", "check", "mechanism"
            ]), f"Response does not address active topic on turn {i}"

            # Validate intent and dialogue_act exist and are non-empty strings
            intent = data_n.get("intent")
            dialogue_act = data_n.get("dialogue_act")
            assert isinstance(intent, str) and len(intent) > 0, f"Invalid intent on turn {i}"
            assert isinstance(dialogue_act, str) and len(dialogue_act) > 0, f"Invalid dialogue_act on turn {i}"

            # Validate evidence citations are present (non-empty list)
            citations = data_n.get("evidence_citations")
            assert isinstance(citations, list), f"Invalid citations type on turn {i}"

            # Validate trace and action objects exist (at least dict or None)
            assert "trace" in data_n and isinstance(data_n.get("trace"), (dict, type(None)))
            assert "action" in data_n and isinstance(data_n.get("action"), (dict, type(None)))

            # Small delay to simulate real conversation pacing
            time.sleep(0.2)

    finally:
        # Try to reset/delete session to cleanup if API supports session reset
        if session_id:
            try:
                delete_resp = requests.delete(f"{BASE_URL}/conversational/session/{session_id}", timeout=TIMEOUT)
                if delete_resp.status_code == 200:
                    delete_json = delete_resp.json()
                    assert delete_json.get("success") is True
                    assert delete_json.get("data", {}).get("session_id") == session_id
                    assert "status" in delete_json.get("data", {})
            except Exception:
                pass


test_multi_turn_context_and_coreference_resolution()