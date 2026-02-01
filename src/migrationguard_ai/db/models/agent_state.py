"""Agent state model for LangGraph persistence."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from migrationguard_ai.db.models.base import Base, TimestampMixin


class AgentState(Base, TimestampMixin):
    """Agent state for LangGraph checkpointing."""

    __tablename__ = "agent_state"

    # Primary key
    state_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Issue tracking
    issue_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True, unique=True)

    # Current stage
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # State data (stored as JSON)
    state_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Checkpoint metadata
    checkpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parent_checkpoint_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Execution metadata
    error_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_issue_id", "issue_id"),
        Index("idx_stage", "stage"),
        Index("idx_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        """String representation of AgentState."""
        return (
            f"<AgentState(state_id={self.state_id}, issue_id={self.issue_id}, "
            f"stage={self.stage})>"
        )
