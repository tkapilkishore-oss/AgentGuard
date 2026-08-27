from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import (
    Approval,
    AuditEvent,
    IdempotencyRecord,
    Mandate,
    Product,
    Transaction,
)
from backend.app.services.audit_log import verify_audit_chain
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


# ==============================================================================
# I1 — HAPPY PATH END-TO-END
# ==============================================================================

def test_i1_happy_path_end_to_end(client: TestClient, db_session):
    """I1: Propose ALLOW -> Execute SUCCESS -> Verify budget, DB, idempotency & audit chain."""
    # 1. Proposal
    prop_payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "agent_claim": {
            "product_id": "prod-002",  # 2799.00 <= 3000.00
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    prop_resp = client.post("/transaction/propose", json=prop_payload)
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()["data"]
    txn_id = prop_data["transaction_id"]
    assert prop_data["decision"] == "ALLOW"
    assert prop_data["reason_code"] == "ALLOW"
    assert prop_data["authoritative_total"] == "2799.00"

    # Verify budget untouched after proposal
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    # Verify initial audit events
    events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    event_types = [e.event_type for e in events]
    assert "PROPOSED" in event_types
    assert "POLICY_DECISION" in event_types

    # 2. Execution
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i1-happy"},
    )
    assert exec_resp.status_code == 200
    exec_data = exec_resp.json()["data"]
    assert exec_data["status"] == "SUCCESS"
    assert exec_data["razorpay_payment_id"].startswith("pay_")

    # Verify budget decreased atomically (3000 - 2799 = 201)
    db_session.refresh(mandate)
    assert mandate.budget_remaining == Decimal("201.00")

    # Verify transaction state in DB
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "SUCCESS"
    assert txn.executed_at is not None

    # Verify idempotency record
    idemp = db_session.query(IdempotencyRecord).filter_by(idempotency_key="idemp-i1-happy").first()
    assert idemp is not None
    assert idemp.transaction_id == txn_id

    # Verify complete audit trail & cryptographic hash chain
    exec_events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    exec_event_types = [e.event_type for e in exec_events]
    assert "EXECUTING" in exec_event_types
    assert "EXECUTED" in exec_event_types

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I2 — OVER-BUDGET → ESCALATION → APPROVAL → EXECUTION
# ==============================================================================

def test_i2_over_budget_escalation_approval_execution(client: TestClient, db_session):
    """I2: Over-budget proposal ESCALATES -> Human APPROVES -> Executes successfully."""
    # 1. Propose over-budget (3499.00 > 3000.00)
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {
                "product_id": "prod-001",  # 3499.00
                "claimed_price": 3499.00,
                "quantity": 1,
            },
        },
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()["data"]
    txn_id = prop_data["transaction_id"]
    assert prop_data["decision"] == "ESCALATE"
    assert prop_data["reason_code"] == "BUDGET_EXCEEDED"

    # Verify unapproved execution returns 202
    unappr_exec = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i2-unappr"},
    )
    assert unappr_exec.status_code == 202
    assert unappr_exec.json()["error"]["code"] == "ESCALATION_REQUIRED"

    # 2. Human Approval
    appr_resp = client.post(f"/transaction/{txn_id}/approve")
    assert appr_resp.status_code == 200
    appr_data = appr_resp.json()["data"]
    assert appr_data["status"] == "approved"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "ALLOWED"
    assert txn.reason_code == "APPROVED_BY_HUMAN"

    approval_row = db_session.query(Approval).filter_by(transaction_id=txn_id).first()
    assert approval_row is not None
    assert approval_row.status == "approved"

    # 3. Execution after approval
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i2-approved"},
    )
    assert exec_resp.status_code == 200
    assert exec_resp.json()["data"]["status"] == "SUCCESS"

    # Budget becomes negative-safe (-499.00) as human approval explicitly authorized budget override
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("-499.00")

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I3 — OVER-BUDGET → HUMAN REJECTION
# ==============================================================================

