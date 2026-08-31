"""Unit tests for LiveRuntimeBridge and zero-business-logic duplication live state queries."""

import pytest
from sqlalchemy.orm import Session

from backend.app.conversational.live_bridge import LiveRuntimeBridge
from backend.app.conversational.models import LiveToolRequest, LiveToolType
from backend.app.db.session import SessionLocal
from scripts.seed_db import seed_database


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        seed_database(session)
        yield session
    finally:
        session.close()


@pytest.fixture
def live_bridge():
    return LiveRuntimeBridge()


def test_live_mandate_budget_query(live_bridge, db: Session):
    """Verify live mandate budget returns authoritative values from PostgreSQL."""
    req = LiveToolRequest(
        tool_type=LiveToolType.MANDATE_BUDGET,
        parameters={"mandate_id": "mandate-001"},
        reason="Querying active balance",
    )
    result = live_bridge.execute_live_tool(req, db=db)
    assert result.success is True
    assert result.data["found"] is True
    assert result.data["budget_remaining"] == "3000.00"
    assert result.data["status"] == "active"


def test_live_product_affordability_query(live_bridge, db: Session):
    """Verify budget shortfall calculation against product catalog."""
    req = LiveToolRequest(
        tool_type=LiveToolType.MANDATE_BUDGET,
        parameters={"mandate_id": "mandate-001", "product_id": "prod-001"},
        reason="Check if mandate can afford earbuds",
    )
    result = live_bridge.execute_live_tool(req, db=db)
    assert result.success is True
    affordability = result.data["product_affordability"]
    assert affordability is not None
    assert affordability["product_name"] == "Wireless Earbuds"
    assert affordability["is_affordable"] is False
    assert affordability["shortfall"] == "499.00"


def test_live_product_catalog_query(live_bridge, db: Session):
    """Verify product catalog queries active inventory."""
    req = LiveToolRequest(
        tool_type=LiveToolType.PRODUCT_CATALOG,
        parameters={},
        reason="List catalog products",
    )
    result = live_bridge.execute_live_tool(req, db=db)
    assert result.success is True
    assert result.data["active_count"] >= 3


def test_live_audit_chain_verification_query(live_bridge, db: Session):
    """Verify live cryptographic SHA-256 audit chain check."""
    req = LiveToolRequest(
        tool_type=LiveToolType.AUDIT_CHAIN_INTEGRITY,
        parameters={},
        reason="Verify audit chain integrity",
    )
    result = live_bridge.execute_live_tool(req, db=db)
    assert result.success is True
    assert result.data["chain_valid"] is True
    assert result.data["status"] == "VALID_TAMPER_PROOF"
