# pyrefly: ignore [missing-import]
import pytest

# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import AuditChainState, AuditEvent
from backend.app.services.audit_log import (
    GENESIS_PREV_HASH,
    compute_event_hash,
    compute_payload_hash,
    log_audit_event,
    verify_audit_chain,
)
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


def test_first_event_genesis_prev_hash(db_session):
    """First logged audit event uses genesis prev_hash (64 zeros)."""
    event = log_audit_event(
        db=db_session,
        event_type="PROPOSED",
        actor="agent",
        payload={"claimed_price": "2799.00"},
    )
    db_session.commit()

    assert event.prev_hash == GENESIS_PREV_HASH
    state = db_session.query(AuditChainState).filter_by(id=1).first()
    assert state is not None
    expected_hash = compute_event_hash(
        prev_hash=GENESIS_PREV_HASH,
        event_type="PROPOSED",
        actor="agent",
        transaction_id=None,
        payload_hash=compute_payload_hash({"claimed_price": "2799.00"}),
    )
    assert state.last_hash == expected_hash


def test_second_event_links_to_first(db_session):
    """Second logged audit event links to the first event's calculated chain hash."""
    e1 = log_audit_event(
        db=db_session,
        event_type="PROPOSED",
        actor="agent",
        payload={"claimed_price": "2799.00"},
    )
    db_session.commit()

    e1_hash = compute_event_hash(
        prev_hash=GENESIS_PREV_HASH,
        event_type="PROPOSED",
        actor="agent",
        transaction_id=None,
        payload_hash=e1.payload_hash,
    )

    e2 = log_audit_event(
        db=db_session,
        event_type="POLICY_DECISION",
        actor="firewall",
        payload={"decision": "ALLOW"},
    )
    db_session.commit()

    assert e2.prev_hash == e1_hash


def test_deterministic_payload_hashing():
    """compute_payload_hash is deterministic regardless of key ordering."""
    p1 = {"b": 2, "a": 1, "c": {"y": 20, "x": 10}}
    p2 = {"a": 1, "c": {"x": 10, "y": 20}, "b": 2}
    assert compute_payload_hash(p1) == compute_payload_hash(p2)


def test_multiple_sequential_events_and_verification(db_session):
    """Logging multiple sequential events creates an unbroken valid chain verified by verify_audit_chain."""
    for i in range(5):
        log_audit_event(
            db=db_session,
            event_type=f"TEST_EVENT_{i}",
            actor="test_actor",
            payload={"index": i},
        )
        db_session.commit()

    valid, err = verify_audit_chain(db_session)
    assert valid is True
    assert err is None


def test_verify_audit_chain_detects_payload_tampering(db_session):
    """Modifying an event payload_hash causes verify_audit_chain to report tamper evidence."""
    for i in range(3):
        log_audit_event(
            db=db_session,
            event_type=f"EVENT_{i}",
            actor="actor",
            payload={"val": i},
        )
        db_session.commit()

    # Tamper with event #1 in database
    event_1 = db_session.query(AuditEvent).filter_by(event_type="EVENT_1").first()
    assert event_1 is not None
    event_1.payload_hash = "f" * 64
    db_session.commit()

    valid, err = verify_audit_chain(db_session)
    assert valid is False
    assert err is not None
    assert "Tamper detected" in err or "head mismatch" in err


def test_verify_audit_chain_detects_prev_hash_tampering(db_session):
    """Modifying an event prev_hash causes verify_audit_chain to report tamper evidence."""
    for i in range(3):
        log_audit_event(
            db=db_session,
            event_type=f"EVENT_{i}",
            actor="actor",
            payload={"val": i},
        )
        db_session.commit()

    event_2 = db_session.query(AuditEvent).filter_by(event_type="EVENT_2").first()
    assert event_2 is not None
    event_2.prev_hash = "a" * 64
    db_session.commit()

    valid, err = verify_audit_chain(db_session)
    assert valid is False
    assert err is not None
    assert "Tamper detected" in err


def test_verify_audit_chain_detects_actor_tampering(db_session):
    """Modifying an event actor field causes verify_audit_chain to report tamper evidence."""
    for i in range(3):
        log_audit_event(
            db=db_session,
            event_type=f"EVENT_{i}",
            actor="valid_actor",
            payload={"val": i},
        )
        db_session.commit()

    event_1 = db_session.query(AuditEvent).filter_by(event_type="EVENT_1").first()
    assert event_1 is not None
    event_1.actor = "malicious_actor"
    db_session.commit()

    valid, err = verify_audit_chain(db_session)
    assert valid is False
    assert err is not None


