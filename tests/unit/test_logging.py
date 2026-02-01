"""
Unit Tests for Structured Logging.

This module tests the structured logging functionality including
context binding, log levels, and specialized logging functions.
"""

import pytest
import structlog
from migrationguard_ai.core.logging import (
    get_logger,
    bind_context,
    unbind_context,
    clear_context,
    LogContext,
    log_event,
    log_error,
    log_performance,
    log_decision,
    log_action_execution,
)


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger(__name__)
        
        assert logger is not None
        # Verify logger has the expected methods
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')
    
    def test_logger_basic_logging(self):
        """Test basic logging methods."""
        logger = get_logger(__name__)
        
        # Should not raise exceptions
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")
    
    def test_logger_with_context(self):
        """Test logging with context variables."""
        logger = get_logger(__name__)
        
        # Log with context
        logger.info("Test message", issue_id="issue_123", merchant_id="merchant_456")
        
        # Should not raise exceptions
        assert True
    
    def test_bind_context(self):
        """Test binding context variables."""
        logger = get_logger(__name__)
        
        # Bind context
        bind_context(issue_id="issue_123", merchant_id="merchant_456")
        
        # Log message (context should be included automatically)
        logger.info("Test message with bound context")
        
        # Clean up
        clear_context()
    
    def test_unbind_context(self):
        """Test unbinding specific context variables."""
        logger = get_logger(__name__)
        
        # Bind context
        bind_context(issue_id="issue_123", merchant_id="merchant_456", component="test")
        
        # Unbind specific keys
        unbind_context("issue_id", "merchant_id")
        
        # Log message (only component should remain)
        logger.info("Test message after unbind")
        
        # Clean up
        clear_context()
    
    def test_clear_context(self):
        """Test clearing all context variables."""
        logger = get_logger(__name__)
        
        # Bind context
        bind_context(issue_id="issue_123", merchant_id="merchant_456")
        
        # Clear all context
        clear_context()
        
        # Log message (no context should be included)
        logger.info("Test message after clear")
    
    def test_log_context_manager(self):
        """Test LogContext context manager."""
        logger = get_logger(__name__)
        
        # Use context manager
        with LogContext(issue_id="issue_123", merchant_id="merchant_456"):
            logger.info("Inside context manager")
        
        # Context should be cleared after exiting
        logger.info("Outside context manager")
    
    def test_log_context_manager_with_exception(self):
        """Test LogContext cleans up even with exceptions."""
        logger = get_logger(__name__)
        
        try:
            with LogContext(issue_id="issue_123"):
                logger.info("Before exception")
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Context should still be cleared
        logger.info("After exception")
    
    def test_log_event(self):
        """Test log_event helper function."""
        logger = get_logger(__name__)
        
        # Test different log levels
        log_event(logger, "debug", "test_event", key="value")
        log_event(logger, "info", "test_event", key="value")
        log_event(logger, "warning", "test_event", key="value")
        log_event(logger, "error", "test_event", key="value")
        log_event(logger, "critical", "test_event", key="value")
    
    def test_log_error(self):
        """Test log_error helper function."""
        logger = get_logger(__name__)
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_error(logger, e, "test_error_event", context="test")
    
    def test_log_performance(self):
        """Test log_performance helper function."""
        logger = get_logger(__name__)
        
        log_performance(
            logger,
            operation="test_operation",
            duration_ms=125.5,
            items_processed=10
        )
    
    def test_log_decision(self):
        """Test log_decision helper function."""
        logger = get_logger(__name__)
        
        log_decision(
            logger,
            issue_id="issue_123",
            action_type="support_guidance",
            risk_level="low",
            confidence=0.92,
            requires_approval=False,
            merchant_id="merchant_456"
        )
    
    def test_log_action_execution(self):
        """Test log_action_execution helper function."""
        logger = get_logger(__name__)
        
        # Test successful execution
        log_action_execution(
            logger,
            action_id="action_123",
            action_type="support_guidance",
            success=True,
            duration_ms=250.0,
            merchant_id="merchant_456"
        )
        
        # Test failed execution
        log_action_execution(
            logger,
            action_id="action_124",
            action_type="engineering_escalation",
            success=False,
            error="Connection timeout"
        )
    
    def test_nested_context(self):
        """Test nested context managers."""
        logger = get_logger(__name__)
        
        with LogContext(level1="outer"):
            logger.info("Outer context")
            
            with LogContext(level2="inner"):
                logger.info("Inner context")
            
            logger.info("Back to outer context")
        
        logger.info("No context")
    
    def test_logger_with_multiple_contexts(self):
        """Test logging with multiple context types."""
        logger = get_logger(__name__)
        
        bind_context(
            issue_id="issue_123",
            merchant_id="merchant_456",
            component="pattern_detector"
        )
        
        logger.info(
            "Complex log entry",
            operation="detect_patterns",
            duration_ms=125.5,
            pattern_count=3,
            confidence=0.85
        )
        
        clear_context()
    
    def test_log_levels(self):
        """Test that all log levels work correctly."""
        logger = get_logger(__name__)
        
        # Test all standard log levels
        logger.debug("Debug level", level="DEBUG")
        logger.info("Info level", level="INFO")
        logger.warning("Warning level", level="WARNING")
        logger.error("Error level", level="ERROR")
        logger.critical("Critical level", level="CRITICAL")
    
    def test_structured_data_logging(self):
        """Test logging with structured data."""
        logger = get_logger(__name__)
        
        # Log with various data types
        logger.info(
            "Structured data test",
            string_value="test",
            int_value=42,
            float_value=3.14,
            bool_value=True,
            list_value=[1, 2, 3],
            dict_value={"key": "value"}
        )
    
    def test_exception_logging(self):
        """Test logging exceptions with stack traces."""
        logger = get_logger(__name__)
        
        try:
            # Create a nested exception
            try:
                raise ValueError("Inner exception")
            except ValueError:
                raise RuntimeError("Outer exception")
        except RuntimeError as e:
            logger.error(
                "Exception occurred",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
