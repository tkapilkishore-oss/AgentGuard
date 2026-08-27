import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.integrations.razorpay_client import RazorpayClient
from backend.app.main import app
from backend.app.models import AuditEvent, IdempotencyRecord, Mandate, Transaction
from backend.app.services.payment_gateway import payment_gateway
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
        yield session
    finally:
        session.close()


def test_phase3_happy_path_e2e(client: TestClient, db: Session):
    """Phase 3 Happy Path E2E: propose -> execute via Razorpay test-mode integration -> SUCCESS."""
    seed_database(db)
    payment_gateway.force_decline = False

    # 1. Propose transaction
    propose_payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",  # Bluetooth Speaker (₹2799.00 <= ₹3000.00)
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    prop_resp = client.post("/transaction/propose", json=propose_payload)
    assert prop_resp.status_code == 200
    prop_json = prop_resp.json()
    assert prop_json["success"] is True
    assert prop_json["data"]["decision"] == "ALLOW"
    assert prop_json["data"]["reason_code"] == "ALLOW"
    txn_id = prop_json["data"]["transaction_id"]

    # 2. Execute transaction
    idempotency_key = f"idemp-p3-happy-{uuid.uuid4().hex[:8]}"
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": idempotency_key},
    )
    assert exec_resp.status_code == 200
    exec_json = exec_resp.json()
    assert exec_json["success"] is True
    assert exec_json["data"]["status"] == "SUCCESS"
    assert exec_json["data"]["reason_code"] == "ALLOW"
    payment_id = exec_json["data"]["razorpay_payment_id"]
    assert payment_id is not None
    assert isinstance(payment_id, str)
    assert payment_id.startswith("pay_")

    # 3. Database Invariants Verification
    db.expire_all()
    txn = db.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "SUCCESS"
    assert txn.idempotency_key == idempotency_key

    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("201.00")  # 3000.00 - 2799.00

    idemp_rec = (
        db.query(IdempotencyRecord).filter_by(idempotency_key=idempotency_key).first()
    )
    assert idemp_rec is not None
    assert idemp_rec.transaction_id == txn_id

    # Audit Events Verification
    events = (
        db.query(AuditEvent)
        .filter_by(transaction_id=txn_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "PROPOSED" in event_types
    assert "POLICY_DECISION" in event_types
    assert "EXECUTING" in event_types
    assert "EXECUTED" in event_types

    executed_event = next(e for e in events if e.event_type == "EXECUTED")
    assert executed_event.actor == "razorpay"
    assert executed_event.payload_hash is not None
    assert executed_event.prev_hash is not None


def test_phase3_payment_failure_and_safe_retry_e2e(client: TestClient, db: Session):
    """Phase 3 Corrected Payment Failure + Safe Retry E2E:

    1. Execute transaction using idempotency_key_A.
    2. Razorpay/test gateway fails -> status FAILED / PAYMENT_DECLINED.
    3. Reserved budget is released.
    4. Execute same FAILED transaction using NEW idempotency_key_B.
    5. Payment succeeds -> status SUCCESS.
    6. Verify budget deducted exactly once.
    7. Verify audit events correctly represent failure and subsequent success.
    """
    seed_database(db)

    # 1. Propose transaction
    propose_payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    prop_resp = client.post("/transaction/propose", json=propose_payload)
    assert prop_resp.status_code == 200
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Initial budget check
    db.expire_all()
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate.budget_remaining == Decimal("3000.00")

    # 2. Force payment gateway decline
    payment_gateway.force_decline = True
    key_a = f"idemp-key-A-{uuid.uuid4().hex[:8]}"
    exec_resp_1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_a},
    )
    assert exec_resp_1.status_code == 200
    json_1 = exec_resp_1.json()
    assert json_1["success"] is True
    assert json_1["data"]["status"] == "FAILED"
    assert json_1["data"]["reason_code"] == "PAYMENT_DECLINED"
    assert json_1["data"]["razorpay_payment_id"] is None

    # Verify state after failure: budget released!
    db.expire_all()
    txn = db.query(Transaction).filter_by(id=txn_id).first()
    assert txn.status == "FAILED"
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate.budget_remaining == Decimal("3000.00")

    idemp_a = db.query(IdempotencyRecord).filter_by(idempotency_key=key_a).first()
    assert idemp_a is not None
    assert idemp_a.response_snapshot["data"]["status"] == "FAILED"

    # 3. Re-enable payment gateway (success mode) and retry with NEW key_B
    payment_gateway.force_decline = False
    key_b = f"idemp-key-B-{uuid.uuid4().hex[:8]}"
    exec_resp_2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_b},
    )
    assert exec_resp_2.status_code == 200
    json_2 = exec_resp_2.json()
    assert json_2["success"] is True
    assert json_2["data"]["status"] == "SUCCESS"
    assert json_2["data"]["razorpay_payment_id"] is not None

    # Verify state after successful retry: budget deducted exactly once, reason_code restored to ALLOW!
    db.expire_all()
    txn = db.query(Transaction).filter_by(id=txn_id).first()
    assert json_2["data"]["reason_code"] == "ALLOW"
    assert txn.status == "SUCCESS"
    assert txn.reason_code == "ALLOW"
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate.budget_remaining == Decimal("201.00")  # 3000.00 - 2799.00

    idemp_b = db.query(IdempotencyRecord).filter_by(idempotency_key=key_b).first()
    assert idemp_b is not None
    assert idemp_b.response_snapshot["data"]["status"] == "SUCCESS"
    assert idemp_b.response_snapshot["data"]["reason_code"] == "ALLOW"

    # Confirm key A snapshot retains FAILED status and PAYMENT_DECLINED reason_code
    assert idemp_a.response_snapshot["data"]["status"] == "FAILED"
    assert idemp_a.response_snapshot["data"]["reason_code"] == "PAYMENT_DECLINED"

    # 4. Verify exact key retry on key_A returns stored FAILED response snapshot
    retry_key_a = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_a},
    )
    assert retry_key_a.status_code == 200
    assert retry_key_a.json()["data"]["status"] == "FAILED"

    # 5. Verify exact key retry on key_B returns stored SUCCESS response snapshot
    retry_key_b = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_b},
    )
    assert retry_key_b.status_code == 200
    assert retry_key_b.json()["data"]["status"] == "SUCCESS"

    # 6. Verify NEW key_C against completed SUCCESS transaction returns 409 REPLAY_DETECTED
    key_c = f"idemp-key-C-{uuid.uuid4().hex[:8]}"
    exec_resp_3 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_c},
    )
    assert exec_resp_3.status_code == 409
    assert exec_resp_3.json()["error"]["code"] == "REPLAY_DETECTED"

    # Audit Events Verification
    events = (
        db.query(AuditEvent)
        .filter_by(transaction_id=txn_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )
    event_types = [e.event_type for e in events]
    assert "FAILED" in event_types
    assert "EXECUTED" in event_types

    failed_event = next(e for e in events if e.event_type == "FAILED")
    assert failed_event.actor == "razorpay"
    executed_event = next(e for e in events if e.event_type == "EXECUTED")
    assert executed_event.actor == "razorpay"


def test_phase3_idempotency_key_reuse_across_transactions(client: TestClient, db: Session):
    """Verify reusing same idempotency key across different transactions returns 400 IDEMPOTENCY_KEY_REUSED."""
    seed_database(db)
    payment_gateway.force_decline = False

    # Propose Txn 1 & Txn 2
    prop_1 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    ).json()["data"]["transaction_id"]

    prop_2 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    ).json()["data"]["transaction_id"]

    shared_key = f"shared-key-{uuid.uuid4().hex[:8]}"

    # Execute Txn 1 with shared_key
    exec_1 = client.post(
        "/transaction/execute",
        json={"transaction_id": prop_1, "idempotency_key": shared_key},
    )
    assert exec_1.status_code == 200

    # Attempt to execute Txn 2 with same shared_key
    exec_2 = client.post(
        "/transaction/execute",
        json={"transaction_id": prop_2, "idempotency_key": shared_key},
    )
    assert exec_2.status_code == 400
    assert exec_2.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


def test_phase3_razorpay_configured_live_mock_simulation(client: TestClient, db: Session):
    """Verify execute endpoint when RazorpayClient is configured with test credentials."""
    seed_database(db)

    # Propose transaction
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Create configured client with mock HTTP response for Razorpay API call
    custom_client = RazorpayClient(
        key_id="rzp_test_live_key",
        key_secret="rzp_test_live_secret",
        mock_fallback=False,
    )
    with patch.object(
        custom_client,
        "create_order",
        return_value={
            "id": f"order_rzp_{uuid.uuid4().hex[:8]}",
            "entity": "order",
            "amount": 279900,
            "status": "created",
        },
    ), patch.object(payment_gateway, "client", custom_client):
        payment_gateway.force_decline = False
        idemp_key = f"idemp-live-{uuid.uuid4().hex[:8]}"
        exec_resp = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": idemp_key},
        )
        assert exec_resp.status_code == 200
        json_data = exec_resp.json()
        assert json_data["success"] is True
        assert json_data["data"]["status"] == "SUCCESS"
        assert json_data["data"]["razorpay_payment_id"].startswith("pay_rzp_")

        # Verify audit event actor == "razorpay"
        db.expire_all()
        event = (
            db.query(AuditEvent)
            .filter_by(transaction_id=txn_id, event_type="EXECUTED")
            .first()
        )
        assert event is not None
        assert event.actor == "razorpay"


