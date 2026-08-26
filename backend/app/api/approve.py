import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.schemas import ApiResponse, ApprovalData
from backend.app.db.session import get_db
from backend.app.models import Approval, Transaction
from backend.app.services.audit_log import log_audit_event

router = APIRouter()

DEFAULT_APPROVER_ID = "human_approver_001"


@router.post("/transaction/{transaction_id}/approve", response_model=ApiResponse[ApprovalData])
def approve_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[ApprovalData]:
    """Human approval endpoint for transactions in ESCALATED / BUDGET_EXCEEDED state."""
    # 1. Fetch transaction with row lock
    txn = db.query(Transaction).filter_by(id=transaction_id).with_for_update().first()
    if not txn:
        raise HTTPException(status_code=404, detail="TRANSACTION_NOT_FOUND")

    # 2. Check transaction expiry
    now = datetime.now(timezone.utc)
    expires_at = txn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now >= expires_at:
        txn.status = "DENIED"
        txn.reason_code = "TRANSACTION_EXPIRED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=400, detail="TRANSACTION_EXPIRED")

    # 3. Security invariant & state validation
    if txn.status != "ESCALATED" or txn.reason_code != "BUDGET_EXCEEDED":
        raise HTTPException(status_code=400, detail="INVALID_TRANSACTION_STATE")

    # 4. Perform atomic state transition & create Approval record
    approval = Approval(
        id=str(uuid.uuid4()),
        transaction_id=txn.id,
        status="approved",
        approver_id=DEFAULT_APPROVER_ID,
        created_at=now,
        resolved_at=now,
    )
    txn.status = "ALLOWED"
    txn.reason_code = "APPROVED_BY_HUMAN"

    try:
        db.add(approval)
        log_audit_event(
            db=db,
            event_type="APPROVED",
            actor="human",
            transaction_id=txn.id,
            payload={"approver_id": DEFAULT_APPROVER_ID, "status": "approved"},
        )
        db.commit()
        db.refresh(txn)
    except Exception:
        db.rollback()
        raise

    return ApiResponse.ok(
        ApprovalData(
            transaction_id=txn.id,
            status="approved",
            approver_id=DEFAULT_APPROVER_ID,
        )
    )


@router.post("/transaction/{transaction_id}/reject", response_model=ApiResponse[ApprovalData])
def reject_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[ApprovalData]:
    """Human rejection endpoint for transactions in ESCALATED / BUDGET_EXCEEDED state."""
    # 1. Fetch transaction with row lock
    txn = db.query(Transaction).filter_by(id=transaction_id).with_for_update().first()
    if not txn:
        raise HTTPException(status_code=404, detail="TRANSACTION_NOT_FOUND")

    # 2. Check transaction expiry
    now = datetime.now(timezone.utc)
    expires_at = txn.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if now >= expires_at:
        txn.status = "DENIED"
        txn.reason_code = "TRANSACTION_EXPIRED"
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        raise HTTPException(status_code=400, detail="TRANSACTION_EXPIRED")

    # 3. Security invariant & state validation
    if txn.status != "ESCALATED" or txn.reason_code != "BUDGET_EXCEEDED":
        raise HTTPException(status_code=400, detail="INVALID_TRANSACTION_STATE")

    # 4. Perform atomic state transition & create Approval record
    approval = Approval(
        id=str(uuid.uuid4()),
        transaction_id=txn.id,
        status="rejected",
        approver_id=DEFAULT_APPROVER_ID,
        created_at=now,
        resolved_at=now,
    )
    txn.status = "DENIED"
    txn.reason_code = "REJECTED_BY_HUMAN"

    try:
        db.add(approval)
        log_audit_event(
            db=db,
            event_type="REJECTED",
            actor="human",
            transaction_id=txn.id,
            payload={"approver_id": DEFAULT_APPROVER_ID, "status": "rejected"},
        )
        db.commit()
        db.refresh(txn)
    except Exception:
        db.rollback()
        raise

    return ApiResponse.ok(
        ApprovalData(
            transaction_id=txn.id,
            status="rejected",
            approver_id=DEFAULT_APPROVER_ID,
        )
    )
