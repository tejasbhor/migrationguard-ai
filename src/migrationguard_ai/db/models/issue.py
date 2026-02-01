"""Issue model for tracking merchant issues."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, Numeric, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migrationguard_ai.db.models.base import Base, TimestampMixin


class Issue(Base, TimestampMixin):
    """Issue model representing a merchant problem being tracked."""

    __tablename__ = "issues"

    # Primary key
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Merchant information
    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)

    # Timestamps
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Analysis results
    root_cause_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)

    # Decision
    selected_action_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Metadata
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pattern_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Resolution tracking
    resolution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    root_cause_reasoning: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    reasoning_chain: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Relationships
    signals = relationship("Signal", back_populates="issue", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="issue", cascade="all, delete-orphan")
    audit_entries = relationship("AuditTrail", back_populates="issue", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_merchant_status", "merchant_id", "status"),
        Index("idx_created_at", "created_at"),
        Index(
            "idx_approval_status",
            "approval_status",
            postgresql_where=(requires_approval == True),
        ),
    )

    def __repr__(self) -> str:
        """String representation of Issue."""
        return (
            f"<Issue(issue_id={self.issue_id}, merchant_id={self.merchant_id}, "
            f"status={self.status}, stage={self.stage})>"
        )
