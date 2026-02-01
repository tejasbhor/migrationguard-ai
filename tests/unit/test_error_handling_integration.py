"""
Unit tests for error handling integration.

Tests verify that safe mode works correctly with decision engine and action executor
to handle errors and maintain system resilience.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from migrationguard_ai.core.safe_mode import (
    SafeModeManager,
    SafeModeDetector,
    SafeModeReason,
)
from migrationguard_ai.services.decision_engine import DecisionEngine
from migrationguard_ai.services.action_executor import ActionExecutor
from migrationguard_ai.core.schemas import RootCauseAnalysis, Action


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with services."""
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test that circuit breaker opens after threshold failures."""
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60
        )
        
        # Simulate failures
        for _ in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "OPEN"
    
    def test_circuit_breaker_half_open_after_timeout(self):
        """Test that circuit breaker enters half-open state after timeout."""
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0  # Immediate recovery for testing
        )
        
        # Open the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        assert circuit_breaker.state == "OPEN"
        
        # Should transition to half-open
        assert circuit_breaker.can_execute()
        assert circuit_breaker.state == "HALF_OPEN"
    
    def test_circuit_breaker_closes_on_success(self):
        """Test that circuit breaker closes after successful call in half-open."""
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0
        )
        
        # Open the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        # Transition to half-open
        circuit_breaker.can_execute()
        
        # Record success
        circuit_breaker.record_success()
        
        assert circuit_breaker.state == "CLOSED"
    
    def test_circuit_breaker_prevents_execution_when_open(self):
        """Test that circuit breaker prevents execution when open."""
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60  # Long timeout
        )
        
        # Open the circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        # Should not allow execution
        assert not circuit_breaker.can_execute()


class TestGracefulDegradationIntegration:
    """Test graceful degradation integration."""
    
    def test_rule_based_analyzer_fallback(self):
        """Test that rule-based analyzer provides fallback for Claude API."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        # Test auth error detection
        signals = [
            {
                "error_message": "401 Unauthorized",
                "error_code": "auth_failed"
            }
        ]
        
        analysis = analyzer.analyze(signals, {})
        
        assert analysis is not None
        assert analysis.category == "authentication_error"
        assert analysis.confidence >= 0.5
        assert len(analysis.recommended_actions) > 0
    
    def test_postgresql_pattern_matcher_fallback(self):
        """Test that PostgreSQL provides fallback for Elasticsearch."""
        matcher = PostgreSQLPatternMatcher(db_session=None)
        
        # Should return None for now (simplified implementation)
        result = matcher.match_pattern(
            error_message="Test error",
            error_code="TEST_ERROR"
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_redis_signal_buffer_fallback(self):
        """Test that Redis buffers signals when Kafka fails."""
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.llen = AsyncMock(return_value=5)
        
        buffer = RedisSignalBuffer(redis_client=mock_redis)
        
        # Buffer a signal
        signal = {"signal_id": "test_123", "data": "test"}
        success = await buffer.buffer_signal(signal)
        
        assert success is True
        mock_redis.lpush.assert_called_once()
    
    def test_degradation_manager_tracks_state(self):
        """Test that degradation manager tracks service states."""
        manager = GracefulDegradationManager()
        
        # Set degraded state
        manager.set_degraded("claude_api", True, "API unavailable")
        
        assert manager.is_degraded("claude_api")
        assert manager.is_any_degraded()
        
        # Clear degraded state
        manager.set_degraded("claude_api", False)
        
        assert not manager.is_degraded("claude_api")
        assert not manager.is_any_degraded()


class TestSafeModeIntegration:
    """Test safe mode integration with decision engine and action executor."""
    
    def test_safe_mode_activates_on_critical_error(self):
        """Test that safe mode activates on critical errors."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        # Trigger critical error
        detector.check_critical_error(
            "database_connection_loss",
            "PostgreSQL connection lost"
        )
        
        assert manager.is_active()
        assert manager.get_activation_reason() == SafeModeReason.DATABASE_FAILURE
    
    def test_safe_mode_requires_manual_deactivation(self):
        """Test that safe mode requires manual deactivation."""
        manager = SafeModeManager()
        
        # Activate safe mode
        manager.activate(SafeModeReason.CRITICAL_ERROR)
        
        assert manager.is_active()
        
        # Deactivate requires operator ID
        result = manager.deactivate("operator_123")
        
        assert result is True
        assert not manager.is_active()
    
    def test_decision_engine_forces_approval_in_safe_mode(self):
        """Test that decision engine forces approval when safe mode is active."""
        engine = DecisionEngine()
        
        # Activate safe mode
        engine.safe_mode_manager.activate(SafeModeReason.CONFIDENCE_DRIFT)
        
        # Create analysis
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=0.95,
            reasoning="Test reasoning",
            evidence=["Test evidence"],
            recommended_actions=["Test action"]
        )
        
        # Make decision
        decision = engine.decide(
            analysis=analysis,
            context={"merchant_id": "test_merchant"},
            issue_id="test_issue"
        )
        
        # Should require approval even with high confidence
        assert decision.requires_approval is True
    
    @pytest.mark.asyncio
    async def test_action_executor_blocks_in_safe_mode(self):
        """Test that action executor blocks execution in safe mode."""
        executor = ActionExecutor()
        
        # Activate safe mode
        executor.safe_mode_manager.activate(SafeModeReason.EXCESSIVE_ACTIONS)
        
        # Create action
        action = Action(
            action_id="test_action",
            action_type="support_guidance",
            risk_level="low",
            status="pending",
            parameters={
                "merchant_id": "test_merchant",
                "message": "Test message"
            }
        )
        
        # Try to execute
        result = await executor.execute(action)
        
        # Should be blocked
        assert result.success is False
        assert "Safe mode active" in result.error_message


class TestErrorHandlingWorkflow:
    """Test complete error handling workflow."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_triggers_graceful_degradation(self):
        """Test that circuit breaker failure triggers graceful degradation."""
        # Create circuit breaker
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=60
        )
        
        # Create degradation manager
        degradation_manager = GracefulDegradationManager()
        
        # Simulate failures
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        
        # Circuit should be open
        assert circuit_breaker.state == "OPEN"
        
        # Set degraded state
        degradation_manager.set_degraded(
            "claude_api",
            True,
            "Circuit breaker open"
        )
        
        assert degradation_manager.is_degraded("claude_api")
    
    def test_excessive_errors_trigger_safe_mode(self):
        """Test that excessive errors trigger safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        # Simulate multiple critical errors
        detector.check_critical_error(
            "database_connection_loss",
            "Connection lost"
        )
        
        # Safe mode should be active
        assert manager.is_active()
    
    def test_confidence_drift_triggers_safe_mode(self):
        """Test that confidence drift triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        # Simulate confidence drift
        detector.check_confidence_drift(
            expected_accuracy=0.90,
            actual_accuracy=0.75,
            threshold=0.05
        )
        
        # Safe mode should be active
        assert manager.is_active()
        assert manager.get_activation_reason() == SafeModeReason.CONFIDENCE_DRIFT


