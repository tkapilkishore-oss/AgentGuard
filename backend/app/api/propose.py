import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.api.schemas import ApiResponse, ProposeData, ProposeRequest
from backend.app.config import settings
from backend.app.db.session import get_db
from backend.app.models import Mandate, Product, Transaction, User
from backend.app.policy.engine import evaluate_policy
from backend.app.policy.models import (
    AgentProposalInput,
    MandatePolicyInput,
    ProductPolicyInput,
)
from backend.app.policy.reason_codes import PolicyDecision
from backend.app.services.audit_log import log_audit_event

router = APIRouter()


@router.post("/transaction/propose", response_model=ApiResponse[ProposeData])
def propose_transaction(
    payload: ProposeRequest,
    db: Session = Depends(get_db),  # noqa: B008
) -> ApiResponse[ProposeData]:
    """Process an untrusted agent transaction proposal and persist the server-authorized decision."""
    # 1. Fetch User
    user = db.query(User).filter_by(id=payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    # 2. Fetch Mandate
    mandate = db.query(Mandate).filter_by(id=payload.mandate_id).first()
    if not mandate or mandate.user_id != payload.user_id:
        raise HTTPException(status_code=404, detail="MANDATE_NOT_FOUND")

    # 3. Fetch Product
    product = db.query(Product).filter_by(id=payload.agent_claim.product_id).first()
    if not product or not product.active:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")

    # 4. Construct Pure Policy Engine Inputs
    now = datetime.now(timezone.utc)
    mandate_input = MandatePolicyInput(
        id=mandate.id,
        user_id=mandate.user_id,
        budget_total=mandate.budget_total,
        budget_remaining=mandate.budget_remaining,
        merchant_scope=mandate.merchant_scope,
        max_transaction_amount=mandate.max_transaction_amount,
        status=mandate.status,
        expires_at=mandate.expires_at,
    )
    product_input = ProductPolicyInput(
        id=product.id,
        merchant_id=product.merchant_id,
        name=product.name,
        price=product.price,
        stock=product.stock,
    )
    proposal_input = AgentProposalInput(
        product_id=payload.agent_claim.product_id,
        claimed_price=payload.agent_claim.claimed_price,
        quantity=payload.agent_claim.quantity,
    )

    # 5. Evaluate Pure Policy Engine
    eval_result = evaluate_policy(
        mandate=mandate_input,
        product=product_input,
        proposal=proposal_input,
        current_time=now,
        price_tolerance=settings.PRICE_MISMATCH_TOLERANCE,
    )

    # 6. Map Policy Decision to Transaction Status
    if eval_result.decision == PolicyDecision.ALLOW:
        txn_status = "ALLOWED"
    elif eval_result.decision == PolicyDecision.ESCALATE:
        txn_status = "ESCALATED"
    else:
        txn_status = "DENIED"

    # 7. Authoritative Server Calculations
    authoritative_price: Decimal = product.price
    authoritative_total: Decimal = authoritative_price * payload.agent_claim.quantity
    transaction_id = str(uuid.uuid4())
    nonce = secrets.token_hex(16)
    expires_at = now + timedelta(seconds=settings.TRANSACTION_EXPIRY_SECONDS)

    # 8. Persist Transaction Record & Audit Events
    txn = Transaction(
        id=transaction_id,
        mandate_id=mandate.id,
        user_id=user.id,
        merchant_id=product.merchant_id,
        product_id=product.id,
        claimed_price=payload.agent_claim.claimed_price,
        authoritative_price=authoritative_price,
        quantity=payload.agent_claim.quantity,
        authoritative_total=authoritative_total,
        status=txn_status,
        reason_code=eval_result.reason_code.value,
        nonce=nonce,
        created_at=now,
        expires_at=expires_at,
    )

    try:
        db.add(txn)
        db.flush()  # Flush transaction row to DB first so FK constraint is satisfied!

        # Log Audit Events for Proposal & Policy Decision
        log_audit_event(
            db=db,
            event_type="PROPOSED",
            actor="agent",
            transaction_id=txn.id,
            payload={
                "product_id": payload.agent_claim.product_id,
                "claimed_price": str(payload.agent_claim.claimed_price),
                "quantity": payload.agent_claim.quantity,
            },
        )
        log_audit_event(
            db=db,
            event_type="POLICY_DECISION",
            actor="firewall",
            transaction_id=txn.id,
            payload={
                "decision": eval_result.decision.value,
                "reason_code": eval_result.reason_code.value,
                "authoritative_total": str(authoritative_total),
            },
        )
        db.commit()
        db.refresh(txn)
    except Exception:
        db.rollback()
        raise

    # 9. Return Response Envelope
    return ApiResponse.ok(
        ProposeData(
            transaction_id=txn.id,
            decision=eval_result.decision.value,
            reason_code=eval_result.reason_code.value,
            authoritative_total=authoritative_total,
            expires_at=expires_at,
        )
    )
