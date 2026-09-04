import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_TC010_grounded_answers_and_code_location_references():
    query_text = (
        "Where are the security checks and protections implemented in the code? "
        "Please provide grounded code references and architectural locations such as "
        "backend/app/policy/engine.py, backend/app/api/execute.py, backend/app/services/audit_log.py."
    )
    payload = {
        "query": query_text,
        "session_id": "",
        "user_id": "test_user_010"
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        resp_json = response.json()

        # Basic success check
        assert resp_json.get("success") is True, "API did not indicate success."

        data = resp_json.get("data")
        assert data, "Response data is missing."

        # Validate presence of required fields
        session_id = data.get("session_id")
        turn_id = data.get("turn_id")
        message = data.get("message")
        intent = data.get("intent")
        dialogue_act = data.get("dialogue_act")
        evidence_citations = data.get("evidence_citations")

        assert isinstance(session_id, str) and len(session_id) > 0, "Invalid or missing session_id."
        assert isinstance(turn_id, int) and turn_id > 0, "Invalid or missing turn_id."
        assert isinstance(message, str) and len(message) > 0, "Empty message in response."
        assert isinstance(intent, str) and len(intent) > 0, "Intent not resolved."
        assert isinstance(dialogue_act, str) and len(dialogue_act) > 0, "Dialogue act missing."
        assert isinstance(evidence_citations, list) and len(evidence_citations) > 0, "No evidence citations provided."

        # Check that indicated architectural locations appear in message or citations
        expected_files = [
            "backend/app/policy/engine.py",
            "backend/app/api/execute.py",
            "backend/app/services/audit_log.py"
        ]

        # Lowercase all to make search case-insensitive
        message_lower = message.lower()
        citations_lower = [str(cit).lower() for cit in evidence_citations]

        found_files = [f for f in expected_files if any(f.lower() in message_lower or f.lower() in cit for cit in citations_lower)]
        assert len(found_files) >= len(expected_files) - 1, (
            "Most expected architectural code references were not found in message or evidence_citations."
        )

        # Verify no error returned
        assert resp_json.get("error") in (None, {}, []), f"Unexpected error in response: {resp_json.get('error')}"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_TC010_grounded_answers_and_code_location_references()