"""Signal model for time-series data storage in TimescaleDB."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migrationguard_ai.db.models.base import Base


class Signal(Base):
    """Signal model for storing time-series event data."""

    __tablename__ = "signals"

    # Primary key
    signal_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Timestamp (primary dimension for TimescaleDB hypertable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Signal source
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Merchant information
    merchant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    migration_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Severity
    severity: Mapped[str] = mapped_column(String(20), nullable=False)

    # Normalized fields
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    affected_resource: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Raw data and context (stored as JSON)
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default='{}')

    # Relationships
    issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("issues.issue_id", ondelete="CASCADE"),
        nullable=True,
    )
    pattern_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True)

    # Relationship to Issue
    issue = relationship("Issue", back_populates="signals")

    # Indexes for TimescaleDB
    __table_args__ = (
        Index("idx_timestamp", "timestamp", postgresql_using="btree"),
        Index("idx_merchant_timestamp", "merchant_id", "timestamp", postgresql_using="btree"),
        Index("idx_source_timestamp", "source", "timestamp", postgresql_using="btree"),
    )

    def __repr__(self) -> str:
        """String representation of Signal."""
        return (
            f"<Signal(signal_id={self.signal_id}, source={self.source}, "
            f"merchant_id={self.merchant_id}, timestamp={self.timestamp})>"
        )
