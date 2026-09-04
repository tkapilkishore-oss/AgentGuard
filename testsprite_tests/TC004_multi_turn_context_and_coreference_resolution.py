import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_multi_turn_context_coreference_resolution():
    headers = {"Content-Type": "application/json"}

    user_id = str(uuid.uuid4())
    session_id = None

    # Turn 1: Start new conversation on a specific AgentGuard topic to establish context (e.g. "price tampering")
    query_1 = "Can you explain the AgentGuard price tampering detection mechanism?"
    payload_1 = {"query": query_1, "user_id": user_id}

    try:
        r1 = requests.post(BASE_URL, json=payload_1, headers=headers, timeout=TIMEOUT)
        assert r1.status_code == 200, f"Unexpected status code on turn 1: {r1.status_code}"
        resp1 = r1.json()
        assert resp1.get("success") is True, "API responded unsuccessfully on turn 1"
        data1 = resp1.get("data", {})
        session_id = data1.get("session_id")
        turn_id_1 = data1.get("turn_id")
        intent_1 = data1.get("intent")
        message_1 = data1.get("message", "")
        assert session_id and isinstance(session_id, str), "Missing or invalid session_id in turn 1 response"
        assert isinstance(turn_id_1, int) and turn_id_1 == 1, "Invalid turn_id for turn 1"
        assert isinstance(intent_1, str) and len(intent_1) > 0, "Missing intent in turn 1 response"
        assert isinstance(message_1, str) and len(message_1) > 0, "Empty message in turn 1 response"

        # Validate that turn 1 establishes the price tampering topic via trace or message
        trace_1 = data1.get("trace", {})
        assert trace_1.get("canonical_topic") == "PRICE_TAMPERING" or "price tampering" in message_1.lower(), (
            "Turn 1 did not establish price tampering topic"
        )
        assert any(term in message_1.lower() for term in ["price", "tampering", "catalog"]), (
            "Turn 1 message does not discuss price tampering"
        )

        # Define a series of follow-up pronoun-based questions referencing the established active topic

        pronoun_queries = [
            "How does it detect anomalies?",
            "Can you tell me more about that?",
            "What about this mechanism's limitations?",
            "Explain the check it performs on transactions.",
            "Could you give details about the attack it prevents?"
        ]

        previous_turn_id = turn_id_1

        for i, follow_up_query in enumerate(pronoun_queries, start=2):
            payload_followup = {"query": follow_up_query, "session_id": session_id, "user_id": user_id}
            r_followup = requests.post(BASE_URL, json=payload_followup, headers=headers, timeout=TIMEOUT)
            assert r_followup.status_code == 200, f"Unexpected status code on turn {i}: {r_followup.status_code}"
            resp_followup = r_followup.json()
            assert resp_followup.get("success") is True, f"API responded unsuccessfully on turn {i}"
            data_followup = resp_followup.get("data", {})

            current_session_id = data_followup.get("session_id")
            current_turn_id = data_followup.get("turn_id")
            current_intent = data_followup.get("intent")
            current_dialogue_act = data_followup.get("dialogue_act")
            current_message = data_followup.get("message", "")

            assert current_session_id == session_id, f"Session ID changed on turn {i}"
            # Removed assertion that current_turn_id == i because turn_id can be a sequence not necessarily aligned with i
            assert current_intent, f"Missing intent on turn {i}"
            assert current_dialogue_act, f"Missing dialogue_act on turn {i}"
            assert isinstance(current_message, str) and len(current_message) > 0, f"Empty message on turn {i}"

            # Validate that pronouns are resolved to the original topic of "price tampering" or related terms
            # The intent or message should reflect the context without generic fallback
            intent_lower = current_intent.lower()
            msg_lower = current_message.lower()
            topic_keywords = ["price", "tampering", "attack", "check", "detection", "transaction"]

            matched = any((k in intent_lower) or (k in msg_lower) for k in topic_keywords)
            assert matched, (
                f"Turn {i} response does not appear to preserve context or resolve pronouns correctly."
                f"\nIntent: {current_intent}\nMessage: {current_message}"
            )

            # Turn ID should increment by 1 each turn
            assert current_turn_id == previous_turn_id + 1, f"Turn ID mismatch at turn {i}"

            previous_turn_id = current_turn_id

    finally:
        # Cleanup: Delete the conversational session to reset system state using DELETE /conversational/session/{session_id}
        # This endpoint exists per PRD but is not in base_url; so adjust URL accordingly.
        if session_id:
            import time

            delete_url = f"http://localhost:8000/conversational/session/{session_id}"
            try:
                resp_del = requests.delete(delete_url, timeout=TIMEOUT)
                # Accept 200 success or 404 if session already expired; do not fail test on cleanup
                if resp_del.status_code not in (200, 404):
                    print(f"Warning: cleanup delete returned unexpected status {resp_del.status_code}")
            except Exception as e:
                print(f"Warning: Exception on cleanup DELETE request: {e}")


test_multi_turn_context_coreference_resolution()
