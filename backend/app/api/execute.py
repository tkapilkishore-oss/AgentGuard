from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.api.schemas import ApiResponse, ExecuteData, ExecuteRequest
from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.models import (
    Approval,
    IdempotencyRecord,
    Mandate,
    Product,
    Transaction,
)
from backend.app.services.audit_log import log_audit_event
from backend.app.services.payment_gateway import payment_gateway

router = APIRouter()


@router.post("/transaction/execute", response_model=ApiResponse[ExecuteData])
def execute_transaction(
    payload: ExecuteRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[ExecuteData] | JSONResponse:
    """Execute a server-authorized transaction against the payment gateway with atomic budget reservation."""
    # 1. Check exact idempotency key replay
    existing_record = (
        db.query(IdempotencyRecord)
        .filter_by(idempotency_key=payload.idempotency_key)
        .first()
    )
    if existing_record:
        if existing_record.transaction_id != payload.transaction_id:
            raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REUSED")
        return JSONResponse(status_code=200, content=existing_record.response_snapshot)

    # 2. Fetch Transaction with row lock
    txn = (
        db.query(Transaction)
        .filter_by(id=payload.transaction_id)
        .with_for_update()
        .first()
    )
    if not txn:
        raise HTTPException(status_code=404, detail="TRANSACTION_NOT_FOUND")

    # 3. Check Status Invariants & Replay Rules
    if txn.status == "SUCCESS":
        # New idempotency key trying to re-execute completed transaction
        raise HTTPException(status_code=409, detail="REPLAY_DETECTED")

    if txn.status == "ESCALATED":
        approval = (
            db.query(Approval)
            .filter_by(transaction_id=txn.id, status="approved")
            .first()
        )
        if not approval:
            raise HTTPException(status_code=202, detail="ESCALATION_REQUIRED")

    if txn.status in ("DENIED", "EXPIRED", "REVOKED"):
        raise HTTPException(status_code=403, detail=txn.reason_code)

    # 4. Server Re-Validation
    mandate = (
        db.query(Mandate)
        .filter_by(id=txn.mandate_id)
        .with_for_update()
        .first()
    )
    if not mandate or mandate.status != "active" or mandate.status == "revoked":
        txn.status = "REVOKED"
        txn.reason_code = "MANDATE_REVOKED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=403, detail="MANDATE_REVOKED")

    now = datetime.now(timezone.utc)
    mandate_exp = (
        mandate.expires_at.replace(tzinfo=timezone.utc)
        if mandate.expires_at.tzinfo is None
        else mandate.expires_at
    )
    if now >= mandate_exp:
        txn.status = "EXPIRED"
        txn.reason_code = "MANDATE_EXPIRED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=403, detail="MANDATE_EXPIRED")

    txn_exp = (
        txn.expires_at.replace(tzinfo=timezone.utc)
        if txn.expires_at.tzinfo is None
        else txn.expires_at
    )
    if now >= txn_exp:
        txn.status = "EXPIRED"
        txn.reason_code = "TRANSACTION_EXPIRED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=403, detail="TRANSACTION_EXPIRED")

    product = db.query(Product).filter_by(id=txn.product_id).first()
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")

    # Catalog price check (re-derived fresh from products table)
    if abs(product.price - txn.authoritative_price) > settings.PRICE_MISMATCH_TOLERANCE:
        txn.status = "DENIED"
        txn.reason_code = "PRICE_MISMATCH"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=403, detail="PRICE_MISMATCH")

    # 5. Authoritative Total & Budget Reservation Check
    authoritative_total = product.price * Decimal(str(txn.quantity))

    # If transaction was human-approved, human approval explicitly authorized exceeding budget/max_transaction limits
    is_human_approved = txn.reason_code == "APPROVED_BY_HUMAN"

    if not is_human_approved and (
        mandate.budget_remaining < authoritative_total
        or mandate.max_transaction_amount < authoritative_total
    ):
        txn.status = "DENIED"
        txn.reason_code = "BUDGET_EXCEEDED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=403, detail="BUDGET_EXCEEDED")

    # 6. Atomic Budget Reservation
    mandate.budget_remaining = mandate.budget_remaining - authoritative_total
    txn.status = "EXECUTING"
    try:
        log_audit_event(
            db=db,
            event_type="EXECUTING",
            actor="firewall",
            transaction_id=txn.id,
            payload={"authoritative_total": str(authoritative_total)},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    # 7. Payment Execution via Mock Payment Gateway
    success, payment_id = payment_gateway.process_payment(
        transaction_id=txn.id,
        amount=authoritative_total,
    )

    # 8. Post-Payment Outcome Handling
    if success:
        txn.status = "SUCCESS"
        txn.executed_at = now
        txn.idempotency_key = payload.idempotency_key

        resp_body = {
            "success": True,
            "data": {
                "transaction_id": txn.id,
                "status": "SUCCESS",
                "reason_code": txn.reason_code,
                "razorpay_payment_id": payment_id,
            },
            "error": None,
        }
        idemp_record = IdempotencyRecord(
            idempotency_key=payload.idempotency_key,
            transaction_id=txn.id,
            response_snapshot=resp_body,
            created_at=now,
        )
        try:
            db.add(idemp_record)
            log_audit_event(
                db=db,
                event_type="EXECUTED",
                actor="razorpay",
                transaction_id=txn.id,
                payload={
                    "razorpay_payment_id": payment_id,
                    "status": "SUCCESS",
                    "authoritative_total": str(authoritative_total),
                },
            )
            db.commit()
            db.refresh(txn)
        except Exception:
            db.rollback()
            raise

        return ApiResponse.ok(
            ExecuteData(
                transaction_id=txn.id,
                status="SUCCESS",
                reason_code=txn.reason_code,
                razorpay_payment_id=payment_id,
            )
        )
    else:
        # Payment declined: release reserved budget!
        mandate.budget_remaining = mandate.budget_remaining + authoritative_total
        txn.status = "FAILED"
        txn.reason_code = "PAYMENT_DECLINED"
        txn.idempotency_key = payload.idempotency_key

        resp_body = {
            "success": True,
            "data": {
                "transaction_id": txn.id,
                "status": "FAILED",
                "reason_code": "PAYMENT_DECLINED",
                "razorpay_payment_id": None,
            },
            "error": None,
        }
        idemp_record = IdempotencyRecord(
            idempotency_key=payload.idempotency_key,
            transaction_id=txn.id,
            response_snapshot=resp_body,
            created_at=now,
        )
        try:
            db.add(idemp_record)
            log_audit_event(
                db=db,
                event_type="FAILED",
                actor="razorpay",
                transaction_id=txn.id,
                payload={
                    "reason_code": "PAYMENT_DECLINED",
                    "status": "FAILED",
                },
            )
            db.commit()
            db.refresh(txn)
        except Exception:
            db.rollback()
            raise

        return ApiResponse.ok(
            ExecuteData(
                transaction_id=txn.id,
                status="FAILED",
                reason_code="PAYMENT_DECLINED",
                razorpay_payment_id=None,
            )
        )
