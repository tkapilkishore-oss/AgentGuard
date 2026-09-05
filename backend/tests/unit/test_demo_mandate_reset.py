from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from backend.app.db.session import SessionLocal, get_db
from backend.app.main import app
from backend.app.models import Mandate, AuditEvent, Transaction
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


def test_demo_reset_unauthorized_missing_header(client: TestClient):
    """Verify that calling /internal/demo/reset-mandate without authorization header returns 403."""
    resp = client.post("/internal/demo/reset-mandate")
    assert resp.status_code == 403
    data = resp.json()
    assert data.get("detail") == "DEMO_CONTROL_UNAUTHORIZED" or (
        data.get("error") and data["error"].get("message") == "DEMO_CONTROL_UNAUTHORIZED"
    )


def test_demo_reset_unauthorized_invalid_header(client: TestClient):
    """Verify that calling /internal/demo/reset-mandate with an invalid header returns 403."""
    resp = client.post(
        "/internal/demo/reset-mandate",
        headers={"X-Demo-Control": "unauthorized-header-value"},
    )
    assert resp.status_code == 403


def test_demo_reset_success_restores_clean_state(client: TestClient, db_session):
    """Verify that /internal/demo/reset-mandate restores mandate-001 to clean ₹3,000 state."""
    # 1. Simulate consumed and revoked state (e.g. after demo run)
    mandate = db_session.query(Mandate).filter_by(id="mandate-001").first()
    assert mandate is not None
    mandate.budget_remaining = Decimal("201.00")
    mandate.status = "revoked"
    db_session.commit()

    # Capture initial audit event count
    initial_audit_count = db_session.query(AuditEvent).count()

    # 2. Call reset-mandate with exact internal demo header
    resp = client.post(
        "/internal/demo/reset-mandate",
        headers={"X-Demo-Control": "agentguard-autonomous-demo"},
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data.get("success") is True
    data = res_data["data"]

    assert data["mandate_id"] == "mandate-001"
    assert data["status"] == "active"
    assert data["budget_total"] == "3000.00"
    assert data["budget_remaining"] == "3000.00"
    assert data["max_transaction_amount"] == "3000.00"

    # 3. Verify database state
    db_session.refresh(mandate)
    assert mandate.status == "active"
    assert mandate.budget_total == Decimal("3000.00")
    assert mandate.budget_remaining == Decimal("3000.00")
    assert mandate.max_transaction_amount == Decimal("3000.00")

    # 4. Verify audit trail appended MANDATE_DEMO_RESET event
    current_audit_count = db_session.query(AuditEvent).count()
    assert current_audit_count == initial_audit_count + 1

    latest_audit = (
        db_session.query(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .first()
    )
    assert latest_audit.event_type == "MANDATE_DEMO_RESET"
    assert latest_audit.actor == "demo_controller"

    # 5. Verify cryptographic chain integrity remains intact
    chain_valid, broken_id = verify_audit_chain(db_session)
    assert chain_valid is True, f"Audit chain broke at event {broken_id}"


def test_demo_reset_does_not_mutate_transactions(client: TestClient, db_session):
    """Verify that resetting mandate-001 does not delete or alter transactions."""
    initial_txns = db_session.query(Transaction).count()

    resp = client.post(
        "/internal/demo/reset-mandate",
        headers={"X-Demo-Control": "agentguard-autonomous-demo"},
    )
    assert resp.status_code == 200

    after_txns = db_session.query(Transaction).count()
    assert after_txns == initial_txns, "Reset must not delete transactions"