def test_i3_over_budget_human_rejection(client: TestClient, db_session):
    """I3: Escalated proposal REJECTED by human -> Execution permanently blocked."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {
                "product_id": "prod-001",
                "claimed_price": 3499.00,
                "quantity": 1,
            },
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Reject
    rej_resp = client.post(f"/transaction/{txn_id}/reject")
    assert rej_resp.status_code == 200
    assert rej_resp.json()["data"]["status"] == "rejected"

    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    assert txn.status == "DENIED"
    assert txn.reason_code == "REJECTED_BY_HUMAN"

    # Execution blocked with 403
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i3-rej"},
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["error"]["code"] == "REJECTED_BY_HUMAN"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I4 — PRICE TAMPERING ATTACK
# ==============================================================================

def test_i4_price_tampering_attack(client: TestClient, db_session):
    """I4: Client claims 1999.00 for 3499.00 product -> DENY PRICE_MISMATCH -> Cannot execute or alter gateway price."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {
                "product_id": "prod-001",
                "claimed_price": 1999.00,  # Lies! Catalog price is 3499.00
                "quantity": 1,
            },
        },
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()["data"]
    txn_id = prop_data["transaction_id"]
    assert prop_data["decision"] == "DENY"
    assert prop_data["reason_code"] == "PRICE_MISMATCH"
    assert prop_data["authoritative_total"] == "3499.00"

    # Attempt approve -> 400
    appr_resp = client.post(f"/transaction/{txn_id}/approve")
    assert appr_resp.status_code == 400

    # Attempt execute -> 403
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i4-tamper"},
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["error"]["code"] == "PRICE_MISMATCH"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I5 — MERCHANT SUBSTITUTION ATTACK
# ==============================================================================

def test_i5_merchant_substitution_attack(client: TestClient, db_session):
    """I5: Proposing product from unauthorized merchant -> DENY MERCHANT_MISMATCH -> Cannot execute."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",  # Scoped to merchant-001
            "agent_claim": {
                "product_id": "prod-003",  # Belongs to merchant-002, catalog price 5999.00
                "claimed_price": 5999.00,
                "quantity": 1,
            },
        },
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()["data"]
    txn_id = prop_data["transaction_id"]
    assert prop_data["decision"] == "DENY"
    assert prop_data["reason_code"] == "MERCHANT_MISMATCH"

    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "idemp-i5-merchant"},
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["error"]["code"] == "MERCHANT_MISMATCH"

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I6 — REVOKED & EXPIRED MANDATE TERMINAL DENIALS
# ==============================================================================

def test_i6_revoked_and_expired_mandate_terminal_denials(client: TestClient, db_session):
    """I6: Revoked or expired mandate proposals return DENY, cannot be approved or executed."""
    # Revocation test
    mandate_1 = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate_1 is not None
    mandate_1.status = "revoked"
    db_session.commit()

    prop_rev = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    assert prop_rev.status_code == 200
    assert prop_rev.json()["data"]["decision"] == "DENY"
    assert prop_rev.json()["data"]["reason_code"] == "MANDATE_REVOKED"

    txn_rev_id = prop_rev.json()["data"]["transaction_id"]
    assert client.post(f"/transaction/{txn_rev_id}/approve").status_code == 400
    assert client.post("/transaction/execute", json={"transaction_id": txn_rev_id, "idempotency_key": "key-rev"}).status_code == 403

    # Expiry test
    mandate_1.status = "active"
    mandate_1.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    prop_exp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    assert prop_exp.status_code == 200
    assert prop_exp.json()["data"]["decision"] == "DENY"
    assert prop_exp.json()["data"]["reason_code"] == "MANDATE_EXPIRED"

    txn_exp_id = prop_exp.json()["data"]["transaction_id"]
    assert client.post(f"/transaction/{txn_exp_id}/approve").status_code == 400
    assert client.post("/transaction/execute", json={"transaction_id": txn_exp_id, "idempotency_key": "key-exp"}).status_code == 403

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I7 — QUANTITY / STOCK ATTACKS
# ==============================================================================

def test_i7_quantity_validation_and_stock_attacks(client: TestClient, db_session):
    """I7: Invalid quantities rejected by schema; quantity exceeding stock denied by policy."""
    # API schema validation rejections (HTTP 422 or 400)
    for inv_qty in [0, -1, 11, 1.5]:
        resp = client.post(
            "/transaction/propose",
            json={
                "user_id": "user-001",
                "mandate_id": "mandate-001",
                "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": inv_qty},
            },
        )
        assert resp.status_code in (400, 422)

    # Exceed stock claim (prod-002 stock = 2)
    product = db_session.query(Product).filter_by(id="prod-002").first()
    assert product is not None
    product.stock = 2
    db_session.commit()

    stock_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 5},
        },
    )
    assert stock_resp.status_code == 200
    assert stock_resp.json()["data"]["decision"] == "DENY"
    assert stock_resp.json()["data"]["reason_code"] == "QUANTITY_INVALID"

    txn_stock_id = stock_resp.json()["data"]["transaction_id"]
    assert client.post("/transaction/execute", json={"transaction_id": txn_stock_id, "idempotency_key": "key-stock"}).status_code == 403

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I8 — PAYMENT DECLINE → RETRY WITH NEW KEY
# ==============================================================================

def test_i8_payment_decline_and_retry_with_new_key(client: TestClient, db_session):
    """I8: Gateway decline sets FAILED and releases budget; retry with NEW key succeeds."""
    payment_gateway.force_decline = True

    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Attempt 1: Payment declines
    exec_1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "key-fail-1"},
    )
    assert exec_1.status_code == 200
    data_1 = exec_1.json()["data"]
    assert data_1["status"] == "FAILED"
    assert data_1["reason_code"] == "PAYMENT_DECLINED"
    assert data_1["razorpay_payment_id"] is None

    # Verify budget released back to 3000.00
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    # Reset gateway for retry
    payment_gateway.force_decline = False

    # Attempt 2: Retry with NEW key
    exec_2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "key-retry-2"},
    )
    assert exec_2.status_code == 200
    data_2 = exec_2.json()["data"]
    assert data_2["status"] == "SUCCESS"
    assert data_2["razorpay_payment_id"].startswith("pay_")

    # Budget remaining deducted ONCE (3000 - 2799 = 201)
    db_session.refresh(mandate)
    assert mandate.budget_remaining == Decimal("201.00")

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I9 — EXACT IDEMPOTENCY REPLAY
# ==============================================================================

def test_i9_exact_idempotency_replay(client: TestClient, db_session):
    """I9: Replaying exact same idempotency_key returns stored snapshot without double deduction or gateway call."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    with patch.object(payment_gateway, "process_payment", wraps=payment_gateway.process_payment) as mock_gw:
        # Call 1
        resp_1 = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "key-exact-replay"},
        )
        assert resp_1.status_code == 200
        assert mock_gw.call_count == 1

        # Call 2 with exact same key
        resp_2 = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "key-exact-replay"},
        )
        assert resp_2.status_code == 200
        assert resp_1.json() == resp_2.json()
        assert mock_gw.call_count == 1  # 0 additional gateway calls!

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("201.00")  # Deducted ONCE


