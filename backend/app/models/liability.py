import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Date, DateTime, Numeric, ForeignKey, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LiabilitiesVault(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "liabilities_vault"
    __table_args__ = (
        CheckConstraint("interest_rate >= 0 AND interest_rate <= 100", name="ck_rate_range"),
        CheckConstraint("tenure_months > 0", name="ck_positive_tenure"),
        CheckConstraint("principal_amount > 0", name="ck_positive_principal"),
    )

    # 100% PRIVATE: user_id only, ZERO family_group_id
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    loan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)  # Annual % e.g. 8.5000
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    monthly_emi: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    payments: Mapped[List["LoanPayment"]] = relationship(
        "LoanPayment", back_populates="loan", cascade="all, delete-orphan"
    )
    prepayments: Mapped[List["LoanPrepayment"]] = relationship(
        "LoanPrepayment", back_populates="loan", cascade="all, delete-orphan"
    )


class LoanPayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loan_payments"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("liabilities_vault.id", ondelete="CASCADE"), index=True, nullable=False
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    principal_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    interest_paid: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Relationships
    loan: Mapped["LiabilitiesVault"] = relationship("LiabilitiesVault", back_populates="payments")


class LoanPrepayment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "loan_prepayments"
    __table_args__ = (
        CheckConstraint("lump_sum_amount > 0", name="ck_positive_prepayment"),
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("liabilities_vault.id", ondelete="CASCADE"), index=True, nullable=False
    )
    prepayment_date: Mapped[date] = mapped_column(Date, nullable=False)
    lump_sum_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    effect: Mapped[str] = mapped_column(String(20), default="REDUCE_TENURE", nullable=False)  # REDUCE_TENURE, REDUCE_EMI

    # Relationships
    loan: Mapped["LiabilitiesVault"] = relationship("LiabilitiesVault", back_populates="prepayments")
