import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Boolean, Date, DateTime, Numeric, ForeignKey,
    CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UpcomingRadar(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "upcoming_radars"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND family_group_id IS NULL) OR (user_id IS NULL AND family_group_id IS NOT NULL)",
            name="ck_bill_ownership_xor"
        ),
        CheckConstraint("amount >= 0", name="ck_bill_non_negative_amount"),
        Index("ix_radars_family_due", "family_group_id", "due_date"),
        Index("ix_radars_user_due", "user_id", "due_date"),
        Index("ix_radars_status_due", "bill_status", "due_date"),
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    family_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    consumer_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="utility", nullable=False)
    bill_status: Mapped[str] = mapped_column(String(20), default="UNPAID", nullable=False, index=True)  # UNPAID, PAID, PAID_UNVERIFIED, OVERDUE
    recurrence_interval: Mapped[str] = mapped_column(String(20), default="NONE", nullable=False)  # NONE, WEEKLY, MONTHLY, QUARTERLY, YEARLY
    anchor_day: Mapped[Optional[int]] = mapped_column(nullable=True)  # Original anchor day of month (1-31)
    next_bill_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    reminders: Mapped[List["BillReminder"]] = relationship(
        "BillReminder", back_populates="bill", cascade="all, delete-orphan"
    )


class BillReminder(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "bill_reminders"
    __table_args__ = (
        UniqueConstraint("bill_id", "offset_days", name="uq_bill_reminder_offset"),
    )

    bill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("upcoming_radars.id", ondelete="CASCADE"), index=True, nullable=False
    )
    trigger_date: Mapped[date] = mapped_column(Date, nullable=False)
    offset_days: Mapped[int] = mapped_column(nullable=False)  # 3, 1, 0
    notification_status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", nullable=False)  # SCHEDULED, SENT, SKIPPED

    # Relationships
    bill: Mapped["UpcomingRadar"] = relationship("UpcomingRadar", back_populates="reminders")
