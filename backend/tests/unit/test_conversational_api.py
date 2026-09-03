"""Unit tests for FastAPI Conversational Brain endpoints (/conversational/query, /session)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.conversational.llm_provider import DeterministicMockLLM
from backend.app.conversational.orchestrator import get_conversational_brain
from backend.app.db.session import SessionLocal
from backend.app.main import app
from scripts.seed_db import seed_database


@pytest.fixture
def client():
    # Inject deterministic mock LLM for testing
    brain = get_conversational_brain(llm_provider=DeterministicMockLLM())
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()


def test_conversational_query_endpoint(client: TestClient, db: Session):
    """Verify POST /conversational/query processes queries and returns structured response."""
    payload = {
        "query": "What is AgentGuard?",
        "session_id": "api_test_sess_1",
        "user_id": "user-001",
    }
    resp = client.post("/conversational/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    res = data["data"]
    assert res["session_id"] == "api_test_sess_1"
    assert res["intent"] == "CONCEPT_EXPLANATION"
    assert "firewall" in res["message"].lower()


def test_conversational_session_inspection_and_reset(client: TestClient, db: Session):
    """Verify GET /conversational/session/{id} and DELETE /conversational/session/{id}."""
    sess_id = "api_test_sess_2"
    # Send a turn
    client.post("/conversational/query", json={"query": "How much budget is left?", "session_id": sess_id})

    # Inspect session
    resp = client.get(f"/conversational/session/{sess_id}")
    assert resp.status_code == 200
    sess_data = resp.json()["data"]
    assert sess_data["session_id"] == sess_id
    assert len(sess_data["history"]) >= 1

    # Reset session
    del_resp = client.delete(f"/conversational/session/{sess_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["status"] == "reset"

    # Inspect again - history should be empty
    resp_after = client.get(f"/conversational/session/{sess_id}")
    assert len(resp_after.json()["data"]["history"]) == 0