# ==============================================================================
# I10 — CROSS-TRANSACTION IDEMPOTENCY KEY REUSE
# ==============================================================================

def test_i10_cross_transaction_idempotency_key_reuse(client: TestClient):
    """I10: Reusing an idempotency key across different transactions returns HTTP 400 IDEMPOTENCY_KEY_REUSED."""
    # Create two proposals BEFORE executing either
    r1 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id_1 = r1.json()["data"]["transaction_id"]

    r2 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id_2 = r2.json()["data"]["transaction_id"]

    # Execute txn_1 with key "shared-idemp"
    e1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id_1, "idempotency_key": "shared-idemp"},
    )
    assert e1.status_code == 200

    # Attempt execute txn_2 with same key "shared-idemp"
    e2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id_2, "idempotency_key": "shared-idemp"},
    )
    assert e2.status_code == 400
    assert e2.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"


# ==============================================================================
# I11 — SUCCESS TRANSACTION REPLAY WITH NEW KEY
# ==============================================================================

def test_i11_success_transaction_replay_with_new_key(client: TestClient):
    """I11: Re-executing a completed SUCCESS transaction with a NEW key returns 409 REPLAY_DETECTED."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # First execution with key-1
    e1 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "key-succ-1"},
    )
    assert e1.status_code == 200

    # Second execution with NEW key-2
    e2 = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "key-succ-2"},
    )
    assert e2.status_code == 409
    assert e2.json()["error"]["code"] == "REPLAY_DETECTED"


# ==============================================================================
# I12 — TRANSACTION EXPIRY
# ==============================================================================

def test_i12_transaction_expiry(client: TestClient, db_session):
    """I12: Force transaction expiry -> execute returns HTTP 403 TRANSACTION_EXPIRED -> deducts 0 budget."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Force transaction expiry into past
    txn = db_session.query(Transaction).filter_by(id=txn_id).first()
    assert txn is not None
    txn.expires_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()

    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "key-exp-txn"},
    )
    assert exec_resp.status_code == 403
    assert exec_resp.json()["error"]["code"] == "TRANSACTION_EXPIRED"

    db_session.refresh(txn)
    assert txn.status == "EXPIRED"

    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


