import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_out_of_scope_domain_boundary_enforcement():
    out_of_scope_queries = [
        "What's the weather like today?",
        "Tell me a joke.",
        "Who won the game last night in sports?",
        "Can you give me some general trivia?"
    ]

    for query in out_of_scope_queries:
        try:
            response = requests.post(
                BASE_URL,
                json={"query": query},
                timeout=TIMEOUT
            )
        except requests.RequestException as e:
            assert False, f"Request failed: {e}"

        assert response.status_code == 200, f"Expected HTTP 200 but got {response.status_code}"

        resp_json = response.json()
        # Basic success flag should be True as per PRD for out-of-scope safe refusal
        assert "success" in resp_json, "Response JSON missing 'success' field"
        assert resp_json["success"] is True, "Response success flag is not True"

        assert "data" in resp_json, "Response JSON missing 'data' field"
        data = resp_json["data"]
        assert "message" in data, "Response data missing 'message' field"
        # The message should politely identify it as out-of-scope or redirect to commerce firewall capabilities
        message = data["message"].lower()
        polite_phrases = [
            "sorry",
            "out of scope",
            "i can't answer",
            "redirect",
            "commerce firewall",
            "capabilities",
            "agentguard"
        ]
        assert any(phrase in message for phrase in polite_phrases), (
            "Response message does not politely identify out-of-scope domain or redirect user"
        )

        # Trace should be present (possibly containing error details)
        assert "trace" in data or "trace" in resp_json, "Response missing 'trace' field"

        # There should be no unauthorized action in action object
        if "action" in data and isinstance(data["action"], dict):
            assert not data["action"], "Unexpected actions present for out-of-scope query"

test_out_of_scope_domain_boundary_enforcement()