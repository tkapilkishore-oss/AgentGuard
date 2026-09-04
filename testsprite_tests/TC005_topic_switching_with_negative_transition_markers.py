import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_topic_switching_with_negative_transition_markers():
    headers = {"Content-Type": "application/json"}
    user_id = "test_user_tc005"

    # Initial query to start a topic
    initial_query = "Tell me about price tampering in AgentGuard."
    payload = {"query": initial_query, "user_id": user_id}
    try:
        resp = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        json_resp = resp.json()

        assert json_resp.get("success") is True, "Initial query failed"
        data = json_resp.get("data", {})
        session_id = data.get("session_id")
        assert session_id, "No session_id returned from initial query"
        turn_id_1 = data.get("turn_id")
        message_1 = data.get("message", "")
        intent_1 = data.get("intent", "")

        # Negative transition markers queries with explicit destination topics:
        negative_markers = [
            "Forget that. Tell me about replay attacks.",
            "Never mind about price tampering, can you explain forensic ledger?",
            "Instead of replay attacks tell me about mandate budget.",
            "Let's move away from forensic ledger and talk about audit trail."
        ]

        expected_new_topics = [
            "replay attacks",
            "forensic ledger",
            "mandate budget",
            "audit trail"
        ]

        expected_canonical_topics = [
            "REPLAY_ATTACK",
            "FORENSIC_LEDGER",
            "MANDATE_BUDGET",
            "AUDIT_TRAIL"
        ]

        for idx, query in enumerate(negative_markers):
            payload_followup = {"query": query, "session_id": session_id, "user_id": user_id}
            resp_followup = requests.post(BASE_URL, json=payload_followup, headers=headers, timeout=TIMEOUT)
            resp_followup.raise_for_status()
            json_followup = resp_followup.json()

            assert json_followup.get("success") is True, f"Pivot query '{query}' failed"
            data_followup = json_followup.get("data", {})
            assert data_followup.get("session_id") == session_id, "Session ID changed unexpectedly"
            turn_id = data_followup.get("turn_id")
            message = data_followup.get("message", "")
            intent = data_followup.get("intent", "")
            trace = data_followup.get("trace", {})

            # Validate turn_id increments properly
            assert isinstance(turn_id, int) and turn_id > turn_id_1, "Turn ID did not increment after pivot"
            turn_id_1 = turn_id

            # Validate that the new destination topic becomes active / is correctly represented
            lower_message = message.lower()
            topic_matched = (
                expected_new_topics[idx] in intent.lower()
                or expected_new_topics[idx] in lower_message
                or trace.get("canonical_topic") == expected_canonical_topics[idx]
                or any(w in lower_message for w in expected_new_topics[idx].split())
            )
            assert topic_matched, f"Destination topic '{expected_new_topics[idx]}' was not addressed after pivot '{query}'"

    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"
    except AssertionError as e:
        assert False, f"Assertion failed: {e}"

test_topic_switching_with_negative_transition_markers()