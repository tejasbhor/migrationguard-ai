"""
Unit tests for Action Executor.

Tests each action type execution, retry logic, audit trail recording, and rate limiting.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from migrationguard_ai.core.schemas import Action, ActionResult
from migrationguard_ai.services.action_executor import ActionExecutor


class TestActionExecutorInitialization:
    """Test action executor initialization."""
    
    def test_executor_initialization(self):
        """Test that executor initializes with all required services."""
        executor = ActionExecutor()
        
        assert executor.support_integrations is not None
        assert executor.notification_service is not None
        assert executor.config_manager is not None
        assert executor.audit_trail is not None
        assert executor.rate_limiter is not None


class TestSupportGuidanceExecution:
    """Test support guidance action execution."""
    
    @pytest.mark.asyncio
    async def test_support_guidance_with_existing_ticket(self):
        """Test support guidance updates existing ticket."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Please update your webhook URL",
                "support_system": "zendesk",
                "ticket_id": "T-12345"
            }
        )
        
        # Mock support system client
        mock_client = AsyncMock()
        mock_client.update_ticket = AsyncMock(return_value={"id": "T-12345"})
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            result = await executor._execute_support_guidance(action)
            
            assert result.success is True
            assert result.result["ticket_id"] == "T-12345"
            assert result.result["message_sent"] is True
            mock_client.update_ticket.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_support_guidance_creates_new_ticket(self):
        """Test support guidance creates new ticket when no ticket_id provided."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Please update your webhook URL",
                "support_system": "zendesk"
            }
        )
        
        # Mock support system client
        mock_client = AsyncMock()
        mock_client.create_ticket = AsyncMock(return_value={"id": "T-NEW-123"})
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            result = await executor._execute_support_guidance(action)
            
            assert result.success is True
            assert result.result["ticket_id"] == "T-NEW-123"
            mock_client.create_ticket.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_support_guidance_handles_missing_parameters(self):
        """Test support guidance fails gracefully with missing parameters."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={}  # Missing required parameters
        )
        
        executor = ActionExecutor()
        
        with pytest.raises(ValueError, match="Missing required parameters"):
            await executor._execute_support_guidance(action)


class TestProactiveCommunicationExecution:
    """Test proactive communication action execution."""
    
    @pytest.mark.asyncio
    async def test_proactive_communication_success(self):
        """Test proactive communication sends to all merchants."""
        action = Action(
            action_type="proactive_communication",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_ids": ["merchant_1", "merchant_2", "merchant_3"],
                "message": "Important update about your migration",
                "subject": "Migration Update",
                "channel": "email"
            }
        )
        
        # Mock notification service
        mock_results = {
            "merchant_1": True,
            "merchant_2": True,
            "merchant_3": True
        }
        
        executor = ActionExecutor()
        
        with patch.object(
            executor.notification_service,
            'send_proactive_communication',
            return_value=mock_results
        ):
            result = await executor._execute_proactive_communication(action)
            
            assert result.success is True
            assert result.result["merchants_notified"] == 3
            assert result.result["total_merchants"] == 3
    
    @pytest.mark.asyncio
    async def test_proactive_communication_partial_failure(self):
        """Test proactive communication handles partial failures."""
        action = Action(
            action_type="proactive_communication",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_ids": ["merchant_1", "merchant_2", "merchant_3"],
                "message": "Important update",
                "subject": "Update",
                "channel": "email"
            }
        )
        
        # Mock partial failure
        mock_results = {
            "merchant_1": True,
            "merchant_2": False,
            "merchant_3": True
        }
        
        executor = ActionExecutor()
        
        with patch.object(
            executor.notification_service,
            'send_proactive_communication',
            return_value=mock_results
        ):
            result = await executor._execute_proactive_communication(action)
            
            assert result.success is True  # Still successful if at least one sent
            assert result.result["merchants_notified"] == 2
            assert result.result["total_merchants"] == 3


