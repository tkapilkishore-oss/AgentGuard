from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import IdempotencyRecord, Mandate, Transaction
from backend.app.services.payment_gateway import payment_gateway
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
    payment_gateway.force_decline = False


def _create_allowed_transaction(client: TestClient) -> str:
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",  # 2799.00 <= 3000.00
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    assert response.json()["data"]["decision"] == "ALLOW"
    return response.json()["data"]["transaction_id"]


def test_execute_happy_path(client: TestClient, db_session):
    """Happy Path: Execute allowed transaction successfully."""
    txn_id = _create_allowed_transaction(client)

    payload = {"transaction_id": txn_id, "idempotency_key": "idemp-001"}
    response = client.post("/transaction/execute", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["transaction_id"] == txn_id
    assert data["status"] == "SUCCESS"
    assert data["razorpay_payment_id"].startswith("pay_")

    # DB Persistence & Budget Verification
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "SUCCESS"
    assert txn.executed_at is not None
    assert txn.idempotency_key == "idemp-001"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("201.00")  # 3000.00 - 2799.00

    idemp = db_session.query(IdempotencyRecord).filter_by(idempotency_key="idemp-001").first()
    assert idemp is not None
    assert idemp.transaction_id == txn_id


def test_execute_approved_by_human_transaction(client: TestClient, db_session):
    """Execution of an escalated transaction after human approval."""
    # Propose over-budget
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-001",  # 3499.00 > 3000.00
            "claimed_price": 3499.00,
            "quantity": 1,
        },
    }
    prop_resp = client.post("/transaction/propose", json=payload)
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Approve
    appr_resp = client.post(f"/transaction/{txn_id}/approve")
    assert appr_resp.status_code == 200

    # Execute
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-appr-001"},
    )
    assert exec_resp.status_code == 200
    data = exec_resp.json()["data"]
    assert data["status"] == "SUCCESS"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "SUCCESS"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("-499.00")  # 3000.00 - 3499.00


def test_execute_escalated_without_approval_returns_202(client: TestClient, db_session):
    """Attempting to execute an escalated transaction without human approval returns HTTP 202 ESCALATION_REQUIRED."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-001",  # 3499.00
            "claimed_price": 3499.00,
            "quantity": 1,
        },
    }
    txn_id = client.post("/transaction/propose", json=payload).json()["data"]["transaction_id"]

    response = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-esc-001"},
    )
    assert response.status_code == 202
    json_data = response.json()
    assert json_data["error"]["code"] == "ESCALATION_REQUIRED"

    # Budget remains untouched
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")


@pytest.mark.parametrize(
    "initial_reason, expected_code",
    [
        ("PRICE_MISMATCH", "PRICE_MISMATCH"),
        ("MERCHANT_MISMATCH", "MERCHANT_MISMATCH"),
        ("MANDATE_REVOKED", "MANDATE_REVOKED"),
        ("MANDATE_EXPIRED", "MANDATE_EXPIRED"),
        ("QUANTITY_INVALID", "QUANTITY_INVALID"),
        ("REJECTED_BY_HUMAN", "REJECTED_BY_HUMAN"),
    ],
)
def test_execute_terminal_denied_returns_403(client: TestClient, db_session, initial_reason, expected_code):
    """Terminal denials return HTTP 403 and cannot be executed."""
    txn_id = _create_allowed_transaction(client)
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.status = "DENIED"
    txn.reason_code = initial_reason
    db_session.commit()

    response = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-denied"},
    )
    assert response.status_code == 403
    json_data = response.json()
    assert json_data["error"]["code"] == expected_code

    # Budget remains untouched
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")


def test_execute_expired_transaction_returns_403(client: TestClient, db_session):
    """Executing an expired transaction returns 403 TRANSACTION_EXPIRED and budget is not deducted."""
    txn_id = _create_allowed_transaction(client)
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    response = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-exp"},
    )
    assert response.status_code == 403
    json_data = response.json()
    assert json_data["error"]["code"] == "TRANSACTION_EXPIRED"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")


def test_execute_authoritative_money_enforcement(client: TestClient, db_session):
    """MockPaymentGateway receives authoritative price (2799.00), not any client-claimed price."""
    txn_id = _create_allowed_transaction(client)

    with patch.object(payment_gateway, "process_payment", wraps=payment_gateway.process_payment) as mock_gw:
        response = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "idemp-auth-money"},
        )
        assert response.status_code == 200
        mock_gw.assert_called_once_with(transaction_id=txn_id, amount=Decimal("2799.00"))


def test_execute_payment_decline_releases_budget(client: TestClient, db_session):
    """When MockPaymentGateway declines payment, transaction status becomes FAILED and budget is released."""
    payment_gateway.force_decline = True
    txn_id = _create_allowed_transaction(client)

    response = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-decline-001"},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["status"] == "FAILED"
    assert data["reason_code"] == "PAYMENT_DECLINED"
    assert data["razorpay_payment_id"] is None

    # Verify budget released
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")  # Released!

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "FAILED"


def test_execute_exact_idempotency_key_replay(client: TestClient, db_session):
    """Exact idempotency_key repeated returns stored snapshot without re-deducting budget."""
    txn_id = _create_allowed_transaction(client)

    payload = {"transaction_id": txn_id, "idempotency_key": "idemp-exact-replay"}
    resp1 = client.post("/transaction/execute", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()["data"]

    # Second call with exact same idempotency_key
    resp2 = client.post("/transaction/execute", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()["data"]

    assert data1 == data2

    # Verify budget remaining was only deducted ONCE (3000 - 2799 = 201)
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("201.00")


def test_execute_idempotency_key_reused_across_different_transactions_fails(client: TestClient):
    """Reusing an idempotency key across different transactions returns HTTP 400 IDEMPOTENCY_KEY_REUSED."""
    # Create two proposals BEFORE executing either (so both get status ALLOWED)
    txn_id_1 = _create_allowed_transaction(client)
    txn_id_2 = _create_allowed_transaction(client)

    # Execute txn_1 with key "shared-key"
    resp1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id_1, "idempotency_key": "shared-key"},
    )
    assert resp1.status_code == 200

    # Attempt execute txn_2 with same key "shared-key"
    resp2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id_2, "idempotency_key": "shared-key"},
    )
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_execute_new_key_on_success_triggers_409_replay(client: TestClient):
    """Calling execute with a NEW idempotency key on a SUCCESS transaction returns 409 REPLAY_DETECTED."""
    txn_id = _create_allowed_transaction(client)

    resp1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-key-1"},
    )
    assert resp1.status_code == 200

    resp2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-key-2"},
    )
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "REPLAY_DETECTED"


def test_execute_retry_after_payment_decline_succeeds(client: TestClient, db_session):
    """A failed payment attempt can be legitimately retried with a NEW idempotency key."""
    # Attempt 1: Payment declines
    payment_gateway.force_decline = True
    txn_id = _create_allowed_transaction(client)

    resp1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-fail-1"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["data"]["status"] == "FAILED"

    # Fix payment gateway for retry
    payment_gateway.force_decline = False

    # Attempt 2: Retry with NEW idempotency key
    resp2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-retry-2"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["data"]["status"] == "SUCCESS"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("201.00")


def test_execute_nonexistent_transaction(client: TestClient):
    response = client.post(
        "/transaction/execute",
        json={"transaction_id": "nonexistent-id", "idempotency_key": "idemp-none"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_execute_db_commit_failure_rollbacks(client: TestClient, db_session):
    """If db.commit fails during execution, rollback occurs and 500 error is returned."""
    txn_id = _create_allowed_transaction(client)

    with patch.object(db_session, "commit", side_effect=RuntimeError("DB Commit Error")):
        response = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "idemp-err"},
        )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")


def test_execute_executing_status_returns_409_conflict(client: TestClient, db_session):
    """SEC-01 Regression: Attempting execution on an EXECUTING transaction returns 409 TRANSACTION_EXECUTING."""
    txn_id = _create_allowed_transaction(client)

    # Set transaction status to EXECUTING manually
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.status = "EXECUTING"
    db_session.commit()

    initial_budget = db_session.query(Mandate).filter_by(id="mandate-001").first().budget_remaining
    initial_idemp_count = db_session.query(IdempotencyRecord).count()

    with patch.object(payment_gateway, "process_payment", wraps=payment_gateway.process_payment) as mock_pg:
        response = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "idemp-executing-test"},
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "TRANSACTION_EXECUTING"

        # Assert no payment gateway call was invoked
        mock_pg.assert_not_called()

    # Assert budget remains unchanged
    current_budget = db_session.query(Mandate).filter_by(id="mandate-001").first().budget_remaining
    assert current_budget == initial_budget

    # Assert no duplicate idempotency record was created
    assert db_session.query(IdempotencyRecord).count() == initial_idemp_count

    # Assert transaction status remains EXECUTING
    db_session.refresh(txn)
    assert txn.status == "EXECUTING"

