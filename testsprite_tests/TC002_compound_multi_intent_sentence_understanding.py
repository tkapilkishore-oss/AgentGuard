import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_TC002_compound_multi_intent_sentence_understanding():
    # Compound multi-intent sentence with connectors 'and', 'also', 'but', 'while', 'plus'
    query_text = (
        "Can you explain the impact of price tampering and how live protection affects it, "
        "also what is the current budget? But please include details while referencing detection methods plus timing considerations."
    )
    user_id = str(uuid.uuid4())

    payload = {
        "query": query_text,
        "user_id": user_id
    }

    try:
        response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Validate top level success
        assert data.get("success") is True, "Response success flag is not True."

        resp_data = data.get("data")
        assert resp_data is not None, "Response missing 'data' field."

        # Validate presence of session_id and turn_id
        session_id = resp_data.get("session_id")
        turn_id = resp_data.get("turn_id")
        assert isinstance(session_id, str) and session_id, "Missing or invalid session_id."
        assert isinstance(turn_id, int) and turn_id > 0, "Missing or invalid turn_id."

        # Validate message is non-empty string
        message = resp_data.get("message")
        assert isinstance(message, str) and message.strip(), "Response message is empty or missing."

        # Validate intent is a non-empty string (relaxed)
        intent = resp_data.get("intent")
        assert isinstance(intent, str) and intent.strip(), "Response intent is missing or empty."

        # Validate evidence_citations is an array (can be empty)
        evidence_citations = resp_data.get("evidence_citations")
        assert isinstance(evidence_citations, list), "evidence_citations is not a list."

        # Validate suggested_followups is an array (can be empty)
        suggested_followups = resp_data.get("suggested_followups")
        assert isinstance(suggested_followups, list), "suggested_followups is not a list."

        # Validate no error object or it's empty
        error = data.get("error")
        assert not error or error == {} or error is None, f"Unexpected error response: {error}"

        # Since this is multi-intent query, check that trace or message does not indicate dropped intents (basic heuristic)
        trace = resp_data.get("trace")
        if trace and isinstance(trace, dict):
            dropped_intents = trace.get("dropped_intents", False)
            assert not dropped_intents, "Secondary intents were dropped according to trace."

    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"
    except ValueError as e:
        assert False, f"Invalid JSON response: {e}"

test_TC002_compound_multi_intent_sentence_understanding()