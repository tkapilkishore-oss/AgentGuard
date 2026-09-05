import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_basic_intent_recognition_and_natural_phrasings():
    queries = [
        "Can you explain price tampering and how it is detected?",
        "What are replay attacks and their risks?",
        "Tell me about the mandate budget and any recent changes.",
        "How does the forensic ledger ensure data integrity?",
        "Explain the audit trail and its importance in security.",
        "What role does SHA-256 verification play in AgentGuard?"
    ]
    
    for query in queries:
        try:
            payload = {"query": query}
            response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
            assert response.status_code == 200, f"HTTP {response.status_code} returned for query: {query}"
            resp_json = response.json()
            assert resp_json.get("success") is True, f"Request failed for query: {query}"
            data = resp_json.get("data")
            assert data is not None, f"No data in response for query: {query}"
            # Validate required fields exist and types
            assert isinstance(data.get("session_id"), str) and data.get("session_id"), "Invalid or missing session_id"
            assert isinstance(data.get("turn_id"), int), "turn_id missing or not int"
            assert isinstance(data.get("message"), str) and data.get("message"), "Missing or empty message"
            assert isinstance(data.get("intent"), str) and data.get("intent"), "Missing or empty intent"
            assert isinstance(data.get("dialogue_act"), str), "Missing dialogue_act"
            # evidence_citations should be a list and should have at least one citation
            citations = data.get("evidence_citations")
            assert isinstance(citations, list), "evidence_citations is not a list"
            assert len(citations) > 0, "No evidence citations returned"
            # Ensure message and citations are semantically relevant to the query by checking keywords presence
            keywords = ["price tampering", "replay attacks", "mandate budget", "forensic ledger", "audit trail", "sha-256"]
            lowered = query.lower()
            matched_kw = [kw for kw in keywords if kw in lowered]
            found_in_response = any(kw in data.get("message").lower() for kw in matched_kw)
            assert found_in_response, f"Response message does not reference core topic for query: {query}"
            # error key presence
            assert "error" in resp_json, "Missing error in response"
            # error should be None or empty dict if success true
            error = resp_json.get("error")
            assert error in (None, {}, []), f"Unexpected error in response: {error}"
        except (requests.RequestException, AssertionError) as e:
            raise AssertionError(f"Test failed for query '{query}': {e}")

test_basic_intent_recognition_and_natural_phrasings()