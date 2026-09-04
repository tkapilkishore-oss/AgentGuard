from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ApiError | None = None

    @classmethod
    def ok(cls, data: T) -> "ApiResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: str, message: str) -> "ApiResponse[T]":
        return cls(success=False, data=None, error=ApiError(code=code, message=message))


class AgentClaim(BaseModel):
    product_id: str = Field(..., min_length=1, max_length=128)
    claimed_price: Decimal = Field(gt=Decimal("0.00"), le=Decimal("10000000.00"))
    quantity: int = Field(ge=1, le=10, strict=True)

    model_config = ConfigDict(extra="ignore")


class ProposeRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    mandate_id: str = Field(..., min_length=1, max_length=128)
    agent_claim: AgentClaim

    model_config = ConfigDict(extra="ignore")


class ProposeData(BaseModel):
    transaction_id: str
    decision: str
    reason_code: str
    authoritative_total: Decimal
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=128)
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    model_config = ConfigDict(extra="ignore")


class ExecuteData(BaseModel):
    transaction_id: str
    status: str
    reason_code: str
    razorpay_payment_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ApprovalData(BaseModel):
    transaction_id: str
    status: str
    approver_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuditEventItem(BaseModel):
    seq_id: int
    id: str
    transaction_id: str | None = None
    event_type: str
    actor: str
    payload_hash: str
    prev_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionSummary(BaseModel):
    id: str
    product_id: str
    product_name: str | None = None
    claimed_price: Decimal
    authoritative_price: Decimal
    quantity: int
    authoritative_total: Decimal
    status: str
    reason_code: str
    created_at: datetime
    executed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionAuditData(BaseModel):
    transaction: TransactionSummary
    events: list[AuditEventItem]
    chain_verified: bool
    chain_verification_error: str | None = None

    model_config = ConfigDict(from_attributes=True)
