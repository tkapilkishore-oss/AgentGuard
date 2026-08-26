# pyrefly: ignore [missing-import]
from sqlalchemy import String

# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
