"""Pydantic schemas for domain objects.

These schemas define the structure and validation rules for data flowing
through the system. They are used for API requests/responses, internal
data transfer, and validation.
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Signal(BaseModel):
    """Signal schema for incoming events and issues."""

    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the signal occurred")
    source: Literal["support_ticket", "api_failure", "checkout_error", "webhook_failure"] = Field(
        ..., description="Source of the signal"
    )
    merchant_id: str = Field(..., description="Merchant identifier", min_length=1)
    migration_stage: Optional[str] = Field(None, description="Current migration stage")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Signal severity")

    # Source-specific data
    raw_data: dict = Field(..., description="Raw data from the source")

    # Normalized fields
    error_message: Optional[str] = Field(None, description="Normalized error message")
    error_code: Optional[str] = Field(None, description="Normalized error code")
    affected_resource: Optional[str] = Field(None, description="Resource affected by the issue")
    context: dict = Field(default_factory=dict, description="Additional context")

    model_config = {"json_schema_extra": {
        "example": {
            "signal_id": "550e8400-e29b-41d4-a716-446655440000",
            "timestamp": "2026-02-01T10:30:00Z",
            "source": "support_ticket",
            "merchant_id": "merchant_123",
            "migration_stage": "phase_2",
            "severity": "high",
            "raw_data": {"ticket_id": "T-12345", "subject": "Checkout not working"},
            "error_message": "Checkout fails with 404 error",
            "error_code": "CHECKOUT_404",
            "affected_resource": "/checkout",
            "context": {"browser": "Chrome", "version": "120.0"}
        }
    }}


class Pattern(BaseModel):
    """Pattern schema for detected issue patterns."""

    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    pattern_type: Literal[
        "api_failure",
        "checkout_issue",
        "webhook_problem",
        "config_error",
        "migration_stage_issue"
    ] = Field(..., description="Type of pattern")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    signal_ids: list[str] = Field(..., description="Signals that match this pattern")
    merchant_ids: list[str] = Field(..., description="Affected merchants")
    first_seen: datetime = Field(..., description="When pattern was first detected")
    last_seen: datetime = Field(..., description="When pattern was last seen")
    frequency: int = Field(..., ge=1, description="Number of occurrences")
    characteristics: dict = Field(..., description="Pattern characteristics")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "pattern_id": "pat_001",
            "pattern_type": "webhook_problem",
            "confidence": 0.92,
            "signal_ids": ["sig_001", "sig_002", "sig_003"],
            "merchant_ids": ["merchant_123", "merchant_456"],
            "first_seen": "2026-02-01T10:00:00Z",
            "last_seen": "2026-02-01T10:30:00Z",
            "frequency": 3,
            "characteristics": {
                "error_pattern": "webhook_404",
                "common_domain": "old-domain.com"
            }
        }
    }}


class RootCauseAnalysis(BaseModel):
    """Root cause analysis result schema."""

    category: Literal[
        "migration_misstep",
        "platform_regression",
        "documentation_gap",
        "config_error"
    ] = Field(..., description="Root cause category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence (0-1)")
    reasoning: str = Field(..., description="Detailed reasoning for the analysis", min_length=1)
    evidence: list[str] = Field(..., description="Supporting evidence")
    alternatives_considered: list[dict] = Field(
        default_factory=list,
        description="Alternative hypotheses that were considered"
    )
    recommended_actions: list[str] = Field(..., description="Recommended actions")

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Ensure category is one of the valid options."""
        valid_categories = ["migration_misstep", "platform_regression", "documentation_gap", "config_error"]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "category": "migration_misstep",
            "confidence": 0.87,
            "reasoning": "Webhook URL still points to old domain based on 404 errors",
            "evidence": [
                "Webhook logs show 404 errors",
                "Migration completed 2 days ago",
                "Similar issue resolved for 12 other merchants"
            ],
            "alternatives_considered": [
                {"hypothesis": "Platform bug", "confidence": 0.15, "rejected_reason": "No other merchants affected"},
                {"hypothesis": "DNS issue", "confidence": 0.10, "rejected_reason": "DNS resolves correctly"}
            ],
            "recommended_actions": [
                "Update webhook URL to new domain",
                "Verify webhook configuration",
                "Test webhook delivery"
            ]
        }
    }}


class Decision(BaseModel):
    """Decision schema for action planning."""

    action_type: Literal[
        "support_guidance",
        "proactive_communication",
        "engineering_escalation",
        "temporary_mitigation",
        "documentation_update"
    ] = Field(..., description="Type of action to take")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk level")
    requires_approval: bool = Field(..., description="Whether human approval is required")
    parameters: dict = Field(..., description="Action parameters")
    estimated_outcome: str = Field(..., description="Expected outcome", min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence")
    reasoning: str = Field(..., description="Decision reasoning", min_length=1)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        """Ensure action_type is valid."""
        valid_types = [
            "support_guidance",
            "proactive_communication",
            "engineering_escalation",
            "temporary_mitigation",
            "documentation_update"
        ]
        if v not in valid_types:
            raise ValueError(f"Action type must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Ensure risk_level is valid."""
        valid_levels = ["low", "medium", "high", "critical"]
        if v not in valid_levels:
            raise ValueError(f"Risk level must be one of: {', '.join(valid_levels)}")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "action_type": "support_guidance",
            "risk_level": "low",
            "requires_approval": False,
            "parameters": {
                "merchant_id": "merchant_123",
                "message": "Please update your webhook URL to the new domain",
                "documentation_link": "https://docs.example.com/webhooks"
            },
            "estimated_outcome": "Merchant updates webhook configuration and checkout resumes",
            "confidence": 0.87,
            "reasoning": "High confidence based on similar resolved cases"
        }
    }}


class Action(BaseModel):
    """Action schema for execution tracking."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier")
    action_type: Literal[
        "support_guidance",
        "proactive_communication",
        "engineering_escalation",
        "temporary_mitigation",
        "documentation_update"
    ] = Field(..., description="Type of action")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Risk level")
    status: Literal["pending", "pending_approval", "in_progress", "completed", "failed", "rolled_back", "rejected"] = Field(
        ..., description="Action status"
    )
    parameters: dict = Field(..., description="Action parameters")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When action was created")
    executed_at: Optional[datetime] = Field(None, description="When action was executed")
    completed_at: Optional[datetime] = Field(None, description="When action was completed")

    model_config = {"json_schema_extra": {
        "example": {
            "action_id": "act_001",
            "action_type": "support_guidance",
            "risk_level": "low",
            "status": "completed",
            "parameters": {
                "merchant_id": "merchant_123",
                "message": "Webhook configuration updated"
            },
            "created_at": "2026-02-01T10:30:00Z",
            "executed_at": "2026-02-01T10:30:05Z",
            "completed_at": "2026-02-01T10:30:10Z"
        }
    }}


class ActionResult(BaseModel):
    """Action execution result schema."""

    action_id: str = Field(..., description="Action identifier")
    success: bool = Field(..., description="Whether action succeeded")
    result: Optional[dict] = Field(None, description="Result data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    executed_at: datetime = Field(..., description="When action was executed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds", ge=0)

    model_config = {"json_schema_extra": {
        "example": {
            "action_id": "act_001",
            "success": True,
            "result": {
                "ticket_id": "T-12345",
                "response_sent": True,
                "merchant_notified": True
            },
            "error_message": None,
            "executed_at": "2026-02-01T10:30:10Z",
            "duration_ms": 250
        }
    }}


# Export all schemas
__all__ = [
    "Signal",
    "Pattern",
    "RootCauseAnalysis",
    "Decision",
    "Action",
    "ActionResult",
]