class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after errors."""
        circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0
        )
        
        # Open circuit
        circuit_breaker.record_failure()
        circuit_breaker.record_failure()
        assert circuit_breaker.state == "OPEN"
        
        # Transition to half-open
        circuit_breaker.can_execute()
        assert circuit_breaker.state == "HALF_OPEN"
        
        # Recover
        circuit_breaker.record_success()
        assert circuit_breaker.state == "CLOSED"
    
    def test_graceful_degradation_recovery(self):
        """Test graceful degradation recovery."""
        manager = GracefulDegradationManager()
        
        # Set degraded
        manager.set_degraded("elasticsearch", True, "Connection failed")
        assert manager.is_degraded("elasticsearch")
        
        # Recover
        manager.set_degraded("elasticsearch", False)
        assert not manager.is_degraded("elasticsearch")
    
    def test_safe_mode_recovery(self):
        """Test safe mode recovery."""
        manager = SafeModeManager()
        
        # Activate
        manager.activate(SafeModeReason.CRITICAL_ERROR)
        assert manager.is_active()
        
        # Deactivate
        manager.deactivate("operator_123")
        assert not manager.is_active()


class TestErrorHandlingEdgeCases:
    """Test edge cases in error handling."""
    
    def test_multiple_circuit_breakers_independent(self):
        """Test that multiple circuit breakers operate independently."""
        cb1 = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=60)
        cb2 = AsyncCircuitBreaker(failure_threshold=2, recovery_timeout=60)
        
        # Open first circuit
        cb1.record_failure()
        cb1.record_failure()
        
        # Second circuit should still be closed
        assert cb1.state == "OPEN"
        assert cb2.state == "CLOSED"
    
    def test_safe_mode_prevents_multiple_activations(self):
        """Test that safe mode prevents multiple activations."""
        manager = SafeModeManager()
        
        # First activation
        manager.activate(SafeModeReason.CRITICAL_ERROR, {"error": "Error 1"})
        first_time = manager._activation_time
        
        # Second activation should be ignored
        manager.activate(SafeModeReason.CONFIDENCE_DRIFT, {"error": "Error 2"})
        
        # Should still have first activation
        assert manager._activation_time == first_time
        assert manager.get_activation_reason() == SafeModeReason.CRITICAL_ERROR
    
    def test_degradation_manager_multiple_services(self):
        """Test degradation manager with multiple services."""
        manager = GracefulDegradationManager()
        
        # Degrade multiple services
        manager.set_degraded("claude_api", True, "API down")
        manager.set_degraded("elasticsearch", True, "ES down")
        
        assert manager.is_degraded("claude_api")
        assert manager.is_degraded("elasticsearch")
        assert manager.is_any_degraded()
        
        # Recover one service
        manager.set_degraded("claude_api", False)
        
        assert not manager.is_degraded("claude_api")
        assert manager.is_degraded("elasticsearch")
        assert manager.is_any_degraded()
        
        # Recover all services
        manager.set_degraded("elasticsearch", False)
        
        assert not manager.is_any_degraded()
