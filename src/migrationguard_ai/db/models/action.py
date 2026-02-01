"""Action model for tracking executed actions."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migrationguard_ai.db.models.base import Base, TimestampMixin


class Action(Base, TimestampMixin):
    """Action model representing an executed or pending action."""

    __tablename__ = "actions"

    # Primary key
    action_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Foreign key to issue
    issue_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("issues.issue_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Action details
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Timing
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Parameters and results (stored as JSON)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Execution status
    success: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rollback support
    rollback_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Reasoning and feedback
    reasoning: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    issue = relationship("Issue", back_populates="actions")

    # Indexes
    __table_args__ = (
        Index("idx_issue", "issue_id"),
        Index("idx_status_created", "status", "created_at"),
        Index("idx_action_type_created", "action_type", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation of Action."""
        return (
            f"<Action(action_id={self.action_id}, action_type={self.action_type}, "
            f"status={self.status}, success={self.success})>"
        )