# ==============================================================================
# I13 — AUDIT CHAIN INTEGRITY & TAMPER DETECTION
# ==============================================================================

def test_i13_audit_chain_integrity_and_tamper_detection(client: TestClient, db_session):
    """I13: Run complete lifecycle -> verify valid audit chain -> tamper database fields -> verify tamper detected."""
    # 1. Proposal
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # 2. Execute
    client.post("/transaction/execute", json={"transaction_id": txn_id, "idempotency_key": "key-chain-test"})

    # 3. Chain must be valid
    valid_1, err_1 = verify_audit_chain(db_session)
    assert valid_1 is True
    assert err_1 is None

    # 4. Tamper with event payload_hash
    event = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).first()
    assert event is not None
    original_payload_hash = event.payload_hash
    event.payload_hash = "bad_hash_" + "0" * 56
    db_session.commit()

    valid_2, err_2 = verify_audit_chain(db_session)
    assert valid_2 is False
    assert err_2 is not None

    # Restore
    event.payload_hash = original_payload_hash
    db_session.commit()
    valid_3, _ = verify_audit_chain(db_session)
    assert valid_3 is True


# ==============================================================================
# I14 — DATABASE ROLLBACK & ATOMICITY
# ==============================================================================

def test_i14_database_rollback_and_atomicity(client: TestClient, db_session):
    """I14: Simulated DB commit error triggers rollback and leaves 0 partial records in DB."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    with patch.object(db_session, "commit", side_effect=RuntimeError("Simulated DB Failure")):
        exec_resp = client.post(
            "/transaction/execute",
            json={"transaction_id": txn_id, "idempotency_key": "key-rollback"},
        )
        assert exec_resp.status_code == 500
        assert exec_resp.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"

    # Verify budget untouched
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    assert mandate.budget_remaining == Decimal("3000.00")

    # Verify no idempotency record created
    idemp = db_session.query(IdempotencyRecord).filter_by(idempotency_key="key-rollback").first()
    assert idemp is None


# ==============================================================================
# SECURITY & TRUST-BOUNDARY FIELD INJECTION TESTS
# ==============================================================================

def test_security_trust_boundary_field_injection(client: TestClient, db_session):
    """Clients cannot inject server-authoritative fields (status, reason_code, authoritative_total, etc)."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "status": "SUCCESS",
        "reason_code": "ALLOW",
        "authoritative_total": 0.01,
        "merchant_id": "attacker-merchant",
        "budget_remaining": 999999.99,
        "nonce": "hacked-nonce",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["authoritative_total"] == "2799.00"

    txn = db_session.query(Transaction).filter_by(id=data["transaction_id"]).first()
    assert txn is not None
    assert txn.merchant_id == "merchant-001"  # Derived from product, not injection!
    assert txn.authoritative_total == Decimal("2799.00")


# ==============================================================================
# STATE MACHINE INVALID TRANSITIONS TESTS
# ==============================================================================

def test_state_machine_invalid_transitions(client: TestClient, db_session):
    """Invalid state transitions return proper HTTP status and error codes."""
    # 1. DENIED transaction cannot be approved
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-001", "claimed_price": 1999.00, "quantity": 1},  # Lies
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    appr_resp = client.post(f"/transaction/{txn_id}/approve")
    assert appr_resp.status_code == 400
    assert appr_resp.json()["error"]["code"] == "INVALID_TRANSACTION_STATE"

    # 2. REJECTED transaction cannot be executed
    prop_esc = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-001", "claimed_price": 3499.00, "quantity": 1},
        },
    )
    txn_esc_id = prop_esc.json()["data"]["transaction_id"]

    client.post(f"/transaction/{txn_esc_id}/reject")
    exec_resp = client.post("/transaction/execute", json={"transaction_id": txn_esc_id, "idempotency_key": "key-sm-1"})
    assert exec_resp.status_code == 403
    assert exec_resp.json()["error"]["code"] == "REJECTED_BY_HUMAN"