class TestEngineeringEscalationExecution:
    """Test engineering escalation action execution."""
    
    @pytest.mark.asyncio
    async def test_escalation_creates_ticket_with_context(self):
        """Test escalation creates ticket with complete context."""
        action = Action(
            action_type="engineering_escalation",
            risk_level="high",
            status="pending",
            parameters={
                "issue_id": "issue_123",
                "merchant_id": "merchant_456",
                "root_cause": {
                    "category": "platform_regression",
                    "confidence": 0.92,
                    "reasoning": "API endpoint returning 500 errors",
                    "evidence": ["Error logs", "Multiple merchants affected"]
                },
                "signals": ["signal_1", "signal_2"],
                "priority": "urgent"
            }
        )
        
        # Mock support system client
        mock_client = AsyncMock()
        mock_client.create_ticket = AsyncMock(return_value={"id": "T-ESC-789"})
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            result = await executor._execute_escalation(action)
            
            assert result.success is True
            assert result.result["escalation_ticket_id"] == "T-ESC-789"
            assert result.result["issue_id"] == "issue_123"
            
            # Verify ticket was created with context
            mock_client.create_ticket.assert_called_once()
            call_kwargs = mock_client.create_ticket.call_args.kwargs
            assert "issue_123" in call_kwargs["description"]
            assert "platform_regression" in call_kwargs["description"]


class TestTemporaryMitigationExecution:
    """Test temporary mitigation action execution."""
    
    @pytest.mark.asyncio
    async def test_mitigation_applies_config_change(self):
        """Test mitigation applies configuration change with rollback data."""
        action = Action(
            action_type="temporary_mitigation",
            risk_level="high",
            status="pending",
            parameters={
                "resource_type": "merchant_config",
                "resource_id": "merchant_123",
                "config_changes": {"api_timeout": "60"},
                "current_config": {"api_timeout": "30"},
                "reason": "Temporary fix for timeout issues"
            }
        )
        
        # Mock config manager
        mock_change = MagicMock()
        mock_change.change_id = "change_abc"
        
        mock_rollback_data = {
            "change_id": "change_abc",
            "resource_type": "merchant_config",
            "resource_id": "merchant_123",
            "rollback_config": {"api_timeout": "30"},
            "snapshot_id": "snapshot_xyz",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        executor = ActionExecutor()
        
        with patch.object(
            executor.config_manager,
            'apply_config_change',
            return_value=(True, mock_change, None)
        ), patch.object(
            executor.config_manager,
            'get_rollback_data',
            return_value=mock_rollback_data
        ):
            result = await executor._execute_mitigation(action)
            
            assert result.success is True
            assert result.result["change_id"] == "change_abc"
            assert "rollback_data" in result.result
            assert result.result["rollback_data"]["change_id"] == "change_abc"
    
    @pytest.mark.asyncio
    async def test_mitigation_handles_config_validation_failure(self):
        """Test mitigation handles configuration validation failures."""
        action = Action(
            action_type="temporary_mitigation",
            risk_level="high",
            status="pending",
            parameters={
                "resource_type": "merchant_config",
                "resource_id": "merchant_123",
                "config_changes": {"invalid_field": "value"},
                "current_config": {"api_timeout": "30"},
                "reason": "Test"
            }
        )
        
        executor = ActionExecutor()
        
        with patch.object(
            executor.config_manager,
            'apply_config_change',
            return_value=(False, None, "Validation failed")
        ):
            with pytest.raises(ValueError, match="Config change failed"):
                await executor._execute_mitigation(action)


class TestDocumentationUpdateExecution:
    """Test documentation update action execution."""
    
    @pytest.mark.asyncio
    async def test_doc_update_creates_ticket(self):
        """Test documentation update creates update request."""
        action = Action(
            action_type="documentation_update",
            risk_level="low",
            status="pending",
            parameters={
                "doc_section": "Webhook Configuration",
                "issue_description": "Missing information about webhook retry logic",
                "suggested_update": "Add section explaining retry behavior"
            }
        )
        
        # Mock support system client
        mock_client = AsyncMock()
        mock_client.create_ticket = AsyncMock(return_value={"id": "T-DOC-456"})
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            result = await executor._execute_doc_update(action)
            
            assert result.success is True
            assert result.result["doc_update_ticket_id"] == "T-DOC-456"
            assert result.result["doc_section"] == "Webhook Configuration"


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Test that transient errors trigger retry."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test message",
                "support_system": "zendesk"
            }
        )
        
        # Mock client that fails twice then succeeds
        mock_client = AsyncMock()
        mock_client.create_ticket = AsyncMock(
            side_effect=[
                ConnectionError("Connection failed"),
                ConnectionError("Connection failed"),
                {"id": "T-SUCCESS"}
            ]
        )
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            result = await executor._execute_with_retry(action)
            
            # Should succeed after retries
            assert result.success is True
            assert mock_client.create_ticket.call_count == 3
    
    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(self):
        """Test that permanent errors don't trigger retry."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test message",
                "support_system": "zendesk"
            }
        )
        
        # Mock client that fails with permanent error
        mock_client = AsyncMock()
        mock_client.create_ticket = AsyncMock(
            side_effect=ValueError("Invalid parameters")
        )
        
        executor = ActionExecutor()
        
        with patch.object(executor.support_integrations, 'get_client', return_value=mock_client):
            with pytest.raises(ValueError):
                await executor._execute_with_retry(action)
            
            # Should only try once for permanent errors
            assert mock_client.create_ticket.call_count == 1


class TestAuditTrailRecording:
    """Test audit trail recording."""
    
    @pytest.mark.asyncio
    async def test_audit_trail_records_successful_action(self):
        """Test that successful actions are recorded in audit trail."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test",
                "support_system": "zendesk"
            }
        )
        
        executor = ActionExecutor()
        
        # Mock successful execution
        mock_result = ActionResult(
            action_id=action.action_id,
            success=True,
            executed_at=datetime.utcnow(),
            result={"ticket_id": "T-123"}
        )
        
        with patch.object(
            executor,
            '_execute_with_retry',
            return_value=mock_result
        ), patch.object(
            executor.audit_trail,
            'record_action',
            new_callable=AsyncMock
        ) as mock_record, patch.object(
            executor.rate_limiter,
            'check_rate_limit',
            return_value=(True, 1, 10)
        ), patch.object(
            executor.rate_limiter,
            'flag_excessive_actions',
            return_value=False
        ):
            result = await executor.execute(action, issue_id="issue_123")
            
            # Verify audit trail was recorded
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args.kwargs["issue_id"] == "issue_123"
            assert call_args.kwargs["action"].action_id == action.action_id
            assert call_args.kwargs["result"].success is True


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excessive_actions(self):
        """Test that rate limiting blocks actions when limit exceeded."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test",
                "support_system": "zendesk"
            }
        )
        
        executor = ActionExecutor()
        
        # Mock rate limit exceeded
        with patch.object(
            executor.rate_limiter,
            'check_rate_limit',
            return_value=(False, 11, 10)  # Exceeded limit
        ):
            result = await executor.execute(action)
            
            # Should fail due to rate limit
            assert result.success is False
            assert "Rate limit exceeded" in result.error_message
    
    @pytest.mark.asyncio
    async def test_excessive_actions_flagged(self):
        """Test that excessive actions are flagged for review."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test",
                "support_system": "zendesk"
            }
        )
        
        executor = ActionExecutor()
        
        # Mock flagging
        with patch.object(
            executor.rate_limiter,
            'check_rate_limit',
            return_value=(True, 10, 10)
        ), patch.object(
            executor.rate_limiter,
            'flag_excessive_actions',
            return_value=True
        ) as mock_flag, patch.object(
            executor,
            '_execute_with_retry',
            return_value=ActionResult(
                action_id=action.action_id,
                success=True,
                executed_at=datetime.utcnow(),
                result={}
            )
        ):
            await executor.execute(action)
            
            # Verify flagging was called
            mock_flag.assert_called_once()


class TestErrorHandling:
    """Test error handling and failure escalation."""
    
    @pytest.mark.asyncio
    async def test_failed_action_escalation(self):
        """Test that failed actions are escalated."""
        action = Action(
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "merchant_123",
                "message": "Test",
                "support_system": "zendesk"
            }
        )
        
        executor = ActionExecutor()
        
        # Mock failure
        with patch.object(
            executor,
            '_execute_with_retry',
            side_effect=Exception("Test failure")
        ), patch.object(
            executor,
            '_escalate_failed_action',
            new_callable=AsyncMock
        ) as mock_escalate, patch.object(
            executor.rate_limiter,
            'check_rate_limit',
            return_value=(True, 1, 10)
        ), patch.object(
            executor.rate_limiter,
            'flag_excessive_actions',
            return_value=False
        ):
            result = await executor.execute(action)
            
            # Verify escalation was called
            assert result.success is False
            mock_escalate.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
