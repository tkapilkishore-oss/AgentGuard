import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_typo_and_informal_language_robustness():
    # Sample inputs with common typos, informal abbreviations, punctuation irregularities, ungrammatical questions
    test_queries = [
        "wht is price tamprng?",               # typo: "what", "tampering"
        "How r replay attacs detected...",     # informal abbreviation "r" for "are", typo "attacs"
        "Tell me abt the mandates budgt pls", # informal abbreviations "abt", "budgt", informal "pls"
        "Can you explain sha 256 verifyin?",  # missing punctuation, typo "verifyin"
        "price tampering how it work?",       # ungrammatical question
        "Replay attacks, detection? pls expln", # punctuation irregularities and informal "pls", "expln"
    ]

    session_id = None
    user_id = str(uuid.uuid4())

    try:
        # Create initial session by sending first query
        initial_payload = {
            "query": test_queries[0],
            "user_id": user_id
        }
        response = requests.post(BASE_URL, json=initial_payload, timeout=TIMEOUT)
        assert response.status_code == 200, f"Unexpected status code on initial query: {response.status_code}"
        resp_json = response.json()
        assert resp_json.get("success") is True, "API did not return success on initial query"
        session_id = resp_json.get("data", {}).get("session_id")
        assert session_id, "No session_id returned on initial query"

        # For each additional test query, send with session_id to maintain context
        for q in test_queries[1:]:
            payload = {
                "query": q,
                "session_id": session_id,
                "user_id": user_id
            }
            resp = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert resp.status_code == 200, f"Unexpected status code for query '{q}': {resp.status_code}"

            resp_body = resp.json()
            assert resp_body.get("success") is True, f"API responded with failure for query '{q}'"
            data = resp_body.get("data", {})
            message = data.get("message", "")
            intent = data.get("intent", "")
            dialogue_act = data.get("dialogue_act", "")
            error = resp_body.get("error")

            # Validate that the response message is not a generic fallback or failure message
            assert message and not ("Sorry" in message or "I don't understand" in message or "fallback" in message.lower()), \
                f"Unhelpful fallback message received for query '{q}': {message}"

            # Validate no error object is returned or is empty
            assert not error or error == {}, f"Error object present in response for query '{q}': {error}"

            # Basic validation that intent and dialogue_act are non-empty strings
            assert isinstance(intent, str) and intent.strip() != "", f"Invalid intent for query '{q}'"
            assert isinstance(dialogue_act, str) and dialogue_act.strip() != "", f"Invalid dialogue_act for query '{q}'"

    finally:
        # Cleanup: attempt to delete the session to reset conversation state
        if session_id:
            try:
                del_url = f"http://localhost:8000/conversational/session/{session_id}"
                del_resp = requests.delete(del_url, timeout=TIMEOUT)
                # status code 200 expected for successful reset; ignore else quietly
                if del_resp.status_code != 200:
                    pass
            except Exception:
                pass

test_typo_and_informal_language_robustness()