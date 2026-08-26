from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import Approval, Transaction
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


def _create_escalated_transaction(client: TestClient) -> str:
    """Helper fixture: proposes an over-budget transaction returning ESCALATED status."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-001",  # 3499.00 > 3000.00
            "claimed_price": 3499.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    return response.json()["data"]["transaction_id"]


def test_approval_happy_path(client: TestClient, db_session):
    """Happy Path: Escalated transaction is approved by human."""
    txn_id = _create_escalated_transaction(client)

    response = client.post(f"/transaction/{txn_id}/approve")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["transaction_id"] == txn_id
    assert data["status"] == "approved"
    assert data["approver_id"] == "human_approver_001"

    # DB Persistence Verification
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "ALLOWED"
    assert txn.reason_code == "APPROVED_BY_HUMAN"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 1
    assert approvals[0].status == "approved"
    assert approvals[0].approver_id == "human_approver_001"


def test_rejection_happy_path(client: TestClient, db_session):
    """Happy Path: Escalated transaction is rejected by human."""
    txn_id = _create_escalated_transaction(client)

    response = client.post(f"/transaction/{txn_id}/reject")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["success"] is True
    data = res_data["data"]
    assert data["transaction_id"] == txn_id
    assert data["status"] == "rejected"
    assert data["approver_id"] == "human_approver_001"

    # DB Persistence Verification
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "DENIED"
    assert txn.reason_code == "REJECTED_BY_HUMAN"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 1
    assert approvals[0].status == "rejected"


@pytest.mark.parametrize(
    "initial_status, initial_reason",
    [
        ("ALLOWED", "ALLOW"),
        ("DENIED", "PRICE_MISMATCH"),
        ("DENIED", "MERCHANT_MISMATCH"),
        ("DENIED", "MANDATE_REVOKED"),
        ("DENIED", "MANDATE_EXPIRED"),
        ("DENIED", "QUANTITY_INVALID"),
    ],
)
def test_approval_rejected_on_invalid_initial_state(client: TestClient, db_session, initial_status, initial_reason):
    """Terminal denials and ALLOWED transactions cannot be approved (returns HTTP 400)."""
    txn_id = _create_escalated_transaction(client)
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.status = initial_status
    txn.reason_code = initial_reason
    db_session.commit()

    response = client.post(f"/transaction/{txn_id}/approve")
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["success"] is False
    assert json_data["error"]["code"] == "INVALID_TRANSACTION_STATE"

    # Verify zero approval records created
    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 0


def test_double_approval_fails(client: TestClient, db_session):
    """Re-approving an already approved transaction fails with 400."""
    txn_id = _create_escalated_transaction(client)

    resp1 = client.post(f"/transaction/{txn_id}/approve")
    assert resp1.status_code == 200

    resp2 = client.post(f"/transaction/{txn_id}/approve")
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 1


def test_reject_after_approve_fails(client: TestClient, db_session):
    """Rejecting an approved transaction fails with 400."""
    txn_id = _create_escalated_transaction(client)

    resp1 = client.post(f"/transaction/{txn_id}/approve")
    assert resp1.status_code == 200

    resp2 = client.post(f"/transaction/{txn_id}/reject")
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "ALLOWED"
    assert txn.reason_code == "APPROVED_BY_HUMAN"


def test_double_rejection_fails(client: TestClient, db_session):
    """Re-rejecting an already rejected transaction fails with 400."""
    txn_id = _create_escalated_transaction(client)

    resp1 = client.post(f"/transaction/{txn_id}/reject")
    assert resp1.status_code == 200

    resp2 = client.post(f"/transaction/{txn_id}/reject")
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 1


def test_approve_after_reject_fails(client: TestClient, db_session):
    """Approving a rejected transaction fails with 400."""
    txn_id = _create_escalated_transaction(client)

    resp1 = client.post(f"/transaction/{txn_id}/reject")
    assert resp1.status_code == 200

    resp2 = client.post(f"/transaction/{txn_id}/approve")
    assert resp2.status_code == 400
    assert resp2.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "DENIED"
    assert txn.reason_code == "REJECTED_BY_HUMAN"


def test_approve_nonexistent_transaction(client: TestClient):
    response = client.post("/transaction/nonexistent-id/approve")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_reject_nonexistent_transaction(client: TestClient):
    response = client.post("/transaction/nonexistent-id/reject")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_expired_transaction_cannot_be_approved(client: TestClient, db_session):
    """Expired escalated transaction cannot be approved (returns 400 TRANSACTION_EXPIRED)."""
    txn_id = _create_escalated_transaction(client)
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    response = client.post(f"/transaction/{txn_id}/approve")
    assert response.status_code == 400
    json_data = response.json()
    assert json_data["error"]["code"] == "TRANSACTION_EXPIRED"

    # Transaction status updated to DENIED / TRANSACTION_EXPIRED
    txn_updated = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn_updated is not None
    assert txn_updated.status == "DENIED"
    assert txn_updated.reason_code == "TRANSACTION_EXPIRED"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 0


def test_client_cannot_inject_approver_id(client: TestClient, db_session):
    """Injected approver_id in request body or params is ignored by server."""
    txn_id = _create_escalated_transaction(client)

    response = client.post(f"/transaction/{txn_id}/approve", json={"approver_id": "admin_hacked"})
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["data"]["approver_id"] == "human_approver_001"

    approval = db_session.query(Approval).filter_by(transaction_id=txn_id).first()
    assert approval is not None
    assert approval.approver_id == "human_approver_001"


def test_approval_db_commit_failure_rollbacks(client: TestClient, db_session):
    """If db.commit fails during approval, transaction remains ESCALATED and 500 error is returned."""
    txn_id = _create_escalated_transaction(client)

    with patch.object(db_session, "commit", side_effect=RuntimeError("DB Commit Error")):
        response = client.post(f"/transaction/{txn_id}/approve")
        assert response.status_code == 500
        json_data = response.json()
        assert json_data["error"]["code"] == "INTERNAL_SERVER_ERROR"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "ESCALATED"
    assert txn.reason_code == "BUDGET_EXCEEDED"

    approvals = db_session.query(Approval).filter_by(transaction_id=txn_id).all()
    assert len(approvals) == 0
