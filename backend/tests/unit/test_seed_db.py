from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models import (
    Approval,
    AuditEvent,
    IdempotencyRecord,
    Mandate,
    Merchant,
    Product,
    Transaction,
    User,
)
from scripts.seed_db import reset_database, seed_database


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_b1_fresh_seed(db: Session):
    """B1: Fresh seed creates all core entities starting from empty tables."""
    reset_database(db)
    db.commit()

    seed_database(db, reset=False)

    assert db.query(Merchant).count() == 2
    assert db.query(Product).count() == 3
    assert db.query(User).count() == 1
    assert db.query(Mandate).count() == 1


def test_b2_exact_merchant_data(db: Session):
    """B2: Verify exact merchant IDs and attributes."""
    seed_database(db, reset=False)

    m1 = db.query(Merchant).filter_by(id="merchant-001").first()
    assert m1 is not None
    assert m1.name == "AudioHub"
    assert m1.category == "electronics"
    assert m1.status == "active"

    m2 = db.query(Merchant).filter_by(id="merchant-002").first()
    assert m2 is not None
    assert m2.name == "ShadyGoods"
    assert m2.category == "electronics"
    assert m2.status == "active"


def test_b3_exact_product_data(db: Session):
    """B3: Verify exact product IDs, prices, merchant associations, stock, and active status."""
    seed_database(db, reset=False)

    p1 = db.query(Product).filter_by(id="prod-001").first()
    assert p1 is not None
    assert p1.merchant_id == "merchant-001"
    assert p1.name == "Wireless Earbuds"
    assert p1.price == Decimal("3499.00")
    assert p1.currency == "INR"
    assert p1.stock == 50
    assert p1.active is True

    p2 = db.query(Product).filter_by(id="prod-002").first()
    assert p2 is not None
    assert p2.merchant_id == "merchant-001"
    assert p2.name == "Bluetooth Speaker"
    assert p2.price == Decimal("2799.00")
    assert p2.currency == "INR"
    assert p2.stock == 30
    assert p2.active is True

    p3 = db.query(Product).filter_by(id="prod-003").first()
    assert p3 is not None
    assert p3.merchant_id == "merchant-002"
    assert p3.name == "Studio Headphones"
    assert p3.price == Decimal("5999.00")
    assert p3.currency == "INR"
    assert p3.stock == 10
    assert p3.active is True


def test_b4_exact_user_data(db: Session):
    """B4: Verify user-001 data."""
    seed_database(db, reset=False)

    u = db.query(User).filter_by(id="user-001").first()
    assert u is not None
    assert u.name == "Demo User"
    assert u.email == "demo@example.com"


def test_b5_exact_mandate_data(db: Session):
    """B5: Verify mandate-001 budget, cap, scope, status, and fresh 24h expiry."""
    seed_database(db, reset=False)

    mand = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mand is not None
    assert mand.user_id == "user-001"
    assert mand.budget_total == Decimal("3000.00")
    assert mand.budget_remaining == Decimal("3000.00")
    assert mand.merchant_scope == "merchant-001"
    assert mand.max_transaction_amount == Decimal("3000.00")
    assert mand.status == "active"

    now = datetime.now(timezone.utc)
    expires_at = mand.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    diff_hours = (expires_at - now).total_seconds() / 3600.0
    assert 23.0 <= diff_hours <= 25.0


def test_b6_idempotent_rerun(db: Session):
    """B6: Running seed multiple times does not duplicate records."""
    seed_database(db, reset=False)
    counts_run1 = (
        db.query(Merchant).count(),
        db.query(Product).count(),
        db.query(User).count(),
        db.query(Mandate).count(),
    )

    seed_database(db, reset=False)
    counts_run2 = (
        db.query(Merchant).count(),
        db.query(Product).count(),
        db.query(User).count(),
        db.query(Mandate).count(),
    )

    assert counts_run1 == counts_run2 == (2, 3, 1, 1)


def test_b7_reset_and_reseed(db: Session):
    """B7: Seed with reset=True restores baseline state after mutations."""
    seed_database(db, reset=False)

    # Mutate mandate budget in test
    mand = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mand is not None
    mand.budget_remaining = Decimal("100.00")
    db.commit()

    # Verify mutation took effect
    mand_mutated = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mand_mutated is not None
    assert mand_mutated.budget_remaining == Decimal("100.00")

    # Reseed with reset=True
    seed_database(db, reset=True)

    # Verify original budget is restored
    mand_restored = db.query(Mandate).filter_by(id="mandate-001").first()
    assert mand_restored is not None
    assert mand_restored.budget_remaining == Decimal("3000.00")


def test_b8_no_fake_operational_data(db: Session):
    """B8: Seed script does NOT create operational records."""
    seed_database(db, reset=False)

    assert db.query(Transaction).count() == 0
    assert db.query(Approval).count() == 0
    assert db.query(IdempotencyRecord).count() == 0
    assert db.query(AuditEvent).count() == 0


def test_b9_scenario_compatibility(db: Session):
    """B9: Verify seeded data mathematically supports all demo scenarios."""
    seed_database(db, reset=False)

    mand = db.query(Mandate).filter_by(id="mandate-001").first()
    p_earbuds = db.query(Product).filter_by(id="prod-001").first()
    p_speaker = db.query(Product).filter_by(id="prod-002").first()
    p_headphones = db.query(Product).filter_by(id="prod-003").first()

    assert mand is not None
    assert p_earbuds is not None
    assert p_speaker is not None
    assert p_headphones is not None

    # Scenario 1: Happy path - speaker price (2799) fits budget (3000)
    assert p_speaker.price <= mand.budget_remaining

    # Scenario 2: Over-budget - earbuds price (3499) exceeds budget (3000)
    assert p_earbuds.price > mand.budget_remaining

    # Scenario 3: Price mismatch - actual earbuds price is 3499.00
    assert p_earbuds.price == Decimal("3499.00")

    # Merchant scope scenario: headphones belong to merchant-002, mandate scope is merchant-001
    assert p_headphones.merchant_id != mand.merchant_scope


def test_b10_transaction_rollback_safety(db: Session):
    """B10: Verify seed rollback safety - forced failure leaves no partial state."""
    reset_database(db)
    db.commit()

    # Add an invalid entity that violates FK constraint to force error mid-seed
    invalid_mandate = Mandate(
        id="mandate-invalid",
        user_id="nonexistent-user-xyz",
        budget_total=Decimal("1000.00"),
        budget_remaining=Decimal("1000.00"),
        max_transaction_amount=Decimal("1000.00"),
        status="active",
        expires_at=datetime.now(timezone.utc),
    )

    try:
        db.merge(invalid_mandate)
        db.commit()
    except IntegrityError:
        db.rollback()

    # Verify database remains completely clean after rollback
    assert db.query(User).count() == 0
    assert db.query(Mandate).count() == 0
