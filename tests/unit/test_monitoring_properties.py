"""
Property-Based Tests for Monitoring and Observability.

This module contains property-based tests that validate monitoring
and observability requirements including logging, metrics, and alerting.

**Property 40: Significant event logging**
**Validates: Requirements 15.2**

**Property 41: Error logging completeness**
**Validates: Requirements 15.3**

**Property 42: Critical error alerting**
**Validates: Requirements 15.6**
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock, patch
import structlog
from datetime import datetime

from migrationguard_ai.core.logging import (
    get_logger,
    log_event,
    log_error,
    log_decision,
    log_action_execution,
    log_performance,
)
from migrationguard_ai.services.alert_manager import (
    AlertManager,
    AlertSeverity,
    AlertChannel,
)
from migrationguard_ai.services.redis_client import RedisClient


# Strategies for generating test data
event_types = st.sampled_from([
    "signal_ingested",
    "pattern_detected",
    "root_cause_analyzed",
    "decision_made",
    "action_executed",
    "approval_requested",
    "approval_granted",
    "approval_rejected",
])

log_levels = st.sampled_from(["debug", "info", "warning", "error", "critical"])

error_types = st.sampled_from([
    "ValueError",
    "TypeError",
    "RuntimeError",
    "ConnectionError",
    "TimeoutError",
    "DatabaseError",
])

action_types = st.sampled_from([
    "support_guidance",
    "proactive_communication",
    "engineering_escalation",
    "temporary_mitigation",
    "documentation_update",
])

risk_levels = st.sampled_from(["low", "medium", "high", "critical"])


class TestSignificantEventLogging:
    """
    Property 40: Significant event logging.
    
    Tests that all significant events are logged with appropriate
    context and structure.
    
    Validates: Requirements 15.2
    """
    
    @given(
        event_type=event_types,
        issue_id=st.text(min_size=5, max_size=20),
        merchant_id=st.text(min_size=5, max_size=20),
    )
    @settings(max_examples=100)
    def test_significant_events_are_logged(
        self,
        event_type: str,
        issue_id: str,
        merchant_id: str
    ):
        """
        Property: All significant events must be logged.
        
        Given any significant event type,
        When the event occurs,
        Then it must be logged with appropriate context.
        """
        logger = get_logger(__name__)
        
        # Capture log output
        with patch.object(logger, 'info') as mock_log:
            log_event(
                logger,
                "info",
                event_type,
                issue_id=issue_id,
                merchant_id=merchant_id,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Verify event was logged
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify event name is present
            assert call_args[0][0] == event_type
            
            # Verify context is included
            assert "issue_id" in call_args[1]
            assert "merchant_id" in call_args[1]
            assert "timestamp" in call_args[1]
    
    @given(
        action_type=action_types,
        action_id=st.text(min_size=5, max_size=20),
        success=st.booleans(),
        duration_ms=st.floats(min_value=0, max_value=60000),
    )
    @settings(max_examples=100)
    def test_action_execution_events_logged(
        self,
        action_type: str,
        action_id: str,
        success: bool,
        duration_ms: float
    ):
        """
        Property: Action execution events must be logged.
        
        Given any action execution,
        When the action completes,
        Then the execution must be logged with outcome and duration.
        """
        logger = get_logger(__name__)
        
        with patch.object(logger, 'info') as mock_log:
            log_action_execution(
                logger,
                action_id=action_id,
                action_type=action_type,
                success=success,
                duration_ms=duration_ms
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify required fields
            assert call_args[0][0] == "action_executed"
            assert call_args[1]["action_id"] == action_id
            assert call_args[1]["action_type"] == action_type
            assert call_args[1]["success"] == success
            assert call_args[1]["duration_ms"] == duration_ms
    
    @given(
        issue_id=st.text(min_size=5, max_size=20),
        action_type=action_types,
        risk_level=risk_levels,
        confidence=st.floats(min_value=0.0, max_value=1.0),
        requires_approval=st.booleans(),
    )
    @settings(max_examples=100)
    def test_decision_events_logged(
        self,
        issue_id: str,
        action_type: str,
        risk_level: str,
        confidence: float,
        requires_approval: bool
    ):
        """
        Property: Decision events must be logged with full context.
        
        Given any decision made by the system,
        When the decision is finalized,
        Then it must be logged with risk level, confidence, and approval status.
        """
        logger = get_logger(__name__)
        
        with patch.object(logger, 'info') as mock_log:
            log_decision(
                logger,
                issue_id=issue_id,
                action_type=action_type,
                risk_level=risk_level,
                confidence=confidence,
                requires_approval=requires_approval
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify decision logging structure
            assert call_args[0][0] == "decision_made"
            assert call_args[1]["issue_id"] == issue_id
            assert call_args[1]["action_type"] == action_type
            assert call_args[1]["risk_level"] == risk_level
            assert call_args[1]["confidence"] == confidence
            assert call_args[1]["requires_approval"] == requires_approval
    
    @given(
        operation=st.text(min_size=3, max_size=50),
        duration_ms=st.floats(min_value=0, max_value=120000),
    )
    @settings(max_examples=100)
    def test_performance_metrics_logged(
        self,
        operation: str,
        duration_ms: float
    ):
        """
        Property: Performance metrics must be logged.
        
        Given any timed operation,
        When the operation completes,
        Then the duration must be logged.
        """
        logger = get_logger(__name__)
        
        with patch.object(logger, 'info') as mock_log:
            log_performance(
                logger,
                operation=operation,
                duration_ms=duration_ms
            )
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify performance logging
            assert call_args[0][0] == "performance_metric"
            assert call_args[1]["operation"] == operation
            assert call_args[1]["duration_ms"] == duration_ms


class TestErrorLoggingCompleteness:
    """
    Property 41: Error logging completeness.
    
    Tests that all errors are logged with complete context including
    stack traces, error types, and relevant context.
    
    Validates: Requirements 15.3
    """
    
    @given(
        error_type=error_types,
        error_message=st.text(min_size=10, max_size=200),
        event=st.text(min_size=5, max_size=50),
    )
    @settings(max_examples=100)
    def test_errors_logged_with_complete_context(
        self,
        error_type: str,
        error_message: str,
        event: str
    ):
        """
        Property: All errors must be logged with complete context.
        
        Given any error that occurs,
        When the error is logged,
        Then it must include error type, message, and stack trace.
        """
        logger = get_logger(__name__)
        
        # Create an exception dynamically
        error_class = type(error_type, (Exception,), {})
        error = error_class(error_message)
        
        with patch.object(logger, 'error') as mock_log:
            log_error(logger, error, event)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify error logging completeness
            assert call_args[0][0] == event
            assert "error" in call_args[1]
            assert "error_type" in call_args[1]
            assert "exc_info" in call_args[1]
            assert call_args[1]["exc_info"] is True
            assert error_message in call_args[1]["error"]
    
    @given(
        error_message=st.text(min_size=10, max_size=200),
        context_keys=st.lists(st.text(min_size=3, max_size=20), min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_errors_include_context(
        self,
        error_message: str,
        context_keys: list
    ):
        """
        Property: Error logs must include relevant context.
        
        Given an error with context,
        When the error is logged,
        Then all context information must be included.
        """
        logger = get_logger(__name__)
        error = RuntimeError(error_message)
        
        # Build context dictionary
        context = {key: f"value_{i}" for i, key in enumerate(context_keys)}
        
        with patch.object(logger, 'error') as mock_log:
            log_error(logger, error, "test_event", **context)
            
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            
            # Verify all context keys are present
            for key in context_keys:
                assert key in call_args[1]
    
    @given(
        log_level=log_levels,
        event=st.text(min_size=5, max_size=50),
    )
    @settings(max_examples=100)
    def test_log_levels_preserved(
        self,
        log_level: str,
        event: str
    ):
        """
        Property: Log levels must be preserved correctly.
        
        Given any log level,
        When an event is logged at that level,
        Then the correct logging method must be called.
        """
        logger = get_logger(__name__)
        
        with patch.object(logger, log_level) as mock_log:
            log_event(logger, log_level, event)
            
            mock_log.assert_called_once()


class TestCriticalErrorAlerting:
    """
    Property 42: Critical error alerting.
    
    Tests that critical errors trigger alerts to operators
    through configured channels.
    
    Validates: Requirements 15.6
    """
    
    @pytest.mark.asyncio
    @given(
        error_type=error_types,
        error_message=st.text(min_size=10, max_size=200),
    )
    @settings(max_examples=50)
    async def test_critical_errors_trigger_alerts(
        self,
        error_type: str,
        error_message: str
    ):
        """
        Property: Critical errors must trigger alerts.
        
        Given a critical error,
        When the error occurs,
        Then an alert must be sent to operators.
        """
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.get.return_value = None  # Not in cooldown
        mock_redis.set.return_value = None
        
        alert_manager = AlertManager(mock_redis)
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                with patch.object(alert_manager, '_send_pagerduty_alert', new_callable=AsyncMock):
                    result = await alert_manager.send_alert(
                        "critical_error",
                        {
                            "error_type": error_type,
                            "error_message": error_message
                        }
                    )
        
        # Verify alert was sent
        assert result is True
    
    @pytest.mark.asyncio
    @given(
        error_rate=st.floats(min_value=0.06, max_value=1.0),
    )
    @settings(max_examples=50)
    async def test_high_error_rate_triggers_alert(
        self,
        error_rate: float
    ):
        """
        Property: High error rates must trigger alerts.
        
        Given an error rate above threshold,
        When the threshold is exceeded,
        Then an alert must be sent.
        """
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.get.return_value = None
        mock_redis.set.return_value = None
        
        alert_manager = AlertManager(mock_redis)
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": error_rate}
                )
        
        assert result is True
    
    @pytest.mark.asyncio
    @given(
        calibration_error=st.floats(min_value=0.11, max_value=1.0),
    )
    @settings(max_examples=50)
    async def test_confidence_drift_triggers_alert(
        self,
        calibration_error: float
    ):
        """
        Property: Confidence calibration drift must trigger alerts.
        
        Given confidence calibration error above threshold,
        When drift is detected,
        Then an alert must be sent.
        """
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.get.return_value = None
        mock_redis.set.return_value = None
        
        alert_manager = AlertManager(mock_redis)
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result = await alert_manager.send_alert(
                    "confidence_drift",
                    {"calibration_error": calibration_error}
                )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_critical_alerts_use_all_channels(self):
        """
        Property: Critical alerts must use all configured channels.
        
        Given a critical alert,
        When the alert is sent,
        Then it must be delivered via email, Slack, and PagerDuty.
        """
        mock_redis = AsyncMock(spec=RedisClient)
        mock_redis.get.return_value = None
        mock_redis.set.return_value = None
        
        alert_manager = AlertManager(mock_redis)
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock) as mock_email:
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock) as mock_slack:
                with patch.object(alert_manager, '_send_pagerduty_alert', new_callable=AsyncMock) as mock_pd:
                    await alert_manager.send_alert(
                        "critical_error",
                        {"error_type": "DatabaseError", "error_message": "Connection failed"}
                    )
                    
                    # Verify all channels were used
                    mock_email.assert_called_once()
                    mock_slack.assert_called_once()
                    mock_pd.assert_called_once()
    
    @pytest.mark.asyncio
    @given(
        cooldown_minutes=st.integers(min_value=1, max_value=60),
    )
    @settings(max_examples=50)
    async def test_alert_cooldown_prevents_spam(
        self,
        cooldown_minutes: int
    ):
        """
        Property: Alert cooldown must prevent notification spam.
        
        Given an alert with cooldown period,
        When the alert is triggered multiple times,
        Then subsequent alerts must be suppressed during cooldown.
        """
        mock_redis = AsyncMock(spec=RedisClient)
        
        alert_manager = AlertManager(mock_redis)
        
        # First alert - not in cooldown
        mock_redis.get.return_value = None
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result1 = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": 0.10}
                )
        
        assert result1 is True
        
        # Second alert - in cooldown
        mock_redis.get.return_value = "1"
        result2 = await alert_manager.send_alert(
            "high_error_rate",
            {"error_rate": 0.10}
        )
        
        assert result2 is False
