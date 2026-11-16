import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, DateTime, Numeric, ForeignKey, JSON, Text, Index, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class PaymentTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "payment_transactions"
    __table_args__ = (
        Index("ix_payment_bill_id", "bill_id"),
        Index("ix_payment_idempotency", "idempotency_key"),
        Index(
            "uq_bill_active_payment",
            "bill_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'SUCCESS')"),
            sqlite_where=text("status IN ('PENDING', 'SUCCESS')"),
        ),
        Index(
            "uq_bill_idempotency",
            "bill_id",
            "idempotency_key",
            unique=True,
        ),
    )

    bill_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("upcoming_radars.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILED
    payment_reference: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    paid_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    paid_by_display_name_snapshot: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="SANDBOX_UPI", nullable=False)
    verified_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_intent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    events: Mapped[List["PaymentEvent"]] = relationship(
        "PaymentEvent", back_populates="transaction", cascade="all, delete-orphan"
    )


class PaymentEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "payment_events"

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payment_transactions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, index=True, nullable=True
    )
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    detail: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    transaction: Mapped["PaymentTransaction"] = relationship("PaymentTransaction", back_populates="events")