def test_verify_audit_chain_detects_transaction_id_tampering(client: TestClient, db_session):
    """Modifying an event transaction_id field causes verify_audit_chain to report tamper evidence."""
    # Propose two transactions
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

    # Tamper with transaction_id on event for txn_1
    event_1 = db_session.query(AuditEvent).filter_by(transaction_id=txn_id_1).first()
    assert event_1 is not None
    event_1.transaction_id = txn_id_2
    db_session.commit()

    valid, err = verify_audit_chain(db_session)
    assert valid is False
    assert err is not None


def test_audit_event_rollback_on_db_failure(db_session):
    """Transaction rollback cleanly removes pending audit events and leaves chain state unchanged."""
    log_audit_event(
        db=db_session,
        event_type="COMMITTED",
        actor="system",
        payload={"status": "ok"},
    )
    db_session.commit()

    state_before = db_session.query(AuditChainState).filter_by(id=1).first().last_hash

    log_audit_event(
        db=db_session,
        event_type="UNCOMMITTED",
        actor="system",
        payload={"status": "fail"},
    )
    db_session.rollback()

    state_after = db_session.query(AuditChainState).filter_by(id=1).first().last_hash
    assert state_after == state_before

    uncommitted = (
        db_session.query(AuditEvent).filter_by(event_type="UNCOMMITTED").first()
    )
    assert uncommitted is None


def test_audit_integration_propose_endpoint(client: TestClient, db_session):
    """POST /transaction/propose automatically logs PROPOSED and POLICY_DECISION audit events."""
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
    txn_id = response.json()["data"]["transaction_id"]

    events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    assert len(events) == 2
    event_types = [e.event_type for e in events]
    assert "PROPOSED" in event_types
    assert "POLICY_DECISION" in event_types

    valid, _err = verify_audit_chain(db_session)
    assert valid is True


def test_audit_integration_approve_and_execute(client: TestClient, db_session):
    """Full proposal -> approve -> execute flow generates valid audit chain."""
    # 1. Propose over-budget
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

    # 2. Approve
    appr_resp = client.post(f"/transaction/{txn_id}/approve")
    assert appr_resp.status_code == 200

    # 3. Execute
    exec_resp = client.post(
        "/transaction/execute",
        json={"transaction_id": txn_id, "idempotency_key": "audit-flow-001"},
    )
    assert exec_resp.status_code == 200

    events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    event_types = [e.event_type for e in events]
    assert "PROPOSED" in event_types
    assert "POLICY_DECISION" in event_types
    assert "APPROVED" in event_types
    assert "EXECUTING" in event_types
    assert "EXECUTED" in event_types

    valid, _err = verify_audit_chain(db_session)
    assert valid is True


def test_audit_integration_rejection_flow(client: TestClient, db_session):
    """Proposal -> reject flow logs PROPOSED, POLICY_DECISION, and REJECTED audit events."""
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

    rej_resp = client.post(f"/transaction/{txn_id}/reject")
    assert rej_resp.status_code == 200

    events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    event_types = [e.event_type for e in events]
    assert "PROPOSED" in event_types
    assert "POLICY_DECISION" in event_types
    assert "REJECTED" in event_types

    valid, _err = verify_audit_chain(db_session)
    assert valid is True


def test_audit_client_injection_protection(client: TestClient, db_session):
    """Injecting audit fields in request payload has 0 effect on audit actor, prev_hash, or event hash."""
    payload = {
        "user_id": "user-001",
        "mandate_id": "mandate-001",
        "prev_hash": "0" * 64,
        "payload_hash": "injected",
        "actor": "attacker",
        "agent_claim": {
            "product_id": "prod-002",
            "claimed_price": 2799.00,
            "quantity": 1,
        },
    }
    response = client.post("/transaction/propose", json=payload)
    assert response.status_code == 200
    txn_id = response.json()["data"]["transaction_id"]

    events = db_session.query(AuditEvent).filter_by(transaction_id=txn_id).all()
    assert len(events) == 2
    for event in events:
        assert event.actor in ("agent", "firewall")
        assert event.actor != "attacker"

    valid, _err = verify_audit_chain(db_session)
    assert valid is True
