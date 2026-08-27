from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import AuditChainState, AuditEvent, Transaction
from backend.app.services.audit_log import verify_audit_chain
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


def test_get_transaction_audit_lifecycle_success(client: TestClient, db_session):
    """Verify that an existing transaction's full lifecycle audit events can be retrieved."""
    # 1. Propose transaction
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {
                "product_id": "prod-002",
                "claimed_price": 2799.00,
                "quantity": 1,
            },
        },
    )
    assert prop_resp.status_code == 200
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # 2. Execute transaction
    exec_resp = client.post(
        "/transaction/execute",
        json={
            "transaction_id": txn_id,
            "idempotency_key": "audit-test-key-001",
        },
    )
    assert exec_resp.status_code == 200

    # 3. Retrieve audit history
    audit_resp = client.get(f"/transaction/{txn_id}/audit")
    assert audit_resp.status_code == 200

    # Envelope validation
    body = audit_resp.json()
    assert body["success"] is True
    assert body["error"] is None
    data = body["data"]

    # Transaction metadata
    assert data["transaction"]["id"] == txn_id
    assert data["transaction"]["status"] == "SUCCESS"
    assert Decimal(str(data["transaction"]["authoritative_total"])) == Decimal("2799.00")
    assert data["transaction"]["product_id"] == "prod-002"
    assert data["transaction"]["product_name"] == "Bluetooth Speaker"

    # Events sequence
    events = data["events"]
    assert len(events) == 4
    event_types = [e["event_type"] for e in events]
    assert event_types == ["PROPOSED", "POLICY_DECISION", "EXECUTING", "EXECUTED"]

    # Actor attribution
    actors = [e["actor"] for e in events]
    assert actors == ["agent", "firewall", "firewall", "razorpay"]

    # Chain verification
    assert data["chain_verified"] is True
    assert data["chain_verification_error"] is None


def test_audit_events_belong_strictly_to_requested_transaction(client: TestClient, db_session):
    """Verify that audit events returned belong solely to the requested transaction ID."""
    # Create txn 1
    r1 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_1 = r1.json()["data"]["transaction_id"]

    # Create txn 2
    r2 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_2 = r2.json()["data"]["transaction_id"]

    audit_1 = client.get(f"/transaction/{txn_1}/audit").json()["data"]["events"]
    audit_2 = client.get(f"/transaction/{txn_2}/audit").json()["data"]["events"]

    assert len(audit_1) > 0
    assert len(audit_2) > 0

    for e in audit_1:
        assert e["transaction_id"] == txn_1
    for e in audit_2:
        assert e["transaction_id"] == txn_2


def test_audit_events_deterministic_chronological_order(client: TestClient, db_session):
    """Verify that events are returned strictly ordered by seq_id in ascending sequence."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-001", "claimed_price": 3499.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # Approve
    client.post(f"/transaction/{txn_id}/approve")

    # Execute
    client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "audit-order-test"},
    )

    audit_resp = client.get(f"/transaction/{txn_id}/audit")
    events = audit_resp.json()["data"]["events"]

    seq_ids = [e["seq_id"] for e in events]
    assert len(seq_ids) == 5
    assert seq_ids == sorted(seq_ids)
    assert len(seq_ids) == len(set(seq_ids))


def test_nonexistent_transaction_returns_404(client: TestClient):
    """Verify that requesting audit history for a non-existent transaction returns 404."""
    resp = client.get("/transaction/nonexistent-uuid-12345/audit")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_standard_response_envelope(client: TestClient, db_session):
    """Verify standard response envelope {success, data, error} across 200 and 404 responses."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    # 200 OK
    resp_200 = client.get(f"/transaction/{txn_id}/audit")
    assert resp_200.status_code == 200
    json_200 = resp_200.json()
    assert set(json_200.keys()) == {"success", "data", "error"}
    assert json_200["success"] is True
    assert json_200["data"] is not None
    assert json_200["error"] is None

    # 404 Not Found
    resp_404 = client.get("/transaction/missing-id/audit")
    assert resp_404.status_code == 404
    json_404 = resp_404.json()
    assert set(json_404.keys()) == {"success", "data", "error"}
    assert json_404["success"] is False
    assert json_404["data"] is None
    assert "code" in json_404["error"]
    assert "message" in json_404["error"]


def test_no_secret_credentials_leaked_in_audit_response(client: TestClient, db_session):
    """Verify that no sensitive configuration or secrets are leaked in audit responses."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    audit_resp = client.get(f"/transaction/{txn_id}/audit")
    raw_text = audit_resp.text

    forbidden_patterns = [
        "GEMINI_API_KEY",
        "RAZORPAY_TEST_KEY_SECRET",
        "rzp_test_secret",
        "AIzaSy",
        "password",
        "DATABASE_URL",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in raw_text


def test_audit_endpoint_is_strictly_read_only(client: TestClient, db_session):
    """Verify that calling audit endpoints does not modify database state or audit chain."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    events_before = db_session.query(AuditEvent).count()
    txns_before = db_session.query(Transaction).count()
    head_before = db_session.query(AuditChainState).filter_by(id=1).first().last_hash

    # Call audit endpoint multiple times
    for _ in range(3):
        res = client.get(f"/transaction/{txn_id}/audit")
        assert res.status_code == 200

    events_after = db_session.query(AuditEvent).count()
    txns_after = db_session.query(Transaction).count()
    head_after = db_session.query(AuditChainState).filter_by(id=1).first().last_hash

    assert events_before == events_after
    assert txns_before == txns_after
    assert head_before == head_after


def test_chain_verification_reflects_backend_tamper_detection(client: TestClient, db_session):
    """Verify chain_verified is True on untampered log, and False if tampering occurs."""
    prop_resp = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    txn_id = prop_resp.json()["data"]["transaction_id"]

    res1 = client.get(f"/transaction/{txn_id}/audit").json()["data"]
    assert res1["chain_verified"] is True
    assert res1["chain_verification_error"] is None

    # Tamper with an event in DB
    event = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).first()
    event.prev_hash = "f" * 64
    db_session.commit()

    res2 = client.get(f"/transaction/{txn_id}/audit").json()["data"]
    assert res2["chain_verified"] is False
    assert res2["chain_verification_error"] is not None
    assert "Tamper detected" in res2["chain_verification_error"]


def test_list_transactions_endpoint(client: TestClient, db_session):
    """Verify GET /transactions returns transactions ordered descending by created_at."""
    r1 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-002", "claimed_price": 2799.00, "quantity": 1},
        },
    )
    id1 = r1.json()["data"]["transaction_id"]

    r2 = client.post(
        "/transaction/propose",
        json={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "agent_claim": {"product_id": "prod-001", "claimed_price": 3499.00, "quantity": 1},
        },
    )
    id2 = r2.json()["data"]["transaction_id"]

    resp = client.get("/transactions")
    assert resp.status_code == 200
    txns = resp.json()["data"]
    assert len(txns) >= 2

    # id2 was created after id1, so it should appear before id1
    ids = [t["id"] for t in txns]
    idx1 = ids.index(id1)
    idx2 = ids.index(id2)
    assert idx2 < idx1

    # Verify audit chain integrity remains valid
    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None
