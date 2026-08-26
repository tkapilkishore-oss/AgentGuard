import os
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text

from backend.app.db.session import SessionLocal, engine, get_db
from backend.app.models import (
    Approval,
    AuditChainState,
    AuditEvent,
    IdempotencyRecord,
    Mandate,
    Merchant,
    Product,
    Transaction,
    User,
)


def test_database_connectivity():
    """Verify database connection and SELECT 1 query."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1


def test_session_lifecycle():
    """Verify SessionLocal and get_db generator lifecycle."""
    session = SessionLocal()
    try:
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        session.close()

    # Test get_db generator
    gen = get_db()
    db_session = next(gen)
    assert db_session is not None
    assert db_session.execute(text("SELECT 1")).scalar() == 1
    with pytest.raises(StopIteration):
        next(gen)


def test_nine_tables_exist_in_postgres():
    """Verify all 9 required Stage 2A tables exist in PostgreSQL catalog."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = {
        "users",
        "merchants",
        "products",
        "mandates",
        "transactions",
        "approvals",
        "idempotency_records",
        "audit_events",
        "audit_chain_state",
    }

    for table in expected_tables:
        assert table in tables, f"Table {table} missing from PostgreSQL database catalog"


def test_monetary_column_types_numeric():
    """Verify monetary columns in PostgreSQL are NUMERIC(10,2) and not float."""
    inspector = inspect(engine)

    monetary_checks = [
        ("products", "price"),
        ("mandates", "budget_total"),
        ("mandates", "budget_remaining"),
        ("mandates", "max_transaction_amount"),
        ("transactions", "claimed_price"),
        ("transactions", "authoritative_price"),
        ("transactions", "authoritative_total"),
    ]

    for table_name, column_name in monetary_checks:
        columns = inspector.get_columns(table_name)
        col_def = next((c for c in columns if c["name"] == column_name), None)
        assert col_def is not None, f"Column {column_name} missing from table {table_name}"
        col_type = str(col_def["type"]).upper()
        assert "NUMERIC" in col_type or "DECIMAL" in col_type, (
            f"Column {table_name}.{column_name} is type {col_type}, expected NUMERIC(10,2)"
        )


def test_foreign_key_constraints():
    """Verify foreign keys exist in PostgreSQL catalog."""
    inspector = inspect(engine)

    fk_checks = [
        ("products", "merchants", "merchant_id"),
        ("mandates", "users", "user_id"),
        ("transactions", "mandates", "mandate_id"),
        ("transactions", "users", "user_id"),
        ("transactions", "merchants", "merchant_id"),
        ("transactions", "products", "product_id"),
        ("approvals", "transactions", "transaction_id"),
        ("idempotency_records", "transactions", "transaction_id"),
        ("audit_events", "transactions", "transaction_id"),
    ]

    for table_name, target_table, fk_column in fk_checks:
        fks = inspector.get_foreign_keys(table_name)
        matching_fk = next(
            (
                fk for fk in fks
                if fk["referred_table"] == target_table and fk_column in fk["constrained_columns"]
            ),
            None,
        )
        assert matching_fk is not None, (
            f"Missing foreign key on {table_name}.{fk_column} -> {target_table}.id"
        )


def test_idempotency_key_uniqueness_semantics():
    """Critical Security Verification:
    - idempotency_records.idempotency_key MUST be Primary Key / Unique.
    - transactions.idempotency_key MUST NOT be Unique.
    """
    inspector = inspect(engine)

    # 1. Check idempotency_records primary key
    idem_pk = inspector.get_pk_constraint("idempotency_records")
    assert "idempotency_key" in idem_pk["constrained_columns"], (
        "idempotency_records.idempotency_key must be Primary Key"
    )

    # 2. Check transactions.idempotency_key is NOT unique
    txn_pk = inspector.get_pk_constraint("transactions")
    assert "idempotency_key" not in txn_pk["constrained_columns"], (
        "transactions.idempotency_key must NOT be Primary Key"
    )

    txn_indexes = inspector.get_indexes("transactions")
    unique_idem_idx = next(
        (
            idx for idx in txn_indexes
            if idx["unique"] and "idempotency_key" in idx["column_names"]
        ),
        None,
    )
    assert unique_idem_idx is None, (
        "transactions.idempotency_key must NOT have a UNIQUE index"
    )


def test_orm_models_instantiation():
    """Verify ORM model classes map cleanly and instantiate without errors."""
    now = datetime.now(timezone.utc)
    u = User(id="u1", name="Test User", email="test@example.com", created_at=now)
    m = Merchant(id="m1", name="Test Merchant", category="electronics", status="active")
    p = Product(id="p1", merchant_id="m1", name="Test Product", price=Decimal("100.00"), stock=10)
    mandate = Mandate(
        id="man1",
        user_id="u1",
        budget_total=Decimal("500.00"),
        budget_remaining=Decimal("500.00"),
        max_transaction_amount=Decimal("500.00"),
        status="active",
        expires_at=now,
    )
    t = Transaction(
        id="t1",
        mandate_id="man1",
        user_id="u1",
        merchant_id="m1",
        product_id="p1",
        claimed_price=Decimal("100.00"),
        authoritative_price=Decimal("100.00"),
        quantity=1,
        authoritative_total=Decimal("100.00"),
        status="proposed",
        reason_code="ALLOW",
        nonce="nonce123",
        expires_at=now,
    )
    appr = Approval(id="a1", transaction_id="t1", status="pending")
    idem = IdempotencyRecord(idempotency_key="ik1", transaction_id="t1", response_snapshot={"status": "success"})
    ae = AuditEvent(
        id="ae1",
        transaction_id="t1",
        event_type="PROPOSED",
        actor="firewall",
        payload_hash="hash1",
        prev_hash="hash0",
    )
    acs = AuditChainState(id=1, last_hash="hash0")

    assert u.__tablename__ == "users"
    assert m.__tablename__ == "merchants"
    assert p.__tablename__ == "products"
    assert mandate.__tablename__ == "mandates"
    assert t.__tablename__ == "transactions"
    assert appr.__tablename__ == "approvals"
    assert idem.__tablename__ == "idempotency_records"
    assert ae.__tablename__ == "audit_events"
    assert acs.__tablename__ == "audit_chain_state"


def test_secret_hygiene():
    """Verify secrets are not hardcoded or tracked in git."""
    gitignore_path = ".gitignore"
    assert os.path.exists(gitignore_path)
    with open(gitignore_path, "r") as f:
        content = f.read()
        assert ".env" in content

    env_example_path = ".env.example"
    assert os.path.exists(env_example_path)
    with open(env_example_path, "r") as f:
        env_example = f.read()
        assert "postgresql://" in env_example
        assert "RAZORPAY_SECRET" not in env_example
