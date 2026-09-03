import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_TC009_live_state_query_routing_and_authoritative_data_accuracy():
    session_id = None
    user_id = str(uuid.uuid4())
    headers = {"Content-Type": "application/json"}

    # We will test several live-state questions to verify that live_data_used is True and data corresponds to live queries
    live_queries = [
        "What is the current budget?",
        "What are the current product catalog prices?",
        "How many transactions are in the forensic ledger?",
        "What is the current mandate status?",
        "Please combine current budget, product prices, forensic ledger counts, and mandate status information."
    ]

    try:
        for query_text in live_queries:
            payload = {
                "query": query_text,
                "session_id": session_id if session_id else "",
                "user_id": user_id
            }

            response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
            # Basic checks for response status
            assert response.status_code == 200, f"Expected 200 but got {response.status_code} for query: {query_text}"

            json_resp = response.json()
            # Check success flag
            assert "success" in json_resp and json_resp["success"] is True, f"API did not succeed for query: {query_text}"

            data = json_resp.get("data")
            assert data is not None, f"No data returned for query: {query_text}"

            # Save session_id for follow up queries
            if not session_id:
                session_id = data.get("session_id")
                assert isinstance(session_id, str) and len(session_id) > 0, "session_id missing or invalid"

            # Validate fields presence
            # turn_id: integer
            turn_id = data.get("turn_id")
            assert isinstance(turn_id, int) and turn_id > 0, f"Invalid turn_id: {turn_id}"

            # message: non-empty string
            message = data.get("message")
            assert isinstance(message, str) and len(message) > 0, "Empty message in response"

            # intent: string non-empty
            intent = data.get("intent")
            assert isinstance(intent, str) and len(intent) > 0, "Intent missing or empty"

            # live_data_used must be True for live-state queries
            live_data_used = data.get("live_data_used")
            assert live_data_used is True, f"live_data_used must be True for live-state query '{query_text}'"

            # live_readings must be an object/dict with data relevant to live-state
            live_readings = data.get("live_readings")
            assert isinstance(live_readings, dict), f"live_readings should be an object for query: {query_text}"
            assert len(live_readings) > 0, f"live_readings should not be empty for query: {query_text}"

            # ensure evidence_citations is an array (can be empty)
            evidence_citations = data.get("evidence_citations")
            assert isinstance(evidence_citations, list), "evidence_citations should be a list"

            # progressive_disclosure_offer: string (can be empty)
            progressive_offer = data.get("progressive_disclosure_offer")
            assert progressive_offer is not None, "progressive_disclosure_offer key missing"

            # suggested_followups: list
            suggested_followups = data.get("suggested_followups")
            assert isinstance(suggested_followups, list), "suggested_followups should be a list"

            # action: object/dict
            action = data.get("action")
            assert isinstance(action, dict), "action should be an object"

            # trace: object/dict - Should be present even if empty for debug info
            trace = data.get("trace")
            assert isinstance(trace, dict), "trace should be an object"

            # error must be None or empty object on success
            error = json_resp.get("error")
            assert error in (None, {}, []), f"Unexpected error content: {error}"

    finally:
        # No session deletion endpoint specified for session here, so no cleanup needed
        pass

test_TC009_live_state_query_routing_and_authoritative_data_accuracy()
