"""Unit tests for database models."""

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from migrationguard_ai.db.models import Action, AgentState, AuditTrail, Issue, Signal


class TestIssueModel:
    """Tests for the Issue model."""

    @pytest.mark.asyncio
    async def test_create_issue(self, db_session):
        """Test creating a basic issue."""
        issue = Issue(
            merchant_id="merchant_123",
            status="active",
            stage="observe",
        )
        db_session.add(issue)
        await db_session.commit()

        assert issue.issue_id is not None
        assert issue.merchant_id == "merchant_123"
        assert issue.status == "active"
        assert issue.stage == "observe"
        assert issue.created_at is not None
        assert issue.updated_at is not None

    @pytest.mark.asyncio
    async def test_issue_with_analysis(self, db_session):
        """Test issue with root cause analysis."""
        issue = Issue(
            merchant_id="merchant_456",
            status="analyzing",
            stage="reason",
            root_cause_category="migration_misstep",
            confidence=0.85,
        )
        db_session.add(issue)
        await db_session.commit()

        assert issue.root_cause_category == "migration_misstep"
        assert float(issue.confidence) == 0.85

    @pytest.mark.asyncio
    async def test_issue_with_decision(self, db_session):
        """Test issue with decision data."""
        issue = Issue(
            merchant_id="merchant_789",
            status="pending_approval",
            stage="decide",
            selected_action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
        )
        db_session.add(issue)
        await db_session.commit()

        assert issue.selected_action_type == "support_guidance"
        assert issue.risk_level == "low"
        assert issue.requires_approval is False

    @pytest.mark.asyncio
    async def test_issue_relationships(self, db_session):
        """Test issue relationships with signals and actions."""
        issue = Issue(
            merchant_id="merchant_rel",
            status="active",
            stage="observe",
        )
        db_session.add(issue)
        await db_session.flush()

        # Add signals
        signal1 = Signal(
            timestamp=datetime.utcnow(),
            source="support_ticket",
            merchant_id="merchant_rel",
            severity="high",
            raw_data={"ticket_id": "T001"},
            issue_id=issue.issue_id,
        )
        signal2 = Signal(
            timestamp=datetime.utcnow(),
            source="api_failure",
            merchant_id="merchant_rel",
            severity="medium",
            raw_data={"error": "timeout"},
            issue_id=issue.issue_id,
        )
        db_session.add_all([signal1, signal2])
        await db_session.commit()

        # Verify relationships
        assert len(issue.signals) == 2
        assert signal1 in issue.signals
        assert signal2 in issue.signals


class TestSignalModel:
    """Tests for the Signal model."""

    @pytest.mark.asyncio
    async def test_create_signal(self, db_session):
        """Test creating a basic signal."""
        signal = Signal(
            timestamp=datetime.utcnow(),
            source="support_ticket",
            merchant_id="merchant_sig_001",
            severity="high",
            raw_data={"ticket_id": "T123", "subject": "Checkout broken"},
            error_message="Checkout not working after migration",
        )
        db_session.add(signal)
        await db_session.commit()

        assert signal.signal_id is not None
        assert signal.source == "support_ticket"
        assert signal.merchant_id == "merchant_sig_001"
        assert signal.severity == "high"
        assert signal.raw_data["ticket_id"] == "T123"

    @pytest.mark.asyncio
    async def test_signal_with_all_fields(self, db_session):
        """Test signal with all optional fields."""
        signal = Signal(
            timestamp=datetime.utcnow(),
            source="api_failure",
            merchant_id="merchant_sig_002",
            migration_stage="phase_2",
            severity="critical",
            error_message="API timeout",
            error_code="ERR_TIMEOUT",
            affected_resource="/api/v2/orders",
            raw_data={"status_code": 504, "latency_ms": 30000},
            context={"retry_count": 3, "last_success": "2026-01-31T10:00:00Z"},
        )
        db_session.add(signal)
        await db_session.commit()

        assert signal.migration_stage == "phase_2"
        assert signal.error_code == "ERR_TIMEOUT"
        assert signal.affected_resource == "/api/v2/orders"
        assert signal.context["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_signal_time_series(self, db_session):
        """Test creating multiple signals for time-series analysis."""
        base_time = datetime.utcnow()
        signals = []

        for i in range(5):
            signal = Signal(
                timestamp=base_time + timedelta(minutes=i),
                source="checkout_error",
                merchant_id="merchant_ts",
                severity="high",
                raw_data={"order_id": f"ORD_{i:03d}"},
            )
            signals.append(signal)
            db_session.add(signal)

        await db_session.commit()

        # Verify all signals were created
        result = await db_session.execute(
            select(Signal).where(Signal.merchant_id == "merchant_ts").order_by(Signal.timestamp)
        )
        retrieved_signals = result.scalars().all()

        assert len(retrieved_signals) == 5
        for i, signal in enumerate(retrieved_signals):
            assert signal.raw_data["order_id"] == f"ORD_{i:03d}"


class TestActionModel:
    """Tests for the Action model."""

    @pytest.mark.asyncio
    async def test_create_action(self, db_session):
        """Test creating a basic action."""
        # Create issue first
        issue = Issue(
            merchant_id="merchant_act_001",
            status="active",
            stage="act",
        )
        db_session.add(issue)
        await db_session.flush()

        action = Action(
            issue_id=issue.issue_id,
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={"message": "Please check your webhook configuration"},
        )
        db_session.add(action)
        await db_session.commit()

        assert action.action_id is not None
        assert action.issue_id == issue.issue_id
        assert action.action_type == "support_guidance"
        assert action.status == "pending"

    @pytest.mark.asyncio
    async def test_action_execution(self, db_session):
        """Test action with execution details."""
        issue = Issue(
            merchant_id="merchant_act_002",
            status="active",
            stage="act",
        )
        db_session.add(issue)
        await db_session.flush()

        action = Action(
            issue_id=issue.issue_id,
            action_type="temporary_mitigation",
            risk_level="medium",
            status="completed",
            parameters={"config_key": "rate_limit", "new_value": 1000},
            result={"previous_value": 500, "applied": True},
            success=True,
            executed_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        db_session.add(action)
        await db_session.commit()

        assert action.success is True
        assert action.result["applied"] is True
        assert action.executed_at is not None

    @pytest.mark.asyncio
    async def test_action_with_rollback(self, db_session):
        """Test action with rollback data."""
        issue = Issue(
            merchant_id="merchant_act_003",
            status="active",
            stage="act",
        )
        db_session.add(issue)
        await db_session.flush()

        action = Action(
            issue_id=issue.issue_id,
            action_type="temporary_mitigation",
            risk_level="high",
            status="completed",
            parameters={"change": "increase_timeout"},
            rollback_data={"original_timeout": 30, "rollback_command": "reset_timeout"},
            success=True,
        )
        db_session.add(action)
        await db_session.commit()

        assert action.rollback_data is not None
        assert action.rollback_data["original_timeout"] == 30
        assert action.rolled_back is False


class TestAuditTrailModel:
    """Tests for the AuditTrail model."""

    @pytest.mark.asyncio
    async def test_create_audit_entry(self, db_session):
        """Test creating an audit trail entry."""
        issue = Issue(
            merchant_id="merchant_audit_001",
            status="active",
            stage="observe",
        )
        db_session.add(issue)
        await db_session.flush()

        audit = AuditTrail(
            issue_id=issue.issue_id,
            event_type="signal_received",
            actor="system",
            inputs={"signal_id": "sig_001", "source": "support_ticket"},
            outputs={"processed": True},
        )
        db_session.add(audit)
        await db_session.commit()

        assert audit.audit_id is not None
        assert audit.event_type == "signal_received"
        assert audit.actor == "system"
        assert audit.hash is not None

    @pytest.mark.asyncio
    async def test_audit_hash_computation(self, db_session):
        """Test that audit hash is computed correctly."""
        issue = Issue(
            merchant_id="merchant_audit_002",
            status="active",
            stage="reason",
        )
        db_session.add(issue)
        await db_session.flush()

        audit = AuditTrail(
            issue_id=issue.issue_id,
            event_type="root_cause_analyzed",
            actor="system",
            inputs={"signals": ["sig_001", "sig_002"]},
            outputs={"category": "migration_misstep", "confidence": 0.92},
            reasoning={"evidence": ["webhook_404", "old_domain"]},
        )
        db_session.add(audit)
        await db_session.flush()

        # Hash should be automatically computed
        assert audit.hash is not None
        assert len(audit.hash) == 64

        # Verify hash matches computed hash
        expected_hash = audit.compute_hash()
        assert audit.hash == expected_hash


class TestAgentStateModel:
    """Tests for the AgentState model."""

    @pytest.mark.asyncio
    async def test_create_agent_state(self, db_session):
        """Test creating agent state."""
        issue_id = uuid.uuid4()
        state = AgentState(
            issue_id=issue_id,
            stage="observe",
            state_data={
                "signals": [],
                "patterns": [],
                "reasoning_chain": ["Started observation"],
            },
        )
        db_session.add(state)
        await db_session.commit()

        assert state.state_id is not None
        assert state.issue_id == issue_id
        assert state.stage == "observe"
        assert state.error_count == 0

    @pytest.mark.asyncio
    async def test_agent_state_with_checkpoint(self, db_session):
        """Test agent state with checkpoint data."""
        issue_id = uuid.uuid4()
        state = AgentState(
            issue_id=issue_id,
            stage="reason",
            state_data={"root_cause": "migration_misstep", "confidence": 0.85},
            checkpoint_id="checkpoint_001",
            parent_checkpoint_id="checkpoint_000",
        )
        db_session.add(state)
        await db_session.commit()

        assert state.checkpoint_id == "checkpoint_001"
        assert state.parent_checkpoint_id == "checkpoint_000"

    @pytest.mark.asyncio
    async def test_agent_state_unique_issue(self, db_session):
        """Test that issue_id is unique in agent_state."""
        issue_id = uuid.uuid4()
        
        state1 = AgentState(
            issue_id=issue_id,
            stage="observe",
            state_data={"step": 1},
        )
        db_session.add(state1)
        await db_session.commit()

        # Attempting to create another state with same issue_id should fail
        state2 = AgentState(
            issue_id=issue_id,
            stage="reason",
            state_data={"step": 2},
        )
        db_session.add(state2)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestModelRelationships:
    """Tests for model relationships and cascades."""

    @pytest.mark.asyncio
    async def test_cascade_delete_issue(self, db_session):
        """Test that deleting an issue cascades to related records."""
        # Create issue with related records
        issue = Issue(
            merchant_id="merchant_cascade",
            status="active",
            stage="observe",
        )
        db_session.add(issue)
        await db_session.flush()

        # Add signal
        signal = Signal(
            timestamp=datetime.utcnow(),
            source="support_ticket",
            merchant_id="merchant_cascade",
            severity="high",
            raw_data={"test": "data"},
            issue_id=issue.issue_id,
        )
        db_session.add(signal)

        # Add action
        action = Action(
            issue_id=issue.issue_id,
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={"message": "test"},
        )
        db_session.add(action)

        # Add audit entry
        audit = AuditTrail(
            issue_id=issue.issue_id,
            event_type="test_event",
            actor="system",
        )
        db_session.add(audit)

        await db_session.commit()

        issue_id = issue.issue_id
        signal_id = signal.signal_id
        action_id = action.action_id
        audit_id = audit.audit_id

        # Delete the issue
        await db_session.delete(issue)
        await db_session.commit()

        # Verify related records are deleted (cascade)
        result = await db_session.execute(select(Signal).where(Signal.signal_id == signal_id))
        assert result.scalar_one_or_none() is None

        result = await db_session.execute(select(Action).where(Action.action_id == action_id))
        assert result.scalar_one_or_none() is None

        # Note: Audit trail should NOT be deleted due to immutability rules
        # This test would need to be adjusted based on actual cascade behavior
