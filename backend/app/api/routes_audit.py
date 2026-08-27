from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.schemas import (
    ApiResponse,
    AuditEventItem,
    TransactionAuditData,
    TransactionSummary,
)
from backend.app.db.session import get_db
from backend.app.models import AuditEvent, Product, Transaction
from backend.app.services.audit_log import verify_audit_chain

router = APIRouter()


@router.get("/transactions", response_model=ApiResponse[list[TransactionSummary]])
def list_transactions(
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[list[TransactionSummary]]:
    """List past transactions in descending order by created_at for audit selection."""
    txns = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(50).all()

    product_ids = {t.product_id for t in txns}
    products = (
        {p.id: p.name for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
        if product_ids
        else {}
    )

    summaries = [
        TransactionSummary(
            id=t.id,
            product_id=t.product_id,
            product_name=products.get(t.product_id),
            claimed_price=t.claimed_price,
            authoritative_price=t.authoritative_price,
            quantity=t.quantity,
            authoritative_total=t.authoritative_total,
            status=t.status,
            reason_code=t.reason_code,
            created_at=t.created_at,
            executed_at=t.executed_at,
        )
        for t in txns
    ]
    return ApiResponse.ok(summaries)


@router.get(
    "/transaction/{transaction_id}/audit",
    response_model=ApiResponse[TransactionAuditData],
)
def get_transaction_audit(
    transaction_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[TransactionAuditData]:
    """Retrieve the authoritative server-generated audit event trace for a transaction.

    Verifies transaction existence, returns events in deterministic chronological
    sequence order (seq_id ASC), and reports cryptographic SHA-256 chain integrity.
    """
    txn = db.query(Transaction).filter_by(id=transaction_id).first()
    if not txn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TRANSACTION_NOT_FOUND",
        )

    product = db.query(Product).filter_by(id=txn.product_id).first()
    product_name = product.name if product else None

    txn_summary = TransactionSummary(
        id=txn.id,
        product_id=txn.product_id,
        product_name=product_name,
        claimed_price=txn.claimed_price,
        authoritative_price=txn.authoritative_price,
        quantity=txn.quantity,
        authoritative_total=txn.authoritative_total,
        status=txn.status,
        reason_code=txn.reason_code,
        created_at=txn.created_at,
        executed_at=txn.executed_at,
    )

    event_rows = (
        db.query(AuditEvent)
        .filter_by(transaction_id=txn.id)
        .order_by(AuditEvent.seq_id.asc())
        .all()
    )

    events = [
        AuditEventItem(
            seq_id=e.seq_id,
            id=e.id,
            transaction_id=e.transaction_id,
            event_type=e.event_type,
            actor=e.actor,
            payload_hash=e.payload_hash,
            prev_hash=e.prev_hash,
            created_at=e.created_at,
        )
        for e in event_rows
    ]

    is_valid, err_msg = verify_audit_chain(db)

    return ApiResponse.ok(
        TransactionAuditData(
            transaction=txn_summary,
            events=events,
            chain_verified=is_valid,
            chain_verification_error=err_msg,
        )
    )
