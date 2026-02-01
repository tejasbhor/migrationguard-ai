"""
Unit tests for safe mode functionality.

Tests verify that safe mode activates correctly for critical errors
and anomalies, and that it properly stops automated actions.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from migrationguard_ai.core.safe_mode import (
    SafeModeManager,
    SafeModeDetector,
    SafeModeReason,
    get_safe_mode_manager,
    get_safe_mode_detector,
)


class TestSafeModeManager:
    """Test safe mode manager functionality."""
    
    def test_initialization(self):
        """Test that manager initializes in inactive state."""
        manager = SafeModeManager()
        
        assert manager.is_active() is False
        assert manager.get_activation_reason() is None
        assert manager.get_activation_context() == {}
    
    def test_activate_safe_mode(self):
        """Test activating safe mode."""
        manager = SafeModeManager()
        
        manager.activate(
            SafeModeReason.CRITICAL_ERROR,
            {"error": "Database connection lost"}
        )
        
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.CRITICAL_ERROR
        assert manager.get_activation_context()["error"] == "Database connection lost"
    
    def test_activate_logs_critical_message(self):
        """Test that activation logs critical message."""
        with patch('migrationguard_ai.core.safe_mode.logger') as mock_logger:
            manager = SafeModeManager()
            
            manager.activate(SafeModeReason.CRITICAL_ERROR)
            
            # Should log critical message
            assert mock_logger.critical.called
            call_args = mock_logger.critical.call_args
            assert "SAFE MODE ACTIVATED" in str(call_args)
    
    def test_activate_when_already_active(self):
        """Test that activating when already active logs warning."""
        with patch('migrationguard_ai.core.safe_mode.logger') as mock_logger:
            manager = SafeModeManager()
            
            manager.activate(SafeModeReason.CRITICAL_ERROR)
            manager.activate(SafeModeReason.CONFIDENCE_DRIFT)
            
            # Should log warning
            assert mock_logger.warning.called
    
    def test_deactivate_safe_mode(self):
        """Test deactivating safe mode."""
        manager = SafeModeManager()
        
        manager.activate(SafeModeReason.CRITICAL_ERROR)
        result = manager.deactivate("operator_123")
        
        assert result is True
        assert manager.is_active() is False
    
    def test_deactivate_when_not_active(self):
        """Test deactivating when not active returns False."""
        manager = SafeModeManager()
        
        result = manager.deactivate("operator_123")
        
        assert result is False
    
    def test_get_status_when_active(self):
        """Test getting status when safe mode is active."""
        manager = SafeModeManager()
        
        manager.activate(
            SafeModeReason.CONFIDENCE_DRIFT,
            {"drift": 0.08}
        )
        
        status = manager.get_status()
        
        assert status["active"] is True
        assert status["activation_reason"] == "confidence_drift"
        assert status["activation_context"]["drift"] == 0.08
        assert status["activation_time"] is not None
    
    def test_get_status_after_deactivation(self):
        """Test getting status after deactivation."""
        manager = SafeModeManager()
        
        manager.activate(SafeModeReason.CRITICAL_ERROR)
        manager.deactivate("operator_123")
        
        status = manager.get_status()
        
        assert status["active"] is False
        assert status["deactivation_time"] is not None
        assert status["deactivated_by"] == "operator_123"
        assert "duration_seconds" in status


class TestSafeModeDetector:
    """Test safe mode detector functionality."""
    
    def test_initialization(self):
        """Test detector initialization."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        assert detector.safe_mode_manager is manager
        assert detector.error_counts == {}
        assert detector.action_counts == {}
    
    def test_check_critical_error_database(self):
        """Test that database connection loss triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_critical_error(
            "database_connection_loss",
            "Connection to PostgreSQL lost",
            {"host": "localhost"}
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.DATABASE_FAILURE
    
    def test_check_critical_error_kafka(self):
        """Test that Kafka unavailability triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_critical_error(
            "kafka_broker_unavailable",
            "All Kafka brokers are down"
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.KAFKA_FAILURE
    
    def test_check_critical_error_claude_api(self):
        """Test that Claude API quota exceeded triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_critical_error(
            "claude_api_quota_exceeded",
            "API quota limit reached"
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.CLAUDE_API_FAILURE
    
    def test_check_critical_error_non_critical(self):
        """Test that non-critical errors don't trigger safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_critical_error(
            "minor_error",
            "Some minor issue"
        )
        
        assert result is False
        assert manager.is_active() is False
    
    def test_check_confidence_drift_triggers_safe_mode(self):
        """Test that confidence drift triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_confidence_drift(
            expected_accuracy=0.90,
            actual_accuracy=0.82,
            threshold=0.05
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.CONFIDENCE_DRIFT
        
        context = manager.get_activation_context()
        assert abs(context["drift"] - 0.08) < 0.0001  # Use approximate comparison for floats
    
    def test_check_confidence_drift_within_threshold(self):
        """Test that small drift doesn't trigger safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_confidence_drift(
            expected_accuracy=0.90,
            actual_accuracy=0.88,
            threshold=0.05
        )
        
        assert result is False
        assert manager.is_active() is False
    
    def test_check_excessive_actions_triggers_safe_mode(self):
        """Test that excessive actions trigger safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_excessive_actions(
            action_type="temporary_mitigation",
            merchant_id="merchant_123",
            count=25,
            time_window_minutes=5,
            threshold=20
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.EXCESSIVE_ACTIONS
        
        context = manager.get_activation_context()
        assert context["count"] == 25
        assert context["merchant_id"] == "merchant_123"
    
    def test_check_excessive_actions_within_threshold(self):
        """Test that normal action count doesn't trigger safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_excessive_actions(
            action_type="support_guidance",
            merchant_id="merchant_123",
            count=15,
            threshold=20
        )
        
        assert result is False
        assert manager.is_active() is False
    
    def test_check_anomalous_behavior(self):
        """Test that anomalous behavior triggers safe mode."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        result = detector.check_anomalous_behavior(
            behavior_type="unusual_pattern",
            description="Unexpected spike in error rates",
            context={"error_rate": 0.45}
        )
        
        assert result is True
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.ANOMALOUS_BEHAVIOR
        
        context = manager.get_activation_context()
        assert context["behavior_type"] == "unusual_pattern"
        assert context["error_rate"] == 0.45


class TestSafeModeReasons:
    """Test safe mode reason enum."""
    
    def test_all_reasons_defined(self):
        """Test that all expected reasons are defined."""
        expected_reasons = [
            "CRITICAL_ERROR",
            "ANOMALOUS_BEHAVIOR",
            "CONFIDENCE_DRIFT",
            "EXCESSIVE_ACTIONS",
            "MANUAL_ACTIVATION",
            "DATABASE_FAILURE",
            "KAFKA_FAILURE",
            "CLAUDE_API_FAILURE",
        ]
        
        for reason in expected_reasons:
            assert hasattr(SafeModeReason, reason)
    
    def test_reason_values(self):
        """Test that reason values are correct."""
        assert SafeModeReason.CRITICAL_ERROR.value == "critical_error"
        assert SafeModeReason.CONFIDENCE_DRIFT.value == "confidence_drift"
        assert SafeModeReason.DATABASE_FAILURE.value == "database_failure"


class TestSafeModeIntegration:
    """Test safe mode integration scenarios."""
    
    def test_multiple_activations_same_reason(self):
        """Test multiple activations with same reason."""
        manager = SafeModeManager()
        
        manager.activate(SafeModeReason.CRITICAL_ERROR, {"error": "Error 1"})
        first_time = manager._activation_time
        
        # Try to activate again
        manager.activate(SafeModeReason.CRITICAL_ERROR, {"error": "Error 2"})
        
        # Should still be the first activation
        assert manager._activation_time == first_time
        assert manager.get_activation_context()["error"] == "Error 1"
    
    def test_activation_deactivation_cycle(self):
        """Test full activation and deactivation cycle."""
        manager = SafeModeManager()
        
        # Activate
        manager.activate(SafeModeReason.CONFIDENCE_DRIFT)
        assert manager.is_active() is True
        
        # Deactivate
        manager.deactivate("operator_123")
        assert manager.is_active() is False
        
        # Can activate again
        manager.activate(SafeModeReason.EXCESSIVE_ACTIONS)
        assert manager.is_active() is True
        assert manager.get_activation_reason() == SafeModeReason.EXCESSIVE_ACTIONS
    
    def test_detector_with_multiple_checks(self):
        """Test detector with multiple check types."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        # First check doesn't trigger
        result1 = detector.check_confidence_drift(0.90, 0.88, 0.05)
        assert result1 is False
        
        # Second check triggers
        result2 = detector.check_critical_error(
            "database_connection_loss",
            "Connection lost"
        )
        assert result2 is True
        assert manager.is_active() is True


class TestSafeModeGlobalInstances:
    """Test global singleton instances."""
    
    def test_get_safe_mode_manager_singleton(self):
        """Test that get_safe_mode_manager returns singleton."""
        manager1 = get_safe_mode_manager()
        manager2 = get_safe_mode_manager()
        
        assert manager1 is manager2
    
    def test_get_safe_mode_detector_singleton(self):
        """Test that get_safe_mode_detector returns singleton."""
        detector1 = get_safe_mode_detector()
        detector2 = get_safe_mode_detector()
        
        assert detector1 is detector2
    
    def test_detector_uses_manager_singleton(self):
        """Test that detector uses the manager singleton."""
        manager = get_safe_mode_manager()
        detector = get_safe_mode_detector()
        
        assert detector.safe_mode_manager is manager


class TestSafeModeEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_activate_with_none_context(self):
        """Test activating with None context."""
        manager = SafeModeManager()
        
        manager.activate(SafeModeReason.CRITICAL_ERROR, None)
        
        assert manager.is_active() is True
        assert manager.get_activation_context() == {}
    
    def test_get_status_never_activated(self):
        """Test getting status when never activated."""
        manager = SafeModeManager()
        
        status = manager.get_status()
        
        assert status["active"] is False
        assert status["activation_time"] is None
        assert status["activation_reason"] is None
    
    def test_confidence_drift_with_negative_drift(self):
        """Test confidence drift calculation with negative drift."""
        manager = SafeModeManager()
        detector = SafeModeDetector(manager)
        
        # Actual is higher than expected (negative drift)
        result = detector.check_confidence_drift(
            expected_accuracy=0.80,
            actual_accuracy=0.90,
            threshold=0.05
        )
        
        # Should still trigger if absolute drift exceeds threshold
        assert result is True
        context = manager.get_activation_context()
        assert abs(context["drift"] - 0.10) < 0.0001  # Use approximate comparison for floats
