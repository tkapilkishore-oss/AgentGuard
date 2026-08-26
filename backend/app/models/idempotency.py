from datetime import datetime, timezone
from typing import Any

# pyrefly: ignore [missing-import]
from sqlalchemy import DateTime, ForeignKey, String

# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import JSONB

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    idempotency_key: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        String, ForeignKey("transactions.id"), nullable=False, index=True
    )
    response_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
