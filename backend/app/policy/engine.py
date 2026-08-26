from datetime import datetime, timezone
from decimal import Decimal

from backend.app.policy.models import (
    AgentProposalInput,
    MandatePolicyInput,
    PolicyEvaluationResult,
    ProductPolicyInput,
)
from backend.app.policy.reason_codes import PolicyDecision, ReasonCode


def evaluate_policy(
    mandate: MandatePolicyInput,
    product: ProductPolicyInput,
    proposal: AgentProposalInput,
    current_time: datetime | None = None,
    price_tolerance: Decimal = Decimal("0.01"),
) -> PolicyEvaluationResult:
    """Pure Python policy engine for Agentic Commerce Firewall.

    Authoritative Validation Order:
    1. Check mandate status (must be active)
    2. Check mandate expiry
    3. Authoritative product/merchant data supplied directly
    4. Validate quantity (int, not bool, >= 1, <= stock, <= 10)
    5. Compare claimed price vs authoritative price
    6. Verify merchant scope using server-derived product.merchant_id
    7. Compute authoritative_total = product.price * quantity
    8. Compare authoritative_total against budget_remaining & max_transaction_amount
    9. Return decision (ALLOW, ESCALATE, DENY) and canonical reason code
    """
    # Safe total calculation for result payload
    safe_quantity = (
        proposal.quantity
        if (isinstance(proposal.quantity, int) and not isinstance(proposal.quantity, bool))
        else 0
    )
    authoritative_total = product.price * Decimal(safe_quantity)

    # 1. Mandate Status Check
    if mandate.status == "revoked":
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.MANDATE_REVOKED,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )
    if mandate.status != "active":
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.MANDATE_EXPIRED,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 2. Mandate Expiry Check
    eval_time = datetime.now(timezone.utc) if current_time is None else current_time
    mandate_expires_at = mandate.expires_at

    # Normalize timezone awareness to prevent TypeError on naive vs aware comparison
    if eval_time.tzinfo is not None and mandate_expires_at.tzinfo is None:
        mandate_expires_at = mandate_expires_at.replace(tzinfo=timezone.utc)
    elif eval_time.tzinfo is None and mandate_expires_at.tzinfo is not None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    if eval_time >= mandate_expires_at:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.MANDATE_EXPIRED,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 4. Quantity Validation (bool excluded, 1 <= qty <= stock, qty <= 10)
    if (
        isinstance(proposal.quantity, bool)
        or not isinstance(proposal.quantity, int)
        or proposal.quantity < 1
        or proposal.quantity > product.stock
        or proposal.quantity > 10
    ):
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.QUANTITY_INVALID,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 5. Price Comparison
    price_diff = abs(proposal.claimed_price - product.price)
    if price_diff > price_tolerance:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.PRICE_MISMATCH,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 6. Merchant Scope Validation
    if mandate.merchant_scope is not None and product.merchant_id != mandate.merchant_scope:
        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            reason_code=ReasonCode.MERCHANT_MISMATCH,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 8. Budget & Limit Semantics
    if (
        authoritative_total > mandate.max_transaction_amount
        or authoritative_total > mandate.budget_remaining
    ):
        return PolicyEvaluationResult(
            decision=PolicyDecision.ESCALATE,
            reason_code=ReasonCode.BUDGET_EXCEEDED,
            authoritative_total=authoritative_total,
            authoritative_price=product.price,
            claimed_price=proposal.claimed_price,
        )

    # 9. All Checks Pass -> ALLOW
    return PolicyEvaluationResult(
        decision=PolicyDecision.ALLOW,
        reason_code=ReasonCode.ALLOW,
        authoritative_total=authoritative_total,
        authoritative_price=product.price,
        claimed_price=proposal.claimed_price,
    )
