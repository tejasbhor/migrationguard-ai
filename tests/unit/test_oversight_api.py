"""
Unit tests for Human Oversight Dashboard API.

Tests approval workflow, metrics, and WebSocket functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from migrationguard_ai.api.routes.approvals import (
    get_pending_approvals,
    approve_or_reject_action,
    ApprovalRequest,
    PendingApproval
)
from migrationguard_ai.api.routes.metrics import (
    get_performance_metrics,
    get_deflection_metrics,
    get_confidence_calibration_metrics
)
from migrationguard_ai.api.routes.issues import (
    list_issues,
    get_issue_detail
)
from migrationguard_ai.db.models import Action as ActionModel, Issue as IssueModel


class TestApprovalWorkflowAPI:
    """Tests for approval workflow endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_pending_approvals_returns_list(self):
        """Test that get_pending_approvals returns a list of pending approvals."""
        # Mock database session
        mock_db = AsyncMock()
        
        # Create mock actions
        mock_action1 = MagicMock(spec=ActionModel)
        mock_action1.action_id = "action_1"
        mock_action1.issue_id = "issue_1"
        mock_action1.action_type = "support_guidance"
        mock_action1.risk_level = "high"
        mock_action1.parameters = {"merchant_id": "merchant_1"}
        mock_action1.reasoning = {}
        mock_action1.created_at = datetime.utcnow()
        mock_action1.status = "pending_approval"
        
        mock_action2 = MagicMock(spec=ActionModel)
        mock_action2.action_id = "action_2"
        mock_action2.issue_id = "issue_2"
        mock_action2.action_type = "engineering_escalation"
        mock_action2.risk_level = "critical"
        mock_action2.parameters = {"merchant_id": "merchant_2"}
        mock_action2.reasoning = {}
        mock_action2.created_at = datetime.utcnow()
        mock_action2.status = "pending_approval"
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_action1, mock_action2]
        mock_db.execute.return_value = mock_result
        
        # Execute (pass explicit values for Query parameters)
        approvals = await get_pending_approvals(db=mock_db, merchant_id=None, risk_level=None, limit=100)
        
        # Verify
        assert len(approvals) == 2
        assert approvals[0].approval_id == "action_1"
        assert approvals[0].risk_level == "high"
        assert approvals[1].approval_id == "action_2"
        assert approvals[1].risk_level == "critical"
    
    @pytest.mark.asyncio
    async def test_get_pending_approvals_filters_by_merchant(self):
        """Test that get_pending_approvals filters by merchant_id."""
        mock_db = AsyncMock()
        
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Execute with filter (pass explicit values for Query parameters)
        approvals = await get_pending_approvals(db=mock_db, merchant_id="merchant_1", risk_level=None, limit=100)
        
        # Verify query was called (filtering logic is in SQL)
        assert mock_db.execute.called
        assert len(approvals) == 0
    
    @pytest.mark.asyncio
    async def test_approve_action_executes_successfully(self):
        """Test that approving an action executes it successfully."""
        mock_db = AsyncMock()
        
        # Create mock action
        mock_action = MagicMock(spec=ActionModel)
        mock_action.action_id = "action_1"
        mock_action.action_type = "support_guidance"
        mock_action.risk_level = "medium"
        mock_action.status = "pending_approval"
        mock_action.parameters = {"merchant_id": "merchant_1"}
        mock_action.issue_id = "issue_1"
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_action
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Mock action executor
        with patch('migrationguard_ai.api.routes.approvals.get_action_executor') as mock_executor_getter:
            mock_executor = AsyncMock()
            mock_executor.execute = AsyncMock(return_value=MagicMock(
                success=True,
                executed_at=datetime.utcnow(),
                result={"ticket_id": "T-123"},
                error_message=None
            ))
            mock_executor_getter.return_value = mock_executor
            
            # Mock WebSocket manager
            with patch('migrationguard_ai.api.routes.approvals.manager.broadcast', new_callable=AsyncMock):
                # Create request
                request = ApprovalRequest(
                    decision="approve",
                    feedback=None,
                    operator_id="operator_1"
                )
                
                # Execute
                response = await approve_or_reject_action(
                    approval_id="action_1",
                    request=request,
                    db=mock_db
                )
        
        # Verify
        assert response.decision == "approve"
        assert response.executed is True
        assert response.result == {"ticket_id": "T-123"}
        assert mock_action.status == "completed"
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_reject_action_records_feedback(self):
        """Test that rejecting an action records operator feedback."""
        mock_db = AsyncMock()
        
        # Create mock action
        mock_action = MagicMock(spec=ActionModel)
        mock_action.action_id = "action_1"
        mock_action.action_type = "support_guidance"
        mock_action.risk_level = "medium"
        mock_action.status = "pending_approval"
        mock_action.parameters = {"merchant_id": "merchant_1"}
        mock_action.issue_id = "issue_1"
        mock_action.reasoning = {}
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_action
        mock_db.execute.return_value = mock_result
        mock_db.commit = AsyncMock()
        
        # Mock WebSocket manager
        with patch('migrationguard_ai.api.routes.approvals.manager.broadcast', new_callable=AsyncMock):
            # Create request with feedback
            request = ApprovalRequest(
                decision="reject",
                feedback="This action is not appropriate for this situation",
                operator_id="operator_1"
            )
            
            # Execute
            response = await approve_or_reject_action(
                approval_id="action_1",
                request=request,
                db=mock_db
            )
        
        # Verify
        assert response.decision == "reject"
        assert response.executed is False
        assert mock_action.status == "rejected"
        assert "operator_feedback" in mock_action.reasoning
        assert mock_action.reasoning["operator_feedback"]["operator_id"] == "operator_1"
        assert mock_action.reasoning["operator_feedback"]["feedback"] == "This action is not appropriate for this situation"
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_approve_nonexistent_action_raises_404(self):
        """Test that approving a nonexistent action raises 404."""
        mock_db = AsyncMock()
        
        # Mock database query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Create request
        request = ApprovalRequest(
            decision="approve",
            feedback=None,
            operator_id="operator_1"
        )
        
        # Execute and verify exception
        with pytest.raises(HTTPException) as exc_info:
            await approve_or_reject_action(
                approval_id="nonexistent",
                request=request,
                db=mock_db
            )
        
        assert exc_info.value.status_code == 404


