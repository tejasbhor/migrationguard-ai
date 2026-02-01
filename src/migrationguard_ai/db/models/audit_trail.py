"""Audit trail model for immutable event logging."""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, event, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migrationguard_ai.db.models.base import Base


class AuditTrail(Base):
    """Immutable audit trail for all system events."""

    __tablename__ = "audit_trail"

    # Primary key
    audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )

    # Timestamp (no updated_at - immutable)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Foreign key to issue
    issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("issues.issue_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Event details
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # 'system' or operator_id

    # Event data (stored as JSON)
    inputs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    outputs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    reasoning: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Immutability chain
    hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hash
    previous_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    issue = relationship("Issue", back_populates="audit_entries")

    # Indexes
    __table_args__ = (
        Index("idx_issue_timestamp", "issue_id", "timestamp"),
        Index("idx_timestamp", "timestamp"),
        Index("idx_event_type_timestamp", "event_type", "timestamp"),
    )

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the audit entry."""
        data = {
            "audit_id": str(self.audit_id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "issue_id": str(self.issue_id) if self.issue_id else None,
            "event_type": self.event_type,
            "actor": self.actor,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "reasoning": self.reasoning,
            "previous_hash": self.previous_hash,
        }
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def __repr__(self) -> str:
        """String representation of AuditTrail."""
        return (
            f"<AuditTrail(audit_id={self.audit_id}, event_type={self.event_type}, "
            f"actor={self.actor}, timestamp={self.timestamp})>"
        )


# Event listeners to enforce immutability
@event.listens_for(AuditTrail, "before_insert")
def compute_hash_before_insert(mapper, connection, target):
    """Compute hash before inserting audit entry."""
    if not target.hash:
        target.hash = target.compute_hash()


@event.listens_for(AuditTrail, "before_update")
def prevent_update(mapper, connection, target):
    """Prevent updates to audit trail entries."""
    raise ValueError("Audit trail entries are immutable and cannot be updated")


@event.listens_for(AuditTrail, "before_delete")
def prevent_delete(mapper, connection, target):
    """Prevent deletion of audit trail entries."""
    raise ValueError("Audit trail entries are immutable and cannot be deleted")
