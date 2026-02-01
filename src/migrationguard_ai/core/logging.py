"""Structured logging configuration using structlog."""

import logging
import sys
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor

from migrationguard_ai.core.config import get_settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries."""
    settings = get_settings()
    event_dict["app"] = settings.APP_NAME
    event_dict["version"] = settings.APP_VERSION
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def add_request_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request context if available."""
    # This will be populated by middleware
    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application."""
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Determine processors based on environment
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_app_context,
        add_request_context,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.ENVIRONMENT == "development":
        # Pretty console output for development
        processors.extend([
            structlog.dev.ConsoleRenderer(),
        ])
    else:
        # JSON output for production
        processors.extend([
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def bind_context(**kwargs) -> None:
    """
    Bind context variables to the current logger context.
    
    This adds context that will be included in all subsequent log entries
    within the current execution context.
    
    Args:
        **kwargs: Context key-value pairs to bind
        
    Example:
        bind_context(issue_id="issue_123", merchant_id="merchant_456")
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """
    Unbind context variables from the current logger context.
    
    Args:
        *keys: Context keys to unbind
        
    Example:
        unbind_context("issue_id", "merchant_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all context variables from the current logger context."""
    structlog.contextvars.clear_contextvars()


class LogContext:
    """
    Context manager for temporary log context binding.
    
    Example:
        with LogContext(issue_id="issue_123", merchant_id="merchant_456"):
            logger.info("Processing issue")
    """
    
    def __init__(self, **kwargs):
        """Initialize context manager with context variables."""
        self.context = kwargs
    
    def __enter__(self):
        """Bind context variables on enter."""
        bind_context(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Unbind context variables on exit."""
        unbind_context(*self.context.keys())


def log_event(
    logger: structlog.stdlib.BoundLogger,
    level: str,
    event: str,
    **kwargs
) -> None:
    """
    Log an event with structured context.
    
    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        event: Event description
        **kwargs: Additional context
        
    Example:
        log_event(logger, "info", "signal_ingested", 
                  signal_id="sig_123", source="zendesk")
    """
    log_method = getattr(logger, level.lower())
    log_method(event, **kwargs)


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    event: str,
    **kwargs
) -> None:
    """
    Log an error with full context and stack trace.
    
    Args:
        logger: Logger instance
        error: Exception instance
        event: Event description
        **kwargs: Additional context
        
    Example:
        try:
            # some code
        except Exception as e:
            log_error(logger, e, "failed_to_process_signal", 
                     signal_id="sig_123")
    """
    logger.error(
        event,
        error=str(error),
        error_type=type(error).__name__,
        exc_info=True,
        **kwargs
    )


def log_performance(
    logger: structlog.stdlib.BoundLogger,
    operation: str,
    duration_ms: float,
    **kwargs
) -> None:
    """
    Log performance metrics for an operation.
    
    Args:
        logger: Logger instance
        operation: Operation name
        duration_ms: Duration in milliseconds
        **kwargs: Additional context
        
    Example:
        log_performance(logger, "pattern_detection", 
                       duration_ms=125.5, pattern_count=3)
    """
    logger.info(
        "performance_metric",
        operation=operation,
        duration_ms=duration_ms,
        **kwargs
    )


def log_decision(
    logger: structlog.stdlib.BoundLogger,
    issue_id: str,
    action_type: str,
    risk_level: str,
    confidence: float,
    requires_approval: bool,
    **kwargs
) -> None:
    """
    Log a decision made by the system.
    
    Args:
        logger: Logger instance
        issue_id: Issue identifier
        action_type: Type of action decided
        risk_level: Risk level assessment
        confidence: Confidence score
        requires_approval: Whether approval is required
        **kwargs: Additional context
        
    Example:
        log_decision(logger, "issue_123", "support_guidance", 
                    "low", 0.92, False)
    """
    logger.info(
        "decision_made",
        issue_id=issue_id,
        action_type=action_type,
        risk_level=risk_level,
        confidence=confidence,
        requires_approval=requires_approval,
        **kwargs
    )


def log_action_execution(
    logger: structlog.stdlib.BoundLogger,
    action_id: str,
    action_type: str,
    success: bool,
    duration_ms: Optional[float] = None,
    **kwargs
) -> None:
    """
    Log action execution result.
    
    Args:
        logger: Logger instance
        action_id: Action identifier
        action_type: Type of action
        success: Whether execution succeeded
        duration_ms: Execution duration in milliseconds
        **kwargs: Additional context
        
    Example:
        log_action_execution(logger, "act_123", "support_guidance", 
                           True, duration_ms=250.0)
    """
    logger.info(
        "action_executed",
        action_id=action_id,
        action_type=action_type,
        success=success,
        duration_ms=duration_ms,
        **kwargs
    )

