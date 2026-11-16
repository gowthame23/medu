import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Boolean, Date, Numeric, Text, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ExpenseCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "expense_categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_category_user_name"),
        Index(
            "uq_system_category_name",
            "name",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
            sqlite_where=text("user_id IS NULL"),
        ),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DailyLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "log_date", name="uq_user_log_date"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    entries: Mapped[List["DailyLogEntry"]] = relationship(
        "DailyLogEntry", back_populates="daily_log", cascade="all, delete-orphan"
    )


class DailyLogEntry(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "daily_log_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_entry_positive_amount"),
    )

    daily_log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("daily_logs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("expense_categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Relationships
    daily_log: Mapped["DailyLog"] = relationship("DailyLog", back_populates="entries")
    category: Mapped["ExpenseCategory"] = relationship("ExpenseCategory")
