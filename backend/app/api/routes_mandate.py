from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.schemas import ApiResponse
from backend.app.db.session import get_db
from backend.app.models import Mandate, Product
from backend.app.services.audit_log import log_audit_event

router = APIRouter()


@router.post("/internal/demo/reset-mandate", response_model=ApiResponse[dict[str, Any]])
def reset_demo_mandate(
    x_demo_control: str | None = Header(default=None),
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[dict[str, Any]]:
    """Internal demo-only controller: safely restores clean prerequisite state for mandate-001."""
    if x_demo_control != "agentguard-autonomous-demo":
        raise HTTPException(status_code=403, detail="DEMO_CONTROL_UNAUTHORIZED")

    mandate = db.query(Mandate).filter_by(id="mandate-001").first()
    if not mandate:
        raise HTTPException(status_code=404, detail="MANDATE_NOT_FOUND")

    now = datetime.now(timezone.utc)
    mandate.status = "active"
    mandate.budget_total = Decimal("3000.00")
    mandate.budget_remaining = Decimal("3000.00")
    mandate.max_transaction_amount = Decimal("3000.00")

    # Ensure expiry is safely in the future (at least 7 days ahead)
    min_future = now + timedelta(days=7)
    current_exp = (
        mandate.expires_at.replace(tzinfo=timezone.utc)
        if mandate.expires_at.tzinfo is None
        else mandate.expires_at
    )
    if current_exp < min_future:
        mandate.expires_at = now + timedelta(days=30)

    try:
        log_audit_event(
            db=db,
            event_type="MANDATE_DEMO_RESET",
            actor="demo_controller",
            transaction_id=None,
            payload={
                "mandate_id": mandate.id,
                "user_id": mandate.user_id,
                "status": "active",
                "budget_total": "3000.00",
                "budget_remaining": "3000.00",
                "max_transaction_amount": "3000.00",
                "reason": "autonomous_demo_lifecycle",
            },
        )
        db.commit()
        db.refresh(mandate)
    except Exception:
        db.rollback()
        raise

    return ApiResponse.ok(
        {
            "mandate_id": mandate.id,
            "status": mandate.status,
            "budget_total": str(mandate.budget_total),
            "budget_remaining": str(mandate.budget_remaining),
            "max_transaction_amount": str(mandate.max_transaction_amount),
            "expires_at": mandate.expires_at.isoformat() if mandate.expires_at else None,
        }
    )


@router.post("/mandate/{mandate_id}/revoke", response_model=ApiResponse[dict[str, Any]])
def revoke_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[dict[str, Any]]:
    """Revoke an active mandate by ID."""
    mandate = db.query(Mandate).filter_by(id=mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="MANDATE_NOT_FOUND")

    mandate.status = "revoked"
    try:
        log_audit_event(
            db=db,
            event_type="MANDATE_REVOKED",
            actor="user",
            transaction_id=None,
            payload={
                "mandate_id": mandate.id,
                "user_id": mandate.user_id,
                "status": "revoked",
            },
        )
        db.commit()
        db.refresh(mandate)
    except Exception:
        db.rollback()
        raise

    return ApiResponse.ok(
        {
            "mandate_id": mandate.id,
            "status": mandate.status,
            "budget_remaining": str(mandate.budget_remaining),
        }
    )


@router.get("/mandate/{mandate_id}", response_model=ApiResponse[dict[str, Any]])
def get_mandate(
    mandate_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[dict[str, Any]]:
    """Fetch mandate details and remaining budget."""
    mandate = db.query(Mandate).filter_by(id=mandate_id).first()
    if not mandate:
        raise HTTPException(status_code=404, detail="MANDATE_NOT_FOUND")

    return ApiResponse.ok(
        {
            "id": mandate.id,
            "user_id": mandate.user_id,
            "budget_total": str(mandate.budget_total),
            "budget_remaining": str(mandate.budget_remaining),
            "merchant_scope": mandate.merchant_scope,
            "max_transaction_amount": str(mandate.max_transaction_amount),
            "status": mandate.status,
            "expires_at": mandate.expires_at.isoformat() if mandate.expires_at else None,
        }
    )


@router.get("/products", response_model=ApiResponse[list[dict[str, Any]]])
def list_products(
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[list[dict[str, Any]]]:
    """Fetch product catalog for shopping agent and frontend UI."""
    products = db.query(Product).filter_by(active=True).all()
    catalog = [
        {
            "id": p.id,
            "merchant_id": p.merchant_id,
            "name": p.name,
            "price": str(p.price),
            "currency": p.currency,
            "stock": p.stock,
        }
        for p in products
    ]
    return ApiResponse.ok(catalog)
