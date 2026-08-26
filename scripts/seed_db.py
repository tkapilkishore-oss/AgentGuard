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


def seed_database(db: Session, reset: bool = False) -> None:
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
    except Exception:
        db.rollback()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed database for AgentGuard")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database tables before re-seeding",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        seed_database(db, reset=args.reset)
        mode = "Reset & Seed" if args.reset else "Seed (Idempotent)"
        print(f"[{mode}] Database seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
