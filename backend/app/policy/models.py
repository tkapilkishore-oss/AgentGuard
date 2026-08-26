from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from backend.app.policy.reason_codes import PolicyDecision, ReasonCode


@dataclass(frozen=True)
class MandatePolicyInput:
    id: str
    user_id: str
    budget_total: Decimal
    budget_remaining: Decimal
    merchant_scope: str | None
    max_transaction_amount: Decimal
    status: str
    expires_at: datetime


@dataclass(frozen=True)
class ProductPolicyInput:
    id: str
    merchant_id: str
    name: str
    price: Decimal
    stock: int
    active: bool = True


@dataclass(frozen=True)
class AgentProposalInput:
    product_id: str
    claimed_price: Decimal
    quantity: int


@dataclass(frozen=True)
class PolicyEvaluationResult:
    decision: PolicyDecision
    reason_code: ReasonCode
    authoritative_total: Decimal
    authoritative_price: Decimal
    claimed_price: Decimal
