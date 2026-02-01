"""
Unit tests for circuit breaker pattern implementation.

Tests verify that circuit breaker:
- Opens after failure threshold is reached
- Closes after recovery timeout
- Transitions through states correctly
- Logs state changes appropriately
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from migrationguard_ai.core.circuit_breaker import (
    AsyncCircuitBreaker,
    circuit_breaker,
    CircuitBreakerConfig,
)


class TestAsyncCircuitBreaker:
    """Test AsyncCircuitBreaker class."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_starts_closed(self):
        """Test that circuit breaker starts in CLOSED state."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_call_in_closed_state(self):
        """Test that successful calls work in CLOSED state."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        async def successful_func():
            return "success"
        
        result = await breaker.call(successful_func)
        
        assert result == "success"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test that circuit opens after failure threshold is reached."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=3,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Fail 3 times to reach threshold
        for i in range(3):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_rejects_calls_when_open(self):
        """Test that circuit rejects calls when OPEN."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == "OPEN"
        
        # Try to call again - should be rejected immediately
        async def any_func():
            return "should not execute"
        
        with pytest.raises(Exception, match="Circuit breaker .* is OPEN"):
            await breaker.call(any_func)
    
    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self):
        """Test that circuit transitions to HALF_OPEN after recovery timeout."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,  # 1 second for faster test
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == "OPEN"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Next call should transition to HALF_OPEN
        async def successful_func():
            return "success"
        
        result = await breaker.call(successful_func)
        
        assert result == "success"
        assert breaker.state == "CLOSED"  # Should close after successful call
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_successful_half_open_call(self):
        """Test that circuit closes after successful call in HALF_OPEN state."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        async def successful_func():
            return "success"
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Successful call should close the circuit
        result = await breaker.call(successful_func)
        
        assert result == "success"
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_reopens_on_half_open_failure(self):
        """Test that circuit reopens if call fails in HALF_OPEN state."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        # Wait for recovery timeout
        await asyncio.sleep(1.1)
        
        # Failing call in HALF_OPEN should reopen circuit
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_specific_exception(self):
        """Test that circuit breaker only catches specified exception type."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10,
            expected_exception=ValueError,
            name="test_breaker"
        )
        
        async def value_error_func():
            raise ValueError("Test value error")
        
        async def type_error_func():
            raise TypeError("Test type error")
        
        # ValueError should be caught
        with pytest.raises(ValueError):
            await breaker.call(value_error_func)
        
        assert breaker.failure_count == 1
        
        # TypeError should not be caught (will propagate)
        with pytest.raises(TypeError):
            await breaker.call(type_error_func)
        
        # Failure count should not increase for TypeError
        assert breaker.failure_count == 1


class TestCircuitBreakerDecorator:
    """Test circuit_breaker decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_applies_circuit_breaker(self):
        """Test that decorator applies circuit breaker to function."""
        
        @circuit_breaker(
            failure_threshold=2,
            recovery_timeout=10,
            name="decorated_func"
        )
        async def test_func(should_fail: bool = False):
            if should_fail:
                raise Exception("Test failure")
            return "success"
        
        # Successful call
        result = await test_func(should_fail=False)
        assert result == "success"
        
        # Fail twice to open circuit
        with pytest.raises(Exception):
            await test_func(should_fail=True)
        
        with pytest.raises(Exception):
            await test_func(should_fail=True)
        
        # Circuit should be open now
        with pytest.raises(Exception, match="Circuit breaker .* is OPEN"):
            await test_func(should_fail=False)
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        
        @circuit_breaker(name="test")
        async def my_function():
            """My function docstring."""
            return "result"
        
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My function docstring."


class TestPreconfiguredCircuitBreakers:
    """Test pre-configured circuit breakers."""
    
    def test_claude_api_circuit_breaker_config(self):
        """Test Claude API circuit breaker configuration."""
        assert CircuitBreakerConfig.CLAUDE_API_FAILURE_THRESHOLD == 5
        assert CircuitBreakerConfig.CLAUDE_API_RECOVERY_TIMEOUT == 60
    
    def test_support_system_circuit_breaker_config(self):
        """Test support system circuit breaker configuration."""
        assert CircuitBreakerConfig.SUPPORT_SYSTEM_FAILURE_THRESHOLD == 3
        assert CircuitBreakerConfig.SUPPORT_SYSTEM_RECOVERY_TIMEOUT == 30
    
    def test_elasticsearch_circuit_breaker_config(self):
        """Test Elasticsearch circuit breaker configuration."""
        assert CircuitBreakerConfig.ELASTICSEARCH_FAILURE_THRESHOLD == 5
        assert CircuitBreakerConfig.ELASTICSEARCH_RECOVERY_TIMEOUT == 45
    
    def test_kafka_circuit_breaker_config(self):
        """Test Kafka circuit breaker configuration."""
        assert CircuitBreakerConfig.KAFKA_FAILURE_THRESHOLD == 5
        assert CircuitBreakerConfig.KAFKA_RECOVERY_TIMEOUT == 30


class TestCircuitBreakerLogging:
    """Test circuit breaker logging."""
    
    @pytest.mark.asyncio
    async def test_logs_state_transitions(self):
        """Test that circuit breaker logs state transitions."""
        with patch('migrationguard_ai.core.circuit_breaker.logger') as mock_logger:
            breaker = AsyncCircuitBreaker(
                failure_threshold=2,
                recovery_timeout=1,
                name="test_breaker"
            )
            
            async def failing_func():
                raise Exception("Test failure")
            
            # Open the circuit
            for i in range(2):
                with pytest.raises(Exception):
                    await breaker.call(failing_func)
            
            # Check that error was logged
            assert mock_logger.error.called
            
            # Check that circuit opened was logged
            mock_logger.error.assert_any_call(
                "circuit_breaker_opened",
                name="test_breaker",
                failure_count=2
            )
    
    @pytest.mark.asyncio
    async def test_logs_initialization(self):
        """Test that circuit breaker logs initialization."""
        with patch('migrationguard_ai.core.circuit_breaker.logger') as mock_logger:
            breaker = AsyncCircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                name="test_breaker"
            )
            
            # Check that initialization was logged
            mock_logger.info.assert_called_once_with(
                "circuit_breaker_initialized",
                name="test_breaker",
                failure_threshold=5,
                recovery_timeout=60
            )


class TestCircuitBreakerEdgeCases:
    """Test circuit breaker edge cases."""
    
    @pytest.mark.asyncio
    async def test_zero_failure_threshold(self):
        """Test circuit breaker with zero failure threshold."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=0,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        async def failing_func():
            raise Exception("Test failure")
        
        # Should open immediately on first failure
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.state == "OPEN"
    
    @pytest.mark.asyncio
    async def test_concurrent_calls(self):
        """Test circuit breaker with concurrent calls."""
        breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            recovery_timeout=10,
            name="test_breaker"
        )
        
        call_count = 0
        
        async def counting_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return call_count
        
        # Make concurrent calls
        results = await asyncio.gather(
            breaker.call(counting_func),
            breaker.call(counting_func),
            breaker.call(counting_func),
        )
        
        assert len(results) == 3
        assert breaker.state == "CLOSED"
        assert call_count == 3