def test_bug_3m_001_successful_retry_clears_stale_payment_declined_reason_code(
    client: TestClient, db: Session
):
    """Regression test BUG-3M-001:

    Verify that retrying a FAILED transaction (with status PAYMENT_DECLINED)
    using a NEW idempotency key clears the stale PAYMENT_DECLINED reason_code
    and updates both the persisted transaction and the response snapshot to ALLOW.
    """
    seed_database(db)

    # 1. Create ALLOW transaction
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    assert prop_resp.status_code == 200
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # 2. Force payment failure
    payment_gateway.force_decline = True
    key_a = f"idemp-bug3m-A-{uuid.uuid4().hex[:8]}"

    # 3. Execute with key A
    exec_a = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_a},
    )

    # 4. Assert FAILED / PAYMENT_DECLINED
    assert exec_a.status_code == 200
    json_a = exec_a.json()["data"]
    assert json_a["status"] == "FAILED"
    assert json_a["reason_code"] == "PAYMENT_DECLINED"

    # 5. Assert budget restored
    db.expire_all()
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate.budget_remaining == Decimal("3000.00")

    # 6. Disable forced failure
    payment_gateway.force_decline = False
    key_b = f"idemp-bug3m-B-{uuid.uuid4().hex[:8]}"

    # 7. Retry with NEW idempotency key B
    exec_b = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": key_b},
    )

    # 8. Assert status == SUCCESS and reason_code == ALLOW in response
    assert exec_b.status_code == 200
    json_b = exec_b.json()["data"]
    assert json_b["status"] == "SUCCESS"
    assert json_b["reason_code"] == "ALLOW"

    # 9. Inspect persisted transaction in DB
    db.expire_all()
    txn = db.query(Transaction).filter_by(id=txn_id).first()
    assert txn.status == "SUCCESS"
    assert txn.reason_code == "ALLOW"

    # 10. Inspect key B response snapshot in DB
    rec_b = db.query(IdempotencyRecord).filter_by(idempotency_key=key_b).first()
    assert rec_b is not None
    assert rec_b.response_snapshot["data"]["status"] == "SUCCESS"
    assert rec_b.response_snapshot["data"]["reason_code"] == "ALLOW"

    # 11. Confirm key A snapshot remains FAILED / PAYMENT_DECLINED
    rec_a = db.query(IdempotencyRecord).filter_by(idempotency_key=key_a).first()
    assert rec_a is not None
    assert rec_a.response_snapshot["data"]["status"] == "FAILED"
    assert rec_a.response_snapshot["data"]["reason_code"] == "PAYMENT_DECLINED"



