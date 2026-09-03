#!/usr/bin/env python3
"""Seed database script for AgentGuard / Agentic Commerce Firewall.

Populates PostgreSQL with exact reproducible seed data defined in docs/SEED_DATA.md.

Usage:
    python scripts/seed_db.py          # Idempotent upsert of seed data
    python scripts/seed_db.py --reset  # Clean reset of all tables before re-seeding
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Ensure project root is in sys.path for backend package imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
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


from backend.app.services.audit_log import log_audit_event


def reset_database(db: Session) -> None:
    """Safely clear operational and core entities without dropping schema."""
    db.query(AuditEvent).delete()
    db.query(AuditChainState).delete()
    db.query(IdempotencyRecord).delete()
    db.query(Approval).delete()
    db.query(Transaction).delete()
    db.query(Mandate).delete()
    db.query(Product).delete()
    db.query(Merchant).delete()
    db.query(User).delete()
    db.flush()
    db.expunge_all()


def seed_database(db: Session, reset: bool = False, demo: bool = False) -> None:
    """Seed database with exact entities from docs/SEED_DATA.md."""
    try:
        if reset:
            reset_database(db)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=24)

        # 1. Independent entities: Users & Merchants
        users = [
            User(
                id="user-001",
                name="Demo User",
                email="demo@example.com",
                created_at=now,
            )
        ]
        for u in users:
            db.merge(u)

        merchants = [
            Merchant(
                id="merchant-001",
                name="AudioHub",
                category="electronics",
                status="active",
            ),
            Merchant(
                id="merchant-002",
                name="ShadyGoods",
                category="electronics",
                status="active",
            ),
        ]
        for m in merchants:
            db.merge(m)

        # Flush users and merchants to satisfy FK constraints for products and mandates
        db.flush()

        # 2. Dependent entities: Products (FK -> Merchants) & Mandates (FK -> Users)
        products = [
            Product(
                id="prod-001",
                merchant_id="merchant-001",
                name="Wireless Earbuds",
                price=Decimal("3499.00"),
                currency="INR",
                stock=50,
                active=True,
            ),
            Product(
                id="prod-002",
                merchant_id="merchant-001",
                name="Bluetooth Speaker",
                price=Decimal("2799.00"),
                currency="INR",
                stock=30,
                active=True,
            ),
            Product(
                id="prod-003",
                merchant_id="merchant-002",
                name="Studio Headphones",
                price=Decimal("5999.00"),
                currency="INR",
                stock=10,
                active=True,
            ),
        ]
        for p in products:
            db.merge(p)

        mandates = [
            Mandate(
                id="mandate-001",
                user_id="user-001",
                budget_total=Decimal("3000.00"),
                budget_remaining=Decimal("3000.00"),
                merchant_scope="merchant-001",
                category_scope=None,
                max_transaction_amount=Decimal("3000.00"),
                status="active",
                created_at=now,
                expires_at=expires_at,
            )
        ]
        for mand in mandates:
            db.merge(mand)

        db.commit()

        if demo:
            seed_demo_transactions(db)

    except Exception:
        db.rollback()
        raise


def seed_demo_transactions(db: Session) -> None:
    """Seeds canonical demonstration transactions with valid SHA-256 cryptographic audit chains."""
    now = datetime.now(timezone.utc)
    t1_time = now - timedelta(minutes=45)
    t2_time = now - timedelta(minutes=30)
    t3_time = now - timedelta(minutes=15)

    # 1. Transaction 1: Happy Path Purchase (Bluetooth Speaker @ ₹2,799.00 - SUCCESS)
    txn1_id = "d1010000-0000-4000-8000-000000000001"
    txn1 = Transaction(
        id=txn1_id,
        mandate_id="mandate-001",
        user_id="user-001",
        merchant_id="merchant-001",
        product_id="prod-002",
        claimed_price=Decimal("2799.00"),
        authoritative_price=Decimal("2799.00"),
        quantity=1,
        authoritative_total=Decimal("2799.00"),
        status="SUCCESS",
        reason_code="ALLOW",
        nonce="demo-nonce-speaker-001",
        idempotency_key="idemp-demo-speaker-001",
        created_at=t1_time,
        expires_at=t1_time + timedelta(minutes=5),
        executed_at=t1_time + timedelta(seconds=2),
    )
    db.merge(txn1)
    db.flush()

    log_audit_event(
        db=db,
        event_type="PROPOSED",
        actor="agent",
        transaction_id=txn1_id,
        payload={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "product_id": "prod-002",
            "claimed_price": "2799.00",
            "quantity": 1,
        },
    )
    log_audit_event(
        db=db,
        event_type="POLICY_DECISION",
        actor="firewall",
        transaction_id=txn1_id,
        payload={
            "decision": "ALLOW",
            "reason_code": "ALLOW",
            "authoritative_price": "2799.00",
            "authoritative_total": "2799.00",
        },
    )
    log_audit_event(
        db=db,
        event_type="EXECUTING",
        actor="firewall",
        transaction_id=txn1_id,
        payload={"authoritative_total": "2799.00"},
    )
    log_audit_event(
        db=db,
        event_type="EXECUTED",
        actor="razorpay",
        transaction_id=txn1_id,
        payload={
            "status": "SUCCESS",
            "razorpay_payment_id": "pay_rzp_demo_speaker01",
            "authoritative_total": "2799.00",
        },
    )

    # 2. Transaction 2: Price Tampering Attack Blocked (Wireless Earbuds claimed ₹1,999 vs ₹3,499 - DENIED)
    txn2_id = "d1020000-0000-4000-8000-000000000002"
    txn2 = Transaction(
        id=txn2_id,
        mandate_id="mandate-001",
        user_id="user-001",
        merchant_id="merchant-001",
        product_id="prod-001",
        claimed_price=Decimal("1999.00"),
        authoritative_price=Decimal("3499.00"),
        quantity=1,
        authoritative_total=Decimal("3499.00"),
        status="DENIED",
        reason_code="PRICE_MISMATCH",
        nonce="demo-nonce-earbuds-tampered",
        idempotency_key=None,
        created_at=t2_time,
        expires_at=t2_time + timedelta(minutes=5),
        executed_at=None,
    )
    db.merge(txn2)
    db.flush()

    log_audit_event(
        db=db,
        event_type="PROPOSED",
        actor="agent",
        transaction_id=txn2_id,
        payload={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "product_id": "prod-001",
            "claimed_price": "1999.00",
            "quantity": 1,
        },
    )
    log_audit_event(
        db=db,
        event_type="POLICY_DECISION",
        actor="firewall",
        transaction_id=txn2_id,
        payload={
            "decision": "DENY",
            "reason_code": "PRICE_MISMATCH",
            "claimed_price": "1999.00",
            "authoritative_price": "3499.00",
        },
    )

    # 3. Transaction 3: Over-Budget Escalation with Human Approval (Wireless Earbuds @ ₹3,499 - SUCCESS)
    txn3_id = "d1030000-0000-4000-8000-000000000003"
    txn3 = Transaction(
        id=txn3_id,
        mandate_id="mandate-001",
        user_id="user-001",
        merchant_id="merchant-001",
        product_id="prod-001",
        claimed_price=Decimal("3499.00"),
        authoritative_price=Decimal("3499.00"),
        quantity=1,
        authoritative_total=Decimal("3499.00"),
        status="SUCCESS",
        reason_code="APPROVED_BY_HUMAN",
        nonce="demo-nonce-earbuds-approved",
        idempotency_key="idemp-demo-earbuds-003",
        created_at=t3_time,
        expires_at=t3_time + timedelta(minutes=5),
        executed_at=t3_time + timedelta(seconds=10),
    )
    db.merge(txn3)
    db.flush()

    appr3 = Approval(
        id=str(uuid.uuid4()),
        transaction_id=txn3_id,
        status="approved",
        approver_id="human-supervisor",
        created_at=t3_time + timedelta(seconds=3),
        resolved_at=t3_time + timedelta(seconds=6),
    )
    db.merge(appr3)
    db.flush()

    log_audit_event(
        db=db,
        event_type="PROPOSED",
        actor="agent",
        transaction_id=txn3_id,
        payload={
            "user_id": "user-001",
            "mandate_id": "mandate-001",
            "product_id": "prod-001",
            "claimed_price": "3499.00",
            "quantity": 1,
        },
    )
    log_audit_event(
        db=db,
        event_type="POLICY_DECISION",
        actor="firewall",
        transaction_id=txn3_id,
        payload={
            "decision": "ESCALATE",
            "reason_code": "BUDGET_EXCEEDED",
            "authoritative_price": "3499.00",
            "authoritative_total": "3499.00",
        },
    )
    log_audit_event(
        db=db,
        event_type="APPROVED",
        actor="human",
        transaction_id=txn3_id,
        payload={
            "approver_id": "human-supervisor",
            "status": "approved",
            "reason_code": "APPROVED_BY_HUMAN",
        },
    )
    log_audit_event(
        db=db,
        event_type="EXECUTING",
        actor="firewall",
        transaction_id=txn3_id,
        payload={"authoritative_total": "3499.00"},
    )
    log_audit_event(
        db=db,
        event_type="EXECUTED",
        actor="razorpay",
        transaction_id=txn3_id,
        payload={
            "status": "SUCCESS",
            "razorpay_payment_id": "pay_rzp_demo_earbuds03",
            "authoritative_total": "3499.00",
        },
    )

    # Ensure mandate budget remains active at ₹3,000.00 for interactive demo scenarios
    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    if mandate:
        mandate.budget_total = Decimal("3000.00")
        mandate.budget_remaining = Decimal("3000.00")
        mandate.status = "active"

    db.commit()


def seed_demo_state(db: Session, reset: bool = False) -> None:
    """Convenience helper to seed the complete demo-ready application state."""
    seed_database(db, reset=reset, demo=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database for AgentGuard")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database tables before re-seeding",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Seed only core catalog and mandate entities without demo transactions",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        is_demo = not args.core_only
        seed_database(db, reset=args.reset, demo=is_demo)
        mode = "Reset & Seed" if args.reset else "Seed (Idempotent)"
        state_type = "DEMO-READY" if is_demo else "CORE-ONLY"
        print(f"[{mode} - {state_type}] Database seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

