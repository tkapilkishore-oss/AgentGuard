import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_ui_and_navigation_surface_recommendations():
    url = f"{BASE_URL}/conversational/query"

    payloads = [
        {"query": "Show me the UI navigation recommendations and action hints for the Forensic Ledger surface."},
        {"query": "What are the suggested UI actions for the Threat Lab application surface?"},
        {"query": "Give me navigation recommendations and structured action hints for Live Protection."}
    ]

    for payload in payloads:
        try:
            response = requests.post(url, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            assert False, f"Request failed: {e}"

        assert response.status_code == 200, f"Unexpected status code {response.status_code} for query: {payload['query']}"
        json_resp = response.json()

        assert "success" in json_resp, "Missing 'success' in response"
        assert json_resp["success"] is True, f"API reported failure for query: {payload['query']}"
        assert "data" in json_resp, "Missing 'data' in response"

        data = json_resp["data"]
        # Validate mandatory fields in data
        assert "session_id" in data and isinstance(data["session_id"], str) and data["session_id"], "Missing or invalid session_id"
        assert "turn_id" in data and isinstance(data["turn_id"], int), "Missing or invalid turn_id"
        assert "message" in data and isinstance(data["message"], str) and data["message"], "Missing or empty message"
        assert "intent" in data and isinstance(data["intent"], str) and data["intent"], "Missing or empty intent"
        assert "dialogue_act" in data and isinstance(data["dialogue_act"], str), "Missing or invalid dialogue_act"
        assert "action" in data and isinstance(data["action"], dict), "Missing or invalid action"
        assert "suggested_followups" in data and isinstance(data["suggested_followups"], list), "Missing or invalid suggested_followups"

        # Validate that action hints and UI/navigation recommendations appear relevant to requested surface
        # We'll check the query text is reflected in some parts of the message or action keys, indicating correct grounding.
        q_lower = payload["query"].lower()
        message_lower = data["message"].lower()

        # At least one of the expected surfaces present in message or action keys or suggested_followups
        matched_surface = False
        surfaces = ["forensic ledger", "threat lab", "live protection"]

        for surface in surfaces:
            if surface in q_lower:
                matched_surface = (
                    surface in message_lower or
                    any(surface in followup.lower() for followup in data["suggested_followups"]) or
                    any(surface in str(value).lower() for key, value in data["action"].items())
                )
                assert matched_surface, f"Response lacks expected UI navigation recommendations or action hints for '{surface}'."


test_ui_and_navigation_surface_recommendations()
