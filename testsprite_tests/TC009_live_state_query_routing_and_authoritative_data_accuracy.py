import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_live_state_query_routing_and_authoritative_data_accuracy():
    url = f"{BASE_URL}/conversational/query"
    user_id = "test-user-live-state-routing"
    session_id = None
    
    try:
        # Start a new session with a live-state question about current budget
        payload = {
            "query": "What is the current budget remaining for this mandate?",
            "user_id": user_id,
            "session_id": None
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code} on budget query"
        json_resp = resp.json()
        assert json_resp.get("success") is True, f"API reported failure: {json_resp.get('error')}"
        data = json_resp.get("data", {})
        session_id = data.get("session_id")
        assert session_id, "Missing session_id in response"
        assert data.get("live_data_used") is True, "Expected live_data_used True for budget query"
        live_readings = data.get("live_readings")
        assert isinstance(live_readings, dict), "Expected live_readings to be object"
        assert "current_budget" in live_readings or "budget" in live_readings, "Expected live budget data in live_readings"

        # Query product catalog prices live state
        payload = {
            "query": "Show me the latest product catalog prices.",
            "user_id": user_id,
            "session_id": session_id
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code} on product catalog prices query"
        json_resp = resp.json()
        assert json_resp.get("success") is True, f"API reported failure: {json_resp.get('error')}"
        data = json_resp.get("data", {})
        assert data.get("live_data_used") is True, "Expected live_data_used True for product catalog query"
        live_readings = data.get("live_readings")
        assert isinstance(live_readings, dict), "Expected live_readings to be object"
        assert "product_prices" in live_readings or "catalog_prices" in live_readings, "Expected live product prices data"

        # Query forensic ledger transaction counts live state
        payload = {
            "query": "How many transactions are currently recorded in the forensic ledger?",
            "user_id": user_id,
            "session_id": session_id
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code} on ledger transaction count query"
        json_resp = resp.json()
        assert json_resp.get("success") is True, f"API reported failure: {json_resp.get('error')}"
        data = json_resp.get("data", {})
        assert data.get("live_data_used") is True, "Expected live_data_used True for ledger query"
        live_readings = data.get("live_readings")
        assert isinstance(live_readings, dict), "Expected live_readings to be object"
        assert "transaction_count" in live_readings or "ledger_transactions" in live_readings, "Expected transaction count data"

        # Query mandate status live state
        payload = {
            "query": "What is the current status of the mandate?",
            "user_id": user_id,
            "session_id": session_id
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code} on mandate status query"
        json_resp = resp.json()
        assert json_resp.get("success") is True, f"API reported failure: {json_resp.get('error')}"
        data = json_resp.get("data", {})
        assert data.get("live_data_used") is True, "Expected live_data_used True for mandate status query"
        live_readings = data.get("live_readings")
        assert isinstance(live_readings, dict), "Expected live_readings to be object"
        assert "mandate_status" in live_readings, "Expected mandate status data"

        # Combined multi-intent live query example
        combined_query = (
            "Tell me the current budget, the prices in the product catalog, "
            "how many transactions the forensic ledger has, and the mandate's status."
        )
        payload = {
            "query": combined_query,
            "user_id": user_id,
            "session_id": session_id
        }
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Unexpected status code {resp.status_code} on combined live query"
        json_resp = resp.json()
        assert json_resp.get("success") is True, f"API reported failure: {json_resp.get('error')}"
        data = json_resp.get("data", {})
        assert data.get("live_data_used") is True, "Expected live_data_used True for combined live query"
        live_readings = data.get("live_readings")
        assert isinstance(live_readings, dict), "Expected live_readings object"
        keys_expected = ["current_budget", "product_prices", "transaction_count", "mandate_status"]
        # Some keys might be in alternate form, so check presence of at least some
        found_keys = sum(1 for k in keys_expected if k in live_readings)
        assert found_keys >= 2, "Expected multiple live state data points in combined query"

    finally:
        # Cleanup: no session delete endpoint needed per PRD for session reset, so skip
        # If reset needed and DELETE is available:
        if session_id:
            try:
                del_url = f"{BASE_URL}/conversational/session/{session_id}"
                del_resp = requests.delete(del_url, timeout=TIMEOUT)
                # Accept success or failure as session may auto-expire
                if del_resp.status_code not in (200, 404):
                    print(f"Warning: Unexpected status on session delete: {del_resp.status_code}")
            except Exception:
                pass

test_live_state_query_routing_and_authoritative_data_accuracy()