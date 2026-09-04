import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_out_of_scope_domain_boundary_enforcement():
    out_of_scope_queries = [
        "What's the weather like today?",
        "Tell me a joke.",
        "Who won the game last night?",
        "Can you give me some general trivia?"
    ]

    for query in out_of_scope_queries:
        try:
            response = requests.post(
                BASE_URL,
                json={"query": query},
                timeout=TIMEOUT
            )
            response.raise_for_status()
        except requests.RequestException as e:
            assert False, f"HTTP request failed for query='{query}': {e}"

        resp_json = response.json()
        # Assert that the overall response success is True (200 and processed)
        assert resp_json.get("success") is True, f"API did not succeed for out-of-scope query='{query}'"

        data = resp_json.get("data")
        error = resp_json.get("error")

        # Validate no unauthorized action was taken
        assert error is None or error == {}, f"Unexpected error object returned: {error}"

        # Validate response fields exist as per schema
        assert data is not None and isinstance(data, dict), "Response 'data' missing or invalid."

        # Check that the query is politely refused / redirected
        message = data.get("message", "").lower()
        intent = data.get("intent", "").lower()
        dialogue_act = data.get("dialogue_act", "").lower()
        trace = data.get("trace", {})

        # Expected polite refusal to out-of-scope requests, or redirection to commerce firewall topics
        polite_indicators = [
            "sorry",
            "out of scope",
            "cannot answer",
            "not supported",
            "redirect",
            "commerce firewall",
            "agentguard"
        ]
        polite_found = any(word in message for word in polite_indicators) or \
                       any(word in intent for word in polite_indicators) or \
                       any(word in dialogue_act for word in polite_indicators)
        assert polite_found, f"Response did not politely identify out-of-scope domain for query='{query}'"

        # Trace should include error details for diagnostic but no unauthorized action
        assert isinstance(trace, dict), "Trace should be a dict."
        # If action present, it should be empty or null indicating no unauthorized action was triggered
        action = data.get("action")
        assert action is None or action == {} or action == [], "Unauthorized or unexpected action was triggered."

test_out_of_scope_domain_boundary_enforcement()