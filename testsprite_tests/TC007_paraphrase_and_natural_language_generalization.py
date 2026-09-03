import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_paraphrase_and_natural_language_generalization():
    paraphrased_queries = [
        "How does the system prevent duplicate transaction submissions?",
        "Can you explain the mechanism for repeat payment protection?",
        "What are the safeguards against replay attacks?",
        "Tell me about protections that stop submitting the same payment twice.",
        "How is transaction replay prevented in the system?"
    ]

    user_id = str(uuid.uuid4())
    session_id = None

    try:
        for idx, query_text in enumerate(paraphrased_queries):
            payload = {
                "query": query_text,
                "session_id": session_id if session_id else "",
                "user_id": user_id
            }
            response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"Unexpected status code {response.status_code} for query '{query_text}'"
            resp_json = response.json()

            # Validate top level response structure
            assert "success" in resp_json and resp_json["success"] is True, f"Request not successful for query '{query_text}'"
            assert "data" in resp_json, f"No data field in response for query '{query_text}'"

            data = resp_json["data"]
            # Validate required fields presence and types
            assert "session_id" in data and isinstance(data["session_id"], str) and data["session_id"], "Missing or invalid session_id"
            assert "turn_id" in data and isinstance(data["turn_id"], int) and data["turn_id"] > 0, "Missing or invalid turn_id"
            assert "message" in data and isinstance(data["message"], str) and len(data["message"].strip()) > 0, "Missing or empty message"
            assert "intent" in data and isinstance(data["intent"], str) and data["intent"], "Missing or invalid intent"
            assert "dialogue_act" in data and isinstance(data["dialogue_act"], str) and data["dialogue_act"], "Missing dialogue_act"
            assert "evidence_citations" in data and isinstance(data["evidence_citations"], list), "Missing or invalid evidence_citations"

            # Validate the answer is relevant and coherent:
            # Check that the message contains terms related to security mechanisms indicated by the query paraphrases
            keywords = ["duplicate", "repeat", "replay", "transaction", "protection", "prevention", "mechanism", "safeguard"]
            message_lower = data["message"].lower()
            assert any(k in message_lower for k in keywords), f"Response message does not address security mechanism for query '{query_text}'"

            # For first iteration, capture session_id to use for follow-ups
            if idx == 0:
                session_id = data["session_id"]

    finally:
        # No session reset or deletion endpoint for sessions explicitly,
        # but if it existed we would clean up here if needed.
        pass

test_paraphrase_and_natural_language_generalization()
