import requests

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30

def test_TC002_compound_multi_intent_sentence_understanding():
    """
    Verify that POST /conversational/query extracts and addresses all meaningful clauses
    in compound multi-intent sentences connected by 'and', 'also', 'but', 'while', 'plus'
    without dropping secondary intents.
    """
    query_text = (
        "Can you explain price tampering concerns and also how live protection impacts detection "
        "while considering our current budget plus the implications on replay protection?"
    )
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "query": query_text,
        "user_id": "test-user-001"
    }

    try:
        response = requests.post(BASE_URL, json=payload, headers=headers, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        resp_json = response.json()
        assert resp_json.get("success") is True, "Response success flag is not True"

        data = resp_json.get("data")
        assert data is not None, "Response JSON missing 'data' field"

        # Validate session_id presence
        session_id = data.get("session_id")
        assert isinstance(session_id, str) and session_id.strip() != "", "Invalid or missing session_id"

        # Validate turn_id is an integer and >= 1
        turn_id = data.get("turn_id")
        assert isinstance(turn_id, int) and turn_id >= 1, "Invalid or missing turn_id"

        # Validate message presence and non-empty string
        message = data.get("message")
        assert isinstance(message, str) and len(message) > 0, "Missing or empty message in response"

        # Validate intent is a non-empty string and includes multiple intents (basic check)
        intent = data.get("intent")
        assert isinstance(intent, str) and intent.strip() != "", "Missing or empty intent"

        # Validate dialogue_act presence
        dialogue_act = data.get("dialogue_act")
        assert isinstance(dialogue_act, str), "Missing dialogue_act"

        # Validate evidence_citations is a list (possibly empty but should exist)
        evidence_citations = data.get("evidence_citations")
        assert isinstance(evidence_citations, list), "evidence_citations should be a list"

        # Validate live_data_used is boolean
        live_data_used = data.get("live_data_used")
        assert isinstance(live_data_used, bool), "live_data_used should be boolean"

        # Validate suggested_followups is a list
        suggested_followups = data.get("suggested_followups")
        assert isinstance(suggested_followups, list), "suggested_followups should be a list"

        # Validate no error in response
        error = resp_json.get("error")
        assert error is None or error == {}, f"Unexpected error in response: {error}"

        # Validate that all major clauses of the compound request are addressed:
        # 1. Price tampering topic
        # 2. Budget / live-state data
        # 3. Protection / detection / defense mechanism
        # 4. Replay attacks / protection
        lower_message = message.lower()
        trace = data.get("trace", {})
        live_readings = data.get("live_readings", {})
        trace_str = str(trace).lower()

        # Clause 1: Price tampering
        has_price_tampering = (
            "price tampering" in lower_message
            or "price" in intent.lower()
            or trace.get("canonical_topic") == "PRICE_TAMPERING"
            or any("tampering" in str(c).lower() for c in evidence_citations)
        )
        assert has_price_tampering, "Response did not address the price tampering clause"

        # Clause 2: Budget / live state
        has_budget_clause = (
            "budget" in lower_message
            or "budget" in str(live_readings).lower()
            or trace.get("is_dynamic_live") is True
            or bool(live_readings)
        )
        assert has_budget_clause, "Response did not address the live mandate budget clause"

        # Clause 3: Protection / detection / defense mechanism
        defense_terms = [
            "firewall",
            "protection",
            "defense",
            "detection",
            "claim diff",
            "security",
            "validation",
            "catalog",
        ]
        has_defense_clause = (
            any(term in lower_message for term in defense_terms)
            or any(term in trace_str for term in ["protection", "detection", "defense", "validation"])
            or any(any(term in str(c).lower() for term in defense_terms) for c in evidence_citations)
        )
        assert has_defense_clause, "Response did not address the protection/detection clause"

        # Clause 4: Replay attacks / protection
        replay_terms = [
            "replay",
            "replay attacks",
            "replay prevention",
            "idempotency",
            "duplicate",
        ]
        has_replay_clause = (
            any(term in lower_message for term in replay_terms)
            or trace.get("canonical_topic") == "REPLAY_ATTACK"
        )
        assert has_replay_clause, "Response did not address the replay clause"

    except requests.RequestException as req_err:
        assert False, f"Request failed: {req_err}"
    except AssertionError:
        raise
    except Exception as ex:
        assert False, f"Unexpected error: {ex}"

test_TC002_compound_multi_intent_sentence_understanding()