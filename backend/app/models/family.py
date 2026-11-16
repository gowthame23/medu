import enum
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class FamilyRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"


class InvitationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class FamilyGroup(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "family_groups"

    group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata", nullable=False)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    members: Mapped[List["FamilyMember"]] = relationship(
        "FamilyMember", back_populates="family_group", cascade="all, delete-orphan"
    )
    invitations: Mapped[List["FamilyInvitation"]] = relationship(
        "FamilyInvitation", back_populates="family_group", cascade="all, delete-orphan"
    )


class FamilyMember(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("user_id", "family_group_id", name="uq_user_family_group"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    family_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), default=FamilyRole.MEMBER.value, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    family_group: Mapped["FamilyGroup"] = relationship("FamilyGroup", back_populates="members")
    user: Mapped["User"] = relationship("User")


class FamilyInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "family_invitations"

    family_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("family_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    invited_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default=InvitationStatus.PENDING.value, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    family_group: Mapped["FamilyGroup"] = relationship("FamilyGroup", back_populates="invitations")
