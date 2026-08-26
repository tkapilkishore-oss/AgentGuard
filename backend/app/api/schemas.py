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
    product_id: str
    claimed_price: Decimal = Field(gt=Decimal("0.00"))
    quantity: int = Field(ge=1, le=10, strict=True)

    model_config = ConfigDict(extra="ignore")


class ProposeRequest(BaseModel):
    user_id: str
    mandate_id: str
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
    transaction_id: str
    idempotency_key: str

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
