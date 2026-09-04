import requests
import uuid

BASE_URL = "http://localhost:8000/conversational/query"
TIMEOUT = 30


def test_conversational_filler_and_noise_filtering():
    # Example input with conversational filler, colloquialisms, hesitation, and informal preamble
    noisy_query = (
        "So, um, like, I was wondering kind of, you know, how does, uh, your system detect price tampering? "
        "I mean, what exactly goes on behind the scenes?"
    )
    user_id = str(uuid.uuid4())

    payload = {
        "query": noisy_query,
        "user_id": user_id
    }

    try:
        response = requests.post(BASE_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        resp_json = response.json()

        # Validate the generic success structure
        assert resp_json.get("success") is True, "API call unsuccessful"
        data = resp_json.get("data")
        assert data, "Response data is missing"

        # Validate fields presence and types
        # session_id as non-empty string
        session_id = data.get("session_id")
        assert isinstance(session_id, str) and session_id, "Invalid or missing session_id"

        # turn_id as integer >= 1
        turn_id = data.get("turn_id")
        assert isinstance(turn_id, int) and turn_id >= 1, "Invalid turn_id"

        # message exists and is non-empty string (the filtered, processed answer)
        message = data.get("message")
        assert isinstance(message, str) and message.strip(), "Empty or invalid message in response"

        # intent should be a non-empty string indicating recognized intent
        intent = data.get("intent")
        assert isinstance(intent, str) and intent.strip(), "Intent missing or invalid"

        # dialogue_act as non-empty string describing dialogue act
        dialogue_act = data.get("dialogue_act")
        assert isinstance(dialogue_act, str) and dialogue_act.strip(), "Dialogue act missing or invalid"

        # evidence_citations as a list (can be empty or with content)
        citations = data.get("evidence_citations")
        assert isinstance(citations, list), "Evidence citations not a list"

        # live_data_used as boolean
        live_data_used = data.get("live_data_used")
        assert isinstance(live_data_used, bool), "live_data_used not boolean"

        # progressive_disclosure_offer as string (could be empty)
        progressive_offer = data.get("progressive_disclosure_offer")
        assert progressive_offer is None or isinstance(progressive_offer, str), "Invalid progressive_disclosure_offer"

        # suggested_followups as list (can be empty)
        suggested_followups = data.get("suggested_followups")
        assert isinstance(suggested_followups, list), "Suggested followups not a list"

        # action as dict (can be empty object)
        action = data.get("action")
        assert isinstance(action, dict), "Action field not an object"

        # trace as dict (can be empty or with details)
        trace = data.get("trace")
        assert isinstance(trace, dict), "Trace field not an object"

        # error must be null or empty object on success
        error = resp_json.get("error")
        assert error in (None, {}, []), "Unexpected error content on successful response"

        # Crucial semantic validation for this test case:
        # Check the message for absence of filler words/phrases and presence of technical answer keywords.
        # Since this is a test, check that common fillers do NOT appear in the response message
        fillers = ["um", "like", "you know", "uh", "I mean", "so,", "kind of"]
        message_lower = message.lower()
        for filler in fillers:
            assert filler not in message_lower, f"Filler phrase '{filler}' found in response message"

        # Check presence of keywords relevant to 'price tampering' detection response
        # Since we do not know exact answer wording, just check some typical concepts appear:
        keywords = ["detect", "price tampering", "verification", "checks", "integrity", "monitor", "protection", "attack"]
        assert any(keyword in message_lower for keyword in keywords), (
            "Response message does not contain core technical keywords expected for price tampering detection"
        )

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    except AssertionError:
        raise
    except Exception as e:
        assert False, f"Unexpected exception occurred: {e}"


test_conversational_filler_and_noise_filtering()