class TestMetricsAPI:
    """Tests for metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics_returns_data(self):
        """Test that get_performance_metrics returns performance data."""
        mock_db = AsyncMock()
        
        # Mock signal count query
        signal_result = MagicMock()
        signal_result.scalar.return_value = 1000
        
        # Mock latency query
        latency_result = MagicMock()
        latency_result.scalar.return_value = 45.5
        
        # Mock action stats query
        action_stats = MagicMock()
        action_stats.total = 100
        action_stats.successful = 95
        action_stats_result = MagicMock()
        action_stats_result.one.return_value = action_stats
        
        # Mock active issues query
        active_issues_result = MagicMock()
        active_issues_result.scalar.return_value = 15
        
        # Set up execute to return different results based on query
        mock_db.execute.side_effect = [
            signal_result,
            latency_result,
            action_stats_result,
            active_issues_result
        ]
        
        # Execute
        metrics = await get_performance_metrics(db=mock_db, time_range=24)
        
        # Verify
        assert metrics.signal_ingestion_rate > 0
        assert metrics.avg_processing_latency == 45.5
        assert metrics.action_success_rate == 95.0
        assert metrics.active_issues == 15
        assert metrics.total_signals_24h == 1000
        assert metrics.total_actions_24h == 100
    
    @pytest.mark.asyncio
    async def test_get_deflection_metrics_calculates_rate(self):
        """Test that get_deflection_metrics calculates deflection rate correctly."""
        mock_db = AsyncMock()
        
        # Mock deflection stats query
        deflection_stats = MagicMock()
        deflection_stats.total = 100
        deflection_stats.deflected = 65
        deflection_stats.escalated = 35
        deflection_result = MagicMock()
        deflection_result.one.return_value = deflection_stats
        
        # Mock resolution time query
        resolution_time_result = MagicMock()
        resolution_time_result.scalar.return_value = 12.5
        
        mock_db.execute.side_effect = [deflection_result, resolution_time_result]
        
        # Execute
        metrics = await get_deflection_metrics(db=mock_db, time_range=24)
        
        # Verify
        assert metrics.deflection_rate == 65.0
        assert metrics.avg_resolution_time == 12.5
        assert metrics.total_deflected == 65
        assert metrics.total_escalated == 35
    
    @pytest.mark.asyncio
    async def test_get_confidence_calibration_metrics_returns_buckets(self):
        """Test that confidence calibration returns bucketed data."""
        mock_db = AsyncMock()
        
        # Mock actions with confidence scores
        mock_actions = []
        for i in range(10):
            action = MagicMock()
            action.reasoning = {"confidence": 0.9}
            action.status = "completed" if i < 9 else "failed"
            mock_actions.append(action)
        
        mock_result = MagicMock()
        mock_result.all.return_value = mock_actions
        mock_db.execute.return_value = mock_result
        
        # Execute
        metrics = await get_confidence_calibration_metrics(db=mock_db, time_range=24)
        
        # Verify
        assert metrics.total_predictions == 10
        assert "0.9-1.0" in metrics.confidence_buckets
        assert metrics.confidence_buckets["0.9-1.0"]["count"] == 10


class TestIssuesAPI:
    """Tests for issues query endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_issues_returns_list(self):
        """Test that list_issues returns a list of issues."""
        mock_db = AsyncMock()
        
        # Create mock issues
        mock_issue1 = MagicMock(spec=IssueModel)
        mock_issue1.issue_id = "issue_1"
        mock_issue1.status = "open"
        mock_issue1.merchant_id = "merchant_1"
        mock_issue1.root_cause_category = "migration_misstep"
        mock_issue1.confidence = 0.85
        mock_issue1.created_at = datetime.utcnow()
        mock_issue1.resolved_at = None
        mock_issue1.resolution_type = None
        
        # Mock database query result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_issue1]
        
        # Mock signal count query
        signal_count_result = MagicMock()
        signal_count_result.scalar.return_value = 5
        
        mock_db.execute.side_effect = [mock_result, signal_count_result]
        
        # Execute (pass explicit values for Query parameters)
        issues = await list_issues(db=mock_db, status=None, merchant_id=None, root_cause_category=None, resolution_type=None, limit=100, offset=0)
        
        # Verify
        assert len(issues) == 1
        assert issues[0].issue_id == "issue_1"
        assert issues[0].status == "open"
        assert issues[0].signal_count == 5
    
    @pytest.mark.asyncio
    async def test_get_issue_detail_returns_complete_info(self):
        """Test that get_issue_detail returns complete issue information."""
        mock_db = AsyncMock()
        
        # Create mock issue
        mock_issue = MagicMock(spec=IssueModel)
        mock_issue.issue_id = "issue_1"
        mock_issue.status = "resolved"
        mock_issue.merchant_id = "merchant_1"
        mock_issue.root_cause_category = "migration_misstep"
        mock_issue.root_cause_reasoning = "API endpoint mismatch"
        mock_issue.confidence = 0.92
        mock_issue.created_at = datetime.utcnow() - timedelta(hours=2)
        mock_issue.resolved_at = datetime.utcnow()
        mock_issue.resolution_type = "automated"
        mock_issue.reasoning_chain = [{"step": "analysis", "result": "found pattern"}]
        
        # Mock database queries
        issue_result = MagicMock()
        issue_result.scalar_one_or_none.return_value = mock_issue
        
        signals_result = MagicMock()
        signals_result.scalars.return_value.all.return_value = []
        
        actions_result = MagicMock()
        actions_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.side_effect = [issue_result, signals_result, actions_result]
        
        # Execute
        detail = await get_issue_detail(issue_id="issue_1", db=mock_db)
        
        # Verify
        assert detail.issue_id == "issue_1"
        assert detail.status == "resolved"
        assert detail.root_cause_category == "migration_misstep"
        assert detail.confidence == 0.92
        assert len(detail.reasoning_chain) == 1
    
    @pytest.mark.asyncio
    async def test_get_issue_detail_nonexistent_raises_404(self):
        """Test that getting a nonexistent issue raises 404."""
        mock_db = AsyncMock()
        
        # Mock database query returning None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute and verify exception
        with pytest.raises(HTTPException) as exc_info:
            await get_issue_detail(issue_id="nonexistent", db=mock_db)
        
        assert exc_info.value.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
