import requests
import uuid

BASE_URL = "http://localhost:8000"
QUERY_ENDPOINT = f"{BASE_URL}/conversational/query"
TIMEOUT = 30


def test_live_state_query_routing_and_authoritative_data_accuracy():
    session_id = None
    user_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json"
    }

    # Test queries targeting live state data
    live_state_queries = [
        # Current budget query which should reflect live database state (expecting live_data_used==True)
        "What is the current budget for mandate-001?",
        # Product catalog prices query
        "Show me the prices for the product catalog items currently available.",
        # Forensic ledger transaction counts
        "How many transactions are recorded in the forensic ledger right now?",
        # Mandate status query
        "What is the current status of mandate-001?",
        # Combined live queries
        "Tell me the current budget, product catalog prices, and forensic ledger transaction counts."
    ]

    try:
        for idx, query_text in enumerate(live_state_queries):
            payload = {
                "query": query_text
            }
            # Use session_id if available to simulate multi-turn context; on first query session_id absent
            if session_id:
                payload["session_id"] = session_id
            payload["user_id"] = user_id

            response = requests.post(QUERY_ENDPOINT, json=payload, headers=headers, timeout=TIMEOUT)
            assert response.status_code == 200, f"HTTP status code not 200 for query {idx + 1}"
            resp_json = response.json()

            # Assert success true
            assert resp_json.get("success") is True, f"API returned success=False for query {idx + 1}"

            data = resp_json.get("data")
            assert data, f"No data found in response for query {idx + 1}"

            # Validate mandatory fields presence and types
            assert isinstance(data.get("session_id"), str) and data.get("session_id"), f"Invalid session_id in query {idx + 1}"
            assert isinstance(data.get("turn_id"), int), f"Invalid turn_id in query {idx + 1}"
            assert isinstance(data.get("message"), str) and data.get("message"), f"Empty message in query {idx + 1}"
            assert isinstance(data.get("intent"), str) and data.get("intent"), f"Empty intent in query {idx + 1}"
            assert isinstance(data.get("dialogue_act"), str) and data.get("dialogue_act"), f"Empty dialogue_act in query {idx + 1}"
            assert isinstance(data.get("evidence_citations"), list), f"evidence_citations not a list for query {idx + 1}"
            assert isinstance(data.get("live_data_used"), bool), f"live_data_used missing or not bool for query {idx + 1}"
            assert isinstance(data.get("live_readings"), dict), f"live_readings missing or not dict for query {idx + 1}"

            # For this test case, live_data_used must be True meaning routed to live PostgreSQL data
            assert data["live_data_used"] is True, f"live_data_used is not True for query {idx + 1}"

            # live_readings should contain relevant keys depending on query
            # Use simple heuristics to check keys presence

            if "budget" in query_text.lower():
                assert "current_budget" in data["live_readings"], "live_readings missing current_budget for budget query"
            if "price" in query_text.lower():
                # Accept either 'product_catalog_prices' or 'product_catalog_price' keys
                assert ("product_catalog_prices" in data["live_readings"]
                        or "product_catalog_price" in data["live_readings"]), "live_readings missing product_catalog_prices for product catalog query"
            if "forensic ledger" in query_text.lower():
                assert "forensic_ledger_transaction_count" in data["live_readings"], "live_readings missing forensic_ledger_transaction_count for forensic ledger query"
            if "mandate status" in query_text.lower() or "status of mandate" in query_text.lower():
                assert "mandate_status" in data["live_readings"], "live_readings missing mandate_status for mandate status query"

            # Refined combined live query check condition to avoid false triggers
            if ("current budget" in query_text.lower() and "prices" in query_text.lower()
                and "forensic ledger" in query_text.lower() and "mandate" not in query_text.lower()):
                # Expect keys for combined queries that mention all 3
                required_keys = {"current_budget", "product_catalog_prices", "forensic_ledger_transaction_count"}
                missing_keys = required_keys - data["live_readings"].keys()
                assert not missing_keys, f"live_readings missing keys {missing_keys} for combined live query"

            # Additionally handle combined query that explicitly mentions all keys (including mandate_status)
            if ("current budget" in query_text.lower() and "prices" in query_text.lower()
                and "forensic ledger" in query_text.lower() and "mandate status" in query_text.lower()):
                required_keys = {"current_budget", "product_catalog_prices", "forensic_ledger_transaction_count", "mandate_status"}
                missing_keys = required_keys - data["live_readings"].keys()
                assert not missing_keys, f"live_readings missing keys {missing_keys} for full combined live query"

            # Capture session_id from first response to reuse in subsequent queries
            if session_id is None:
                session_id = data["session_id"]

    finally:
        if session_id:
            # Cleanup: reset session to clear conversational context after test
            reset_url = f"{BASE_URL}/conversational/session/{session_id}"
            try:
                reset_response = requests.delete(reset_url, timeout=TIMEOUT)
                assert reset_response.status_code == 200, "Failed to reset session after test"
                reset_json = reset_response.json()
                assert reset_json.get("success") is True, "Reset session success false"
                assert reset_json.get("data", {}).get("session_id") == session_id, "Reset session_id mismatch"
                assert reset_json.get("data", {}).get("status") == "reset", "Unexpected reset status message"
            except Exception as e:
                # In case session reset fails, just print but do not raise to avoid masking original test outcome
                print(f"Warning: Exception during session reset cleanup: {e}")


test_live_state_query_routing_and_authoritative_data_accuracy()
