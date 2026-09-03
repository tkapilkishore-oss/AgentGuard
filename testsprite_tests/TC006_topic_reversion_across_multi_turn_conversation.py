import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_topic_reversion_across_multi_turn_conversation():
    user_id = str(uuid.uuid4())

    try:
        # Step 1: Start a new conversation on a topic (e.g., price tampering)
        initial_query = {
            "query": "Can you explain price tampering?",
            "user_id": user_id
        }
        resp1 = requests.post(BASE_URL, json=initial_query, timeout=TIMEOUT)
        assert resp1.status_code == 200
        json1 = resp1.json()
        assert json1.get("success") is True
        data1 = json1.get("data", {})
        session_id = data1.get("session_id")
        turn_id_1 = data1.get("turn_id")
        intent_1 = data1.get("intent")
        message_1 = data1.get("message")
        assert session_id and turn_id_1 is not None and intent_1 and message_1

        # Step 2: Switch topic to something else (e.g., replay attacks)
        second_query = {
            "query": "What about replay attacks?",
            "session_id": session_id,
            "user_id": user_id,
        }
        resp2 = requests.post(BASE_URL, json=second_query, timeout=TIMEOUT)
        assert resp2.status_code == 200
        json2 = resp2.json()
        assert json2.get("success") is True
        data2 = json2.get("data", {})
        turn_id_2 = data2.get("turn_id")
        intent_2 = data2.get("intent")
        message_2 = data2.get("message")
        assert turn_id_2 == turn_id_1 + 1
        assert intent_2 and message_2
        assert session_id == data2.get("session_id")

        # Step 3: Request to go back or return to the earlier topic ("price tampering")
        revert_query = {
            "query": "Can we go back to price tampering?",
            "session_id": session_id,
            "user_id": user_id,
        }
        resp3 = requests.post(BASE_URL, json=revert_query, timeout=TIMEOUT)
        assert resp3.status_code == 200
        json3 = resp3.json()
        assert json3.get("success") is True
        data3 = json3.get("data", {})
        turn_id_3 = data3.get("turn_id")
        intent_3 = data3.get("intent")
        message_3 = data3.get("message")
        assert turn_id_3 == turn_id_2 + 1
        assert intent_3 and message_3
        # Validate that the topic intent in the response matches the original topic (price tampering)
        # We allow partial/intuitive check that intent or message references price tampering
        price_tampering_lower = "price tampering"
        assert (
            price_tampering_lower in intent_3.lower()
            or price_tampering_lower in message_3.lower()
        )

    finally:
        # Cleanup: Delete the conversational session after test to avoid residue
        if 'session_id' in locals():
            reset_endpoint = f"http://localhost:8000/conversational/session/{session_id}"
            try:
                del_resp = requests.delete(reset_endpoint, timeout=TIMEOUT)
                # Not asserting delete resp to avoid test fail on cleanup
            except Exception:
                pass


test_topic_reversion_across_multi_turn_conversation()