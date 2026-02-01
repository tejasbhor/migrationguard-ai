"""
Circuit Breaker Pattern Implementation.

This module provides circuit breaker functionality for external service calls
to prevent cascading failures and enable graceful degradation.
"""

from typing import Callable, Any, Optional
from functools import wraps
import asyncio
from circuitbreaker import circuit as sync_circuit
from datetime import datetime, timedelta

from migrationguard_ai.core.logging import get_logger


logger = get_logger(__name__)


class CircuitBreakerConfig:
    """Configuration for circuit breakers."""
    
    # Claude API circuit breaker
    CLAUDE_API_FAILURE_THRESHOLD = 5
    CLAUDE_API_RECOVERY_TIMEOUT = 60  # seconds
    CLAUDE_API_EXPECTED_EXCEPTION = Exception
    
    # Support systems circuit breaker
    SUPPORT_SYSTEM_FAILURE_THRESHOLD = 3
    SUPPORT_SYSTEM_RECOVERY_TIMEOUT = 30  # seconds
    SUPPORT_SYSTEM_EXPECTED_EXCEPTION = Exception
    
    # Elasticsearch circuit breaker
    ELASTICSEARCH_FAILURE_THRESHOLD = 5
    ELASTICSEARCH_RECOVERY_TIMEOUT = 45  # seconds
    ELASTICSEARCH_EXPECTED_EXCEPTION = Exception
    
    # Kafka circuit breaker
    KAFKA_FAILURE_THRESHOLD = 5
    KAFKA_RECOVERY_TIMEOUT = 30  # seconds
    KAFKA_EXPECTED_EXCEPTION = Exception


class AsyncCircuitBreaker:
    """
    Async circuit breaker implementation.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            name: Name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
        logger.info(
            f"circuit_breaker_initialized",
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        
        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure.total_seconds() >= self.recovery_timeout
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        # Check if circuit is open
        if self.state == "OPEN":
            if self._should_attempt_reset():
                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    failure_count=self.failure_count
                )
                self.state = "HALF_OPEN"
            else:
                logger.warning(
                    "circuit_breaker_open",
                    name=self.name,
                    failure_count=self.failure_count
                )
                raise Exception(f"Circuit breaker {self.name} is OPEN")
        
        try:
            # Call the function
            result = await func(*args, **kwargs)
            
            # Success - reset if in HALF_OPEN state
            if self.state == "HALF_OPEN":
                logger.info(
                    "circuit_breaker_closed",
                    name=self.name,
                    previous_failures=self.failure_count
                )
                self.failure_count = 0
                self.state = "CLOSED"
            
            return result
            
        except self.expected_exception as e:
            # Failure - increment counter
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            logger.error(
                "circuit_breaker_failure",
                name=self.name,
                failure_count=self.failure_count,
                error=str(e)
            )
            
            # Open circuit if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(
                    "circuit_breaker_opened",
                    name=self.name,
                    failure_count=self.failure_count
                )
            
            raise


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    name: str = "circuit_breaker"
):
    """
    Decorator for applying circuit breaker to async functions.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        expected_exception: Exception type to catch
        name: Name for logging
        
    Example:
        @circuit_breaker(
            failure_threshold=5,
            recovery_timeout=60,
            name="claude_api"
        )
        async def call_claude_api():
            ...
    """
    breaker = AsyncCircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        name=name
    )
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
claude_api_circuit_breaker = circuit_breaker(
    failure_threshold=CircuitBreakerConfig.CLAUDE_API_FAILURE_THRESHOLD,
    recovery_timeout=CircuitBreakerConfig.CLAUDE_API_RECOVERY_TIMEOUT,
    expected_exception=CircuitBreakerConfig.CLAUDE_API_EXPECTED_EXCEPTION,
    name="claude_api"
)

support_system_circuit_breaker = circuit_breaker(
    failure_threshold=CircuitBreakerConfig.SUPPORT_SYSTEM_FAILURE_THRESHOLD,
    recovery_timeout=CircuitBreakerConfig.SUPPORT_SYSTEM_RECOVERY_TIMEOUT,
    expected_exception=CircuitBreakerConfig.SUPPORT_SYSTEM_EXPECTED_EXCEPTION,
    name="support_system"
)

elasticsearch_circuit_breaker = circuit_breaker(
    failure_threshold=CircuitBreakerConfig.ELASTICSEARCH_FAILURE_THRESHOLD,
    recovery_timeout=CircuitBreakerConfig.ELASTICSEARCH_RECOVERY_TIMEOUT,
    expected_exception=CircuitBreakerConfig.ELASTICSEARCH_EXPECTED_EXCEPTION,
    name="elasticsearch"
)

kafka_circuit_breaker = circuit_breaker(
    failure_threshold=CircuitBreakerConfig.KAFKA_FAILURE_THRESHOLD,
    recovery_timeout=CircuitBreakerConfig.KAFKA_RECOVERY_TIMEOUT,
    expected_exception=CircuitBreakerConfig.KAFKA_EXPECTED_EXCEPTION,
    name="kafka"
)
