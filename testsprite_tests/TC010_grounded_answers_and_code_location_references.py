import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_tc010_grounded_answers_and_code_location_references():
    query_text = (
        "Where are the specific security checks and protections implemented "
        "in the codebase? Please provide grounded references like backend/app/policy/engine.py, "
        "backend/app/api/execute.py, backend/app/services/audit_log.py."
    )

    payload = {
        "query": query_text,
        # "session_id" and "user_id" omitted to create a new session
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            BASE_URL,
            json=payload,
            headers=headers,
            timeout=TIMEOUT,
        )
        assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}"
        json_resp = response.json()
        assert json_resp.get("success") is True, "Response success flag is not true"
        data = json_resp.get("data")
        assert data is not None, "Response missing 'data' field"
        session_id = data.get("session_id")
        turn_id = data.get("turn_id")
        message = data.get("message")
        intent = data.get("intent")
        evidence_citations = data.get("evidence_citations")
        # Validate that session_id is returned and is non-empty string
        assert isinstance(session_id, str) and session_id.strip(), "Invalid or missing session_id"
        # Validate turn_id is int and >= 1
        assert isinstance(turn_id, int) and turn_id >= 1, "Invalid turn_id"
        # Validate message is a non-empty string
        assert isinstance(message, str) and message.strip(), "Missing or empty message"
        # Validate intent is string and relevant to code location references
        assert isinstance(intent, str) and intent.strip(), "Missing or empty intent"
        # Validate evidence_citations includes expected code file references
        assert isinstance(evidence_citations, list), "evidence_citations should be a list"
        expected_files = [
            "backend/app/policy/engine.py",
            "backend/app/api/execute.py",
            "backend/app/services/audit_log.py"
        ]
        # Check that at least one expected file reference is mentioned in citations
        found_reference = any(
            any(ef in str(citation) for ef in expected_files) for citation in evidence_citations
        )
        assert found_reference, f"Expected code location references not found in evidence_citations: {expected_files}"
        # Optionally check the grounded nature by presence of filesystem-like paths in message
        found_path_in_message = any(ef in message for ef in expected_files)
        assert found_path_in_message, "Expected code location paths not found in message text"
    finally:
        # Cleanup: reset the session by DELETE /conversational/session/{session_id}
        if 'session_id' in locals() and session_id:
            reset_url = f"http://localhost:8000/conversational/session/{session_id}"
            try:
                resp_del = requests.delete(reset_url, timeout=TIMEOUT)
                # Accept both success and 'already reset' error responses gracefully
                assert resp_del.status_code in (200, 404)
            except Exception:
                pass

test_tc010_grounded_answers_and_code_location_references()