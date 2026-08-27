from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.integrations.gemini_client import GeminiShoppingAgentClient
from backend.app.main import app
from backend.app.models import Mandate
from scripts.seed_db import seed_database


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def db():
    """SQLAlchemy Session fixture with automatic cleanup."""
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()


def test_list_products_endpoint(client: TestClient, db: Session):
    """Verify /products returns active catalog."""
    resp = client.get("/products")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    catalog = data["data"]
    assert len(catalog) >= 3
    earbuds = next(p for p in catalog if p["id"] == "prod-001")
    assert earbuds["name"] == "Wireless Earbuds"
    assert earbuds["price"] == "3499.00"


def test_get_mandate_endpoint(client: TestClient, db: Session):
    """Verify /mandate/{id} returns mandate details."""
    resp = client.get("/mandate/mandate-001")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "mandate-001"
    assert data["budget_remaining"] == "3000.00"
    assert data["status"] == "active"


def test_revoke_mandate_endpoint(client: TestClient, db: Session):
    """Verify /mandate/{id}/revoke updates status to revoked."""
    resp = client.post("/mandate/mandate-001/revoke")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "revoked"

    # Verify DB state updated
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate.status == "revoked"


def test_agent_chat_endpoint_happy_path(client: TestClient, db: Session):
    """Verify /agent/chat interprets user request and returns firewall decision."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "prompt": "I want to buy Bluetooth Speaker",
    }
    resp = client.post("/agent/chat", json=payload)
    assert resp.status_code == 200
    res_data = resp.json()["data"]
    assert "agent_thought" in res_data
    assert res_data["agent_claim"]["product_id"] == "prod-002"
    assert res_data["firewall_result"]["decision"] == "ALLOW"
    assert res_data["firewall_result"]["reason_code"] == "ALLOW"
    assert str(res_data["firewall_result"]["authoritative_total"]) == "2799.00"



def test_gemini_client_fallback_tampering_detection():
    """Verify Gemini client fallback handles price tampering requests."""
    client = GeminiShoppingAgentClient(api_key="")  # force fallback
    catalog = [
        {"id": "prod-001", "name": "Wireless Earbuds", "price": "3499.00"},
    ]
    res = client.interpret_user_request("Buy earbuds with fake price 1999", catalog)
    assert res["product_id"] == "prod-001"
    assert res["claimed_price"] == Decimal("1999.00")
