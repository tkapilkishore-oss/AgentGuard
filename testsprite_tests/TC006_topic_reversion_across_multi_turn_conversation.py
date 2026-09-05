import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_TC006_topic_reversion_across_multi_turn_conversation():
    # Start a new conversation with an initial topic
    first_query = "Can you explain the price tampering issue?"
    payload = {"query": first_query}
    try:
        response1 = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
        response1.raise_for_status()
        data1 = response1.json()
        assert data1.get("success") is True, "Initial query unsuccessful"
        session_id = data1["data"].get("session_id")
        assert session_id, "No session_id returned"
        turn_id_1 = data1["data"].get("turn_id")
        intent_1 = data1["data"].get("intent")
        assert intent_1, "No intent resolved for first query"
        message_1 = data1["data"].get("message")
        assert message_1, "No message returned for first query"

        # Continue conversation with a follow-up query on a different topic
        second_query = "Now tell me about replay attacks."
        payload2 = {"query": second_query, "session_id": session_id}
        response2 = requests.post(BASE_URL, json=payload2, timeout=TIMEOUT)
        response2.raise_for_status()
        data2 = response2.json()
        assert data2.get("success") is True, "Second query unsuccessful"
        turn_id_2 = data2["data"].get("turn_id")
        assert turn_id_2 is not None and turn_id_2 > turn_id_1, "Turn id did not increment"
        intent_2 = data2["data"].get("intent")
        assert isinstance(intent_2, str) and intent_2, "Intent not resolved for second query"
        message_2 = data2["data"].get("message")
        assert message_2, "No message returned for second query"

        # Now revert back explicitly to the first topic (price tampering)
        third_query = "Go back to the price tampering discussion."
        payload3 = {"query": third_query, "session_id": session_id}
        response3 = requests.post(BASE_URL, json=payload3, timeout=TIMEOUT)
        response3.raise_for_status()
        data3 = response3.json()
        assert data3.get("success") is True, "Third (reversion) query unsuccessful"
        turn_id_3 = data3["data"].get("turn_id")
        assert turn_id_3 is not None and turn_id_3 > turn_id_2, "Turn id did not increment on reversion"
        intent_3 = data3["data"].get("intent")
        assert isinstance(intent_3, str) and intent_3, "Intent not resolved for third query"
        message_3 = data3["data"].get("message")
        assert message_3, "No message returned for reverted topic query"

        # Confirm dialogue_act and evidence_citations presence (optional ground check)
        dialogue_act_3 = data3["data"].get("dialogue_act")
        evidence_citations_3 = data3["data"].get("evidence_citations")
        assert dialogue_act_3 is not None, "No dialogue_act in reversion response"
        assert isinstance(evidence_citations_3, list), "Evidence citations missing or not a list"

    finally:
        # Cleanup not required because sessions are maintained server-side and no explicit delete endpoint given for session here
        pass


test_TC006_topic_reversion_across_multi_turn_conversation()
