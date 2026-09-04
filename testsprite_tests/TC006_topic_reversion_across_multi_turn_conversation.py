import requests
import uuid
import time

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_topic_reversion_across_multi_turn_conversation():
    # We simulate a multi-turn conversation where we begin on one topic,
    # switch to another topic, then explicitly request to revert back to the original topic.
    # The system should restore the earlier topic and continue the conversation coherently.

    # Step 1: Start a new conversation with an initial query on a topic, e.g., "price tampering"
    initial_query = "Can you explain how price tampering is detected in AgentGuard?"
    user_id = str(uuid.uuid4())

    response1 = requests.post(
        BASE_URL,
        json={"query": initial_query, "user_id": user_id},
        timeout=TIMEOUT,
    )
    assert response1.status_code == 200, f"Unexpected status code: {response1.status_code}"
    resp1_json = response1.json()
    assert resp1_json.get("success") is True, "Initial query did not succeed"
    data1 = resp1_json.get("data", {})
    session_id = data1.get("session_id")
    assert session_id, "No session_id returned on initial query"
    turn_id_1 = data1.get("turn_id")
    assert isinstance(turn_id_1, int) and turn_id_1 > 0, "Invalid turn_id in initial query response"
    intent_1 = data1.get("intent")
    message_1 = data1.get("message")
    assert isinstance(message_1, str) and len(message_1) > 0, "Empty message in initial response"

    # Step 2: Follow-up query switching to a different topic, e.g., "replay attacks"
    second_query = "What about replay attacks? How do they work?"
    response2 = requests.post(
        BASE_URL,
        json={"query": second_query, "session_id": session_id, "user_id": user_id},
        timeout=TIMEOUT,
    )
    assert response2.status_code == 200, f"Unexpected status code: {response2.status_code}"
    resp2_json = response2.json()
    assert resp2_json.get("success") is True, "Second query did not succeed"
    data2 = resp2_json.get("data", {})
    turn_id_2 = data2.get("turn_id")
    assert isinstance(turn_id_2, int) and turn_id_2 > turn_id_1, "Turn ID did not increment for second query"
    intent_2 = data2.get("intent")
    message_2 = data2.get("message")
    assert isinstance(message_2, str) and len(message_2) > 0, "Empty message in second response"
    # Confirm topic shifted to replay attacks or related intent
    assert intent_2 and ("replay" in intent_2.lower() or "attack" in intent_2.lower()) or "replay" in message_2.lower()

    # Step 3: Explicitly request to revert back or return to the original topic ("price tampering")
    revert_query = "Can we go back to price tampering and continue?"
    response3 = requests.post(
        BASE_URL,
        json={"query": revert_query, "session_id": session_id, "user_id": user_id},
        timeout=TIMEOUT,
    )
    assert response3.status_code == 200, f"Unexpected status code: {response3.status_code}"
    resp3_json = response3.json()
    assert resp3_json.get("success") is True, "Topic revert query did not succeed"
    data3 = resp3_json.get("data", {})
    turn_id_3 = data3.get("turn_id")
    assert isinstance(turn_id_3, int) and turn_id_3 > turn_id_2, "Turn ID did not increment for revert query"
    intent_3 = data3.get("intent")
    message_3 = data3.get("message")
    assert isinstance(message_3, str) and len(message_3) > 0, "Empty message in topic revert response"
    # Check if the restored topic/message is about price tampering again
    assert "price tampering" in message_3.lower() or ("price" in intent_3.lower() if intent_3 else False)

    # Validate that dialogue_act, evidence_citations, and suggested_followups exist and are well-formed in the last response
    assert "dialogue_act" in data3 and isinstance(data3["dialogue_act"], str)
    assert "evidence_citations" in data3 and isinstance(data3["evidence_citations"], list)
    assert "suggested_followups" in data3 and isinstance(data3["suggested_followups"], list)

test_topic_reversion_across_multi_turn_conversation()