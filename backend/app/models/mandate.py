from datetime import datetime, timezone
from decimal import Decimal

# pyrefly: ignore [missing-import]
from sqlalchemy import DateTime, ForeignKey, Numeric, String

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Mandate(Base):
    __tablename__ = "mandates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    budget_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    budget_remaining: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    merchant_scope: Mapped[str | None] = mapped_column(String, nullable=True)
    category_scope: Mapped[str | None] = mapped_column(String, nullable=True)
    max_transaction_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
