"""
Safe Mode Module.

This module implements safe mode functionality to protect the system
when critical errors or anomalies are detected.

Safe mode:
- Stops all automated action execution
- Queues all decisions for human approval
- Sends alerts to operators
- Requires manual intervention to exit

Triggers:
- Critical errors (database connection loss, Kafka unavailability)
- Anomalous behavior (confidence calibration drift, unusual action patterns)
- Manual activation by operators
"""

from typing import Optional
from datetime import datetime, timezone
from enum import Enum

from migrationguard_ai.core.logging import get_logger

logger = get_logger(__name__)


class SafeModeReason(str, Enum):
    """Reasons for entering safe mode."""
    
    CRITICAL_ERROR = "critical_error"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    CONFIDENCE_DRIFT = "confidence_drift"
    EXCESSIVE_ACTIONS = "excessive_actions"
    MANUAL_ACTIVATION = "manual_activation"
    DATABASE_FAILURE = "database_failure"
    KAFKA_FAILURE = "kafka_failure"
    CLAUDE_API_FAILURE = "claude_api_failure"


class SafeModeManager:
    """
    Manager for safe mode state and operations.
    
    Coordinates safe mode activation, deactivation, and state tracking.
    """
    
    def __init__(self):
        """Initialize safe mode manager."""
        self._safe_mode_active = False
        self._activation_time: Optional[datetime] = None
        self._activation_reason: Optional[SafeModeReason] = None
        self._activation_context: dict = {}
        self._deactivation_time: Optional[datetime] = None
        self._deactivated_by: Optional[str] = None
        
        logger.info("Safe mode manager initialized")
    
    def activate(
        self,
        reason: SafeModeReason,
        context: Optional[dict] = None,
    ) -> None:
        """
        Activate safe mode.
        
        Args:
            reason: Reason for activation
            context: Additional context about the activation
        """
        if self._safe_mode_active:
            logger.warning(
                "Safe mode already active",
                current_reason=self._activation_reason,
                new_reason=reason,
            )
            return
        
        self._safe_mode_active = True
        self._activation_time = datetime.now(timezone.utc)
        self._activation_reason = reason
        self._activation_context = context or {}
        self._deactivation_time = None
        self._deactivated_by = None
        
        logger.critical(
            "SAFE MODE ACTIVATED",
            reason=reason.value,
            context=self._activation_context,
            timestamp=self._activation_time.isoformat(),
        )
    
    def deactivate(self, operator_id: str) -> bool:
        """
        Deactivate safe mode (requires manual intervention).
        
        Args:
            operator_id: ID of operator deactivating safe mode
            
        Returns:
            bool: True if deactivated, False if not active
        """
        if not self._safe_mode_active:
            logger.warning(
                "Attempted to deactivate safe mode when not active",
                operator_id=operator_id,
            )
            return False
        
        self._safe_mode_active = False
        self._deactivation_time = datetime.now(timezone.utc)
        self._deactivated_by = operator_id
        
        duration = (self._deactivation_time - self._activation_time).total_seconds()
        
        logger.warning(
            "Safe mode deactivated",
            operator_id=operator_id,
            duration_seconds=duration,
            reason=self._activation_reason.value if self._activation_reason else None,
        )
        
        return True
    
    def is_active(self) -> bool:
        """
        Check if safe mode is currently active.
        
        Returns:
            bool: True if safe mode is active
        """
        return self._safe_mode_active
    
    def get_status(self) -> dict:
        """
        Get current safe mode status.
        
        Returns:
            dict: Safe mode status information
        """
        status = {
            "active": self._safe_mode_active,
            "activation_time": self._activation_time.isoformat() if self._activation_time else None,
            "activation_reason": self._activation_reason.value if self._activation_reason else None,
            "activation_context": self._activation_context,
        }
        
        if not self._safe_mode_active and self._deactivation_time:
            status["deactivation_time"] = self._deactivation_time.isoformat()
            status["deactivated_by"] = self._deactivated_by
            
            if self._activation_time:
                duration = (self._deactivation_time - self._activation_time).total_seconds()
                status["duration_seconds"] = duration
        
        return status
    
    def get_activation_reason(self) -> Optional[SafeModeReason]:
        """
        Get the reason for current safe mode activation.
        
        Returns:
            Optional[SafeModeReason]: Activation reason or None if not active
        """
        return self._activation_reason if self._safe_mode_active else None
    
    def get_activation_context(self) -> dict:
        """
        Get the context for current safe mode activation.
        
        Returns:
            dict: Activation context or empty dict if not active
        """
        return self._activation_context if self._safe_mode_active else {}


class SafeModeDetector:
    """
    Detector for conditions that should trigger safe mode.
    
    Monitors system health and detects anomalies.
    """
    
    def __init__(self, safe_mode_manager: SafeModeManager):
        """
        Initialize safe mode detector.
        
        Args:
            safe_mode_manager: Safe mode manager instance
        """
        self.safe_mode_manager = safe_mode_manager
        self.error_counts = {}
        self.action_counts = {}
        
        logger.info("Safe mode detector initialized")
    
    def check_critical_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Check if a critical error should trigger safe mode.
        
        Args:
            error_type: Type of error
            error_message: Error message
            context: Additional context
            
        Returns:
            bool: True if safe mode was activated
        """
        critical_error_types = [
            "database_connection_loss",
            "kafka_broker_unavailable",
            "claude_api_quota_exceeded",
            "multiple_service_failures",
        ]
        
        if error_type in critical_error_types:
            reason_map = {
                "database_connection_loss": SafeModeReason.DATABASE_FAILURE,
                "kafka_broker_unavailable": SafeModeReason.KAFKA_FAILURE,
                "claude_api_quota_exceeded": SafeModeReason.CLAUDE_API_FAILURE,
                "multiple_service_failures": SafeModeReason.CRITICAL_ERROR,
            }
            
            reason = reason_map.get(error_type, SafeModeReason.CRITICAL_ERROR)
            
            activation_context = {
                "error_type": error_type,
                "error_message": error_message,
                **(context or {}),
            }
            
            self.safe_mode_manager.activate(reason, activation_context)
            
            logger.critical(
                "Critical error triggered safe mode",
                error_type=error_type,
                error_message=error_message,
            )
            
            return True
        
        return False
    
    def check_confidence_drift(
        self,
        expected_accuracy: float,
        actual_accuracy: float,
        threshold: float = 0.05,
    ) -> bool:
        """
        Check if confidence calibration drift should trigger safe mode.
        
        Args:
            expected_accuracy: Expected accuracy based on confidence
            actual_accuracy: Actual measured accuracy
            threshold: Maximum acceptable drift (default 5%)
            
        Returns:
            bool: True if safe mode was activated
        """
        drift = abs(expected_accuracy - actual_accuracy)
        
        if drift > threshold:
            context = {
                "expected_accuracy": expected_accuracy,
                "actual_accuracy": actual_accuracy,
                "drift": drift,
                "threshold": threshold,
            }
            
            self.safe_mode_manager.activate(
                SafeModeReason.CONFIDENCE_DRIFT,
                context,
            )
            
            logger.critical(
                "Confidence drift triggered safe mode",
                drift=drift,
                threshold=threshold,
            )
            
            return True
        
        return False
    
    def check_excessive_actions(
        self,
        action_type: str,
        merchant_id: str,
        count: int,
        time_window_minutes: int = 5,
        threshold: int = 20,
    ) -> bool:
        """
        Check if excessive actions should trigger safe mode.
        
        Args:
            action_type: Type of action
            merchant_id: Merchant ID
            count: Number of actions in time window
            time_window_minutes: Time window in minutes
            threshold: Maximum acceptable actions
            
        Returns:
            bool: True if safe mode was activated
        """
        if count > threshold:
            context = {
                "action_type": action_type,
                "merchant_id": merchant_id,
                "count": count,
                "time_window_minutes": time_window_minutes,
                "threshold": threshold,
            }
            
            self.safe_mode_manager.activate(
                SafeModeReason.EXCESSIVE_ACTIONS,
                context,
            )
            
            logger.critical(
                "Excessive actions triggered safe mode",
                action_type=action_type,
                merchant_id=merchant_id,
                count=count,
            )
            
            return True
        
        return False
    
    def check_anomalous_behavior(
        self,
        behavior_type: str,
        description: str,
        context: Optional[dict] = None,
    ) -> bool:
        """
        Check if anomalous behavior should trigger safe mode.
        
        Args:
            behavior_type: Type of anomalous behavior
            description: Description of the behavior
            context: Additional context
            
        Returns:
            bool: True if safe mode was activated
        """
        activation_context = {
            "behavior_type": behavior_type,
            "description": description,
            **(context or {}),
        }
        
        self.safe_mode_manager.activate(
            SafeModeReason.ANOMALOUS_BEHAVIOR,
            activation_context,
        )
        
        logger.critical(
            "Anomalous behavior triggered safe mode",
            behavior_type=behavior_type,
            description=description,
        )
        
        return True


# Singleton instance
_safe_mode_manager: Optional[SafeModeManager] = None
_safe_mode_detector: Optional[SafeModeDetector] = None


def get_safe_mode_manager() -> SafeModeManager:
    """
    Get or create the safe mode manager singleton.
    
    Returns:
        SafeModeManager instance
    """
    global _safe_mode_manager
    
    if _safe_mode_manager is None:
        _safe_mode_manager = SafeModeManager()
    
    return _safe_mode_manager


def get_safe_mode_detector() -> SafeModeDetector:
    """
    Get or create the safe mode detector singleton.
    
    Returns:
        SafeModeDetector instance
    """
    global _safe_mode_detector
    
    if _safe_mode_detector is None:
        manager = get_safe_mode_manager()
        _safe_mode_detector = SafeModeDetector(manager)
    
    return _safe_mode_detector
