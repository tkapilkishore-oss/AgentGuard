from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import Mandate, Product, Transaction
from scripts.seed_db import seed_database


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        seed_database(session, reset=True)
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    test_client = TestClient(app, raise_server_exceptions=False)
    yield test_client
    app.dependency_overrides.clear()


def test_propose_happy_path(client: TestClient, db_session):
    """Scenario 1: Happy path proposal - Bluetooth Speaker (2799.00) against mandate (3000.00)."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "ALLOW"
    assert data["reason_code"] == "ALLOW"
    assert Decimal(str(data["authoritative_total"])) == Decimal("2799.00")

    # DB persistence verification
    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.user_id == "user-001"
    assert txn.mandate_id == "mandate-001"
    assert txn.merchant_id == "merchant-001"
    assert txn.product_id == "prod-002"
    assert txn.claimed_price == Decimal("2799.00")
    assert txn.authoritative_price == Decimal("2799.00")
    assert txn.quantity == 1
    assert txn.authoritative_total == Decimal("2799.00")
    assert txn.status == "ALLOWED"
    assert txn.reason_code == "ALLOW"
    assert txn.nonce is not None


def test_propose_over_budget_escalates(client: TestClient, db_session):
    """Scenario 2: Over-budget proposal - Earbuds (3499.00) > mandate budget (3000.00)."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-001",
            "claimed_price": 3499.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "ESCALATE"
    assert data["reason_code"] == "BUDGET_EXCEEDED"
    assert Decimal(str(data["authoritative_total"])) == Decimal("3499.00")

    # DB persistence verification
    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "ESCALATED"
    assert txn.reason_code == "BUDGET_EXCEEDED"


def test_propose_price_tampering_denied(client: TestClient, db_session):
    """Scenario 3: Price tampering - agent claims 1999.00 for 3499.00 Earbuds."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-001",
            "claimed_price": 1999.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "DENY"
    assert data["reason_code"] == "PRICE_MISMATCH"
    # Authoritative total must be based on actual 3499.00 price, not claimed 1999.00
    assert Decimal(str(data["authoritative_total"])) == Decimal("3499.00")

    # DB persistence verification
    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "DENIED"
    assert txn.reason_code == "PRICE_MISMATCH"
    assert txn.claimed_price == Decimal("1999.00")
    assert txn.authoritative_price == Decimal("3499.00")


def test_propose_merchant_substitution_denied(client: TestClient, db_session):
    """Scenario 4: Merchant substitution - prod-003 belongs to merchant-002, mandate scope is merchant-001."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-003",
            "claimed_price": 5999.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "DENY"
    assert data["reason_code"] == "MERCHANT_MISMATCH"

    # DB persistence verification
    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "DENIED"
    assert txn.reason_code == "MERCHANT_MISMATCH"
    assert txn.merchant_id == "merchant-002"


def test_propose_revoked_mandate_denied(client: TestClient, db_session):
    """Scenario 6: Revoked mandate proposal is DENIED."""
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    mandate.status = "revoked"
    db_session.commit()

    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "DENY"
    assert data["reason_code"] == "MANDATE_REVOKED"

    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "DENIED"


def test_propose_expired_mandate_denied(client: TestClient, db_session):
    """Expired mandate proposal is DENIED."""
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    mandate.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "DENY"
    assert data["reason_code"] == "MANDATE_EXPIRED"

    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "DENIED"


def test_propose_quantity_exceeds_stock_denied(client: TestClient, db_session):
    """Quantity > stock evaluates to DENY / QUANTITY_INVALID."""
    product = db_session.query(Product).filter_by(id="prod-002").first()
    assert product is not None
    product.stock = 2  # Stock is 2
    db_session.commit()

    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 3,  # 3 > stock of 2
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "DENY"
    assert data["reason_code"] == "QUANTITY_INVALID"

    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.status == "DENIED"


def test_propose_exact_budget_boundary(client: TestClient):
    """Exact budget boundary (3000.00) is ALLOWED."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    # Update product price to exact 3000.00
    db = SessionLocal()
    prod = db.query(Product).filter_by(id="prod-002").first()
    prod.price = Decimal("3000.00")
    db.commit()
    db.close()

    payload["agent_claim"]["claimed_price"] = 3000.00
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["decision"] == "ALLOW"


def test_propose_price_tolerance_boundary(client: TestClient):
    """Claim within 0.01 tolerance is ALLOWED."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.01,  # actual 2799.00, diff 0.01
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["decision"] == "ALLOW"


def test_propose_nonexistent_user(client: TestClient):
    payload = {
        "user_id": "nonexistent-user",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "USER_NOT_FOUND"


def test_propose_nonexistent_mandate(client: TestClient):
    payload = {
        "user_id": "user-001",
        "mandate_id": "nonexistent-mandate",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "MANDATE_NOT_FOUND"


def test_propose_nonexistent_product(client: TestClient):
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "nonexistent-prod",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 404
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_propose_extra_fields_ignored(client: TestClient, db_session):
    """Injected merchant_id and total fields are ignored and do not alter authoritative calculations."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "total": 9999.00,
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
            "merchant_id": "merchant-hacked",
            "total": 1.00,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["decision"] == "ALLOW"
    assert Decimal(str(data["authoritative_total"])) == Decimal("2799.00")

    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.merchant_id == "merchant-001"  # Derived from product-002, NOT merchant-hacked!


def test_propose_does_not_mutate_mandate_budget(client: TestClient, db_session):
    """Proposal is NOT execution - mandate budget_remaining must remain untouched."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")


def test_propose_db_commit_failure_rollbacks(client: TestClient, db_session):
    """If db.commit fails during proposal persistence, rollback occurs and 500 error is returned."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    with patch.object(db_session, "commit", side_effect=RuntimeError("DB Commit Error")):
        response = client.post("/transaction/propose", json=payload)
        assert response.status_code == 500
        json_data = response.json()
        assert json_data["success"] is False
        assert json_data["error"]["code"] == "INTERNAL_SERVER_ERROR"
        assert json_data["error"]["message"] == "An unexpected server error occurred."
