"""
Unit tests for graceful degradation functionality.

Tests verify that the system continues to operate with reduced functionality
when external services are unavailable.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from migrationguard_ai.core.graceful_degradation import (
    RuleBasedRootCauseAnalyzer,
    PostgreSQLPatternMatcher,
    RedisSignalBuffer,
    GracefulDegradationManager,
    get_degradation_manager,
)
from migrationguard_ai.core.schemas import Signal, Pattern


class TestRuleBasedRootCauseAnalyzer:
    """Test rule-based fallback for Claude API."""
    
    @pytest.mark.asyncio
    async def test_analyze_with_auth_errors(self):
        """Test that auth errors are classified as migration_misstep."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="api_failure",
                merchant_id="merchant1",
                severity="high",
                raw_data={},
                error_code="401",
                error_message="Unauthorized access"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        assert analysis.category == "migration_misstep"
        assert analysis.confidence == 0.75
        assert "authentication" in analysis.reasoning.lower()
        assert len(analysis.evidence) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_with_config_errors(self):
        """Test that config errors are classified correctly."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="api_failure",
                merchant_id="merchant1",
                severity="medium",
                raw_data={},
                error_message="Configuration variable WEBHOOK_URL is missing"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        assert analysis.category == "config_error"
        assert analysis.confidence == 0.70
        assert "configuration" in analysis.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_with_webhook_failures(self):
        """Test that webhook failures are classified as config_error."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="webhook_failure",
                merchant_id="merchant1",
                severity="high",
                raw_data={},
                error_message="Webhook delivery failed"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        assert analysis.category == "config_error"
        assert analysis.confidence == 0.65
        assert "webhook" in analysis.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_with_cross_merchant_pattern(self):
        """Test that cross-merchant patterns indicate platform_regression."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="api_failure",
                merchant_id="merchant1",
                severity="high",
                raw_data={},
                error_code="404"
            )
        ]
        
        patterns = [
            Pattern(
                pattern_id="pat1",
                pattern_type="api_failure",
                confidence=0.9,
                signal_ids=["sig1", "sig2", "sig3", "sig4"],
                merchant_ids=["merchant1", "merchant2", "merchant3", "merchant4"],
                first_seen=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                frequency=10,
                characteristics={}
            )
        ]
        
        analysis = await analyzer.analyze(signals, patterns, None)
        
        assert analysis.category == "platform_regression"
        assert analysis.confidence == 0.68  # Endpoint errors with cross-merchant pattern
        assert "many merchants" in analysis.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_with_checkout_errors(self):
        """Test that checkout errors are classified as migration_misstep."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="checkout_error",
                merchant_id="merchant1",
                severity="critical",
                raw_data={},
                error_message="Payment processing failed"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        assert analysis.category == "migration_misstep"
        assert analysis.confidence == 0.60
        assert "checkout" in analysis.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_with_no_specific_pattern(self):
        """Test default classification when no specific pattern matches."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="api_failure",
                merchant_id="merchant1",
                severity="low",
                raw_data={},
                error_message="Unknown error"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        assert analysis.category == "migration_misstep"
        assert analysis.confidence == 0.50
        assert "unable to determine" in analysis.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_analyze_without_signals_raises_error(self):
        """Test that analyzing without signals raises ValueError."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        with pytest.raises(ValueError, match="At least one signal is required"):
            await analyzer.analyze([], [], None)
    
    @pytest.mark.asyncio
    async def test_recommended_actions_for_each_category(self):
        """Test that each category has recommended actions."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        categories = [
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ]
        
        for category in categories:
            actions = analyzer._get_recommended_actions(category)
            assert len(actions) > 0
            assert all(isinstance(action, str) for action in actions)


class TestPostgreSQLPatternMatcher:
    """Test PostgreSQL fallback for Elasticsearch."""
    
    @pytest.mark.asyncio
    async def test_match_pattern_returns_none(self):
        """Test that fallback pattern matcher returns None."""
        mock_session = MagicMock()
        matcher = PostgreSQLPatternMatcher(mock_session)
        
        signal = Signal(
            signal_id="sig1",
            timestamp=datetime.now(timezone.utc),
            source="api_failure",
            merchant_id="merchant1",
            severity="medium",
            raw_data={}
        )
        
        result = await matcher.match_pattern(signal)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_patterns_returns_empty_list(self):
        """Test that fallback pattern search returns empty list."""
        mock_session = MagicMock()
        matcher = PostgreSQLPatternMatcher(mock_session)
        
        results = await matcher.search_patterns({"query": "test"})
        
        assert results == []


class TestRedisSignalBuffer:
    """Test Redis fallback for Kafka."""
    
    @pytest.mark.asyncio
    async def test_buffer_signal_success(self):
        """Test buffering signal in Redis."""
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock(return_value=True)
        
        buffer = RedisSignalBuffer(mock_redis)
        
        signal = Signal(
            signal_id="sig1",
            timestamp=datetime.now(timezone.utc),
            source="api_failure",
            merchant_id="merchant1",
            severity="medium",
            raw_data={}
        )
        
        result = await buffer.buffer_signal(signal)
        
        assert result is True
        mock_redis.lpush.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_buffer_signal_failure(self):
        """Test handling of buffer failure."""
        mock_redis = AsyncMock()
        mock_redis.lpush = AsyncMock(side_effect=Exception("Redis error"))
        
        buffer = RedisSignalBuffer(mock_redis)
        
        signal = Signal(
            signal_id="sig1",
            timestamp=datetime.now(timezone.utc),
            source="api_failure",
            merchant_id="merchant1",
            severity="medium",
            raw_data={}
        )
        
        result = await buffer.buffer_signal(signal)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_buffer_size(self):
        """Test getting buffer size."""
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(return_value=5)
        
        buffer = RedisSignalBuffer(mock_redis)
        
        size = await buffer.get_buffer_size()
        
        assert size == 5
    
    @pytest.mark.asyncio
    async def test_get_buffer_size_on_error(self):
        """Test getting buffer size when Redis fails."""
        mock_redis = AsyncMock()
        mock_redis.llen = AsyncMock(side_effect=Exception("Redis error"))
        
        buffer = RedisSignalBuffer(mock_redis)
        
        size = await buffer.get_buffer_size()
        
        assert size == 0


class TestGracefulDegradationManager:
    """Test graceful degradation manager."""
    
    def test_initialization(self):
        """Test manager initialization."""
        manager = GracefulDegradationManager()
        
        assert manager.degradation_state["claude_api"] is False
        assert manager.degradation_state["elasticsearch"] is False
        assert manager.degradation_state["kafka"] is False
    
    def test_set_degraded(self):
        """Test setting degradation state."""
        manager = GracefulDegradationManager()
        
        manager.set_degraded("claude_api", True)
        
        assert manager.is_degraded("claude_api") is True
        assert manager.is_degraded("elasticsearch") is False
    
    def test_set_degraded_logs_state_change(self):
        """Test that state changes are logged."""
        with patch('migrationguard_ai.core.graceful_degradation.logger') as mock_logger:
            manager = GracefulDegradationManager()
            
            manager.set_degraded("claude_api", True)
            
            # Should log warning when entering degraded mode
            assert mock_logger.warning.called
    
    def test_is_any_degraded(self):
        """Test checking if any service is degraded."""
        manager = GracefulDegradationManager()
        
        assert manager.is_any_degraded() is False
        
        manager.set_degraded("kafka", True)
        
        assert manager.is_any_degraded() is True
    
    def test_get_degradation_status(self):
        """Test getting degradation status for all services."""
        manager = GracefulDegradationManager()
        
        manager.set_degraded("claude_api", True)
        manager.set_degraded("elasticsearch", True)
        
        status = manager.get_degradation_status()
        
        assert status["claude_api"] is True
        assert status["elasticsearch"] is True
        assert status["kafka"] is False
    
    def test_get_degradation_manager_singleton(self):
        """Test that get_degradation_manager returns singleton."""
        manager1 = get_degradation_manager()
        manager2 = get_degradation_manager()
        
        assert manager1 is manager2


class TestGracefulDegradationIntegration:
    """Test integration of graceful degradation with services."""
    
    @pytest.mark.asyncio
    async def test_rule_based_analyzer_provides_valid_analysis(self):
        """Test that rule-based analyzer provides valid analysis structure."""
        analyzer = RuleBasedRootCauseAnalyzer()
        
        signals = [
            Signal(
                signal_id="sig1",
                timestamp=datetime.now(timezone.utc),
                source="api_failure",
                merchant_id="merchant1",
                severity="high",
                raw_data={},
                error_code="401"
            )
        ]
        
        analysis = await analyzer.analyze(signals, [], None)
        
        # Verify all required fields are present
        assert analysis.category in [
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ]
        assert 0.0 <= analysis.confidence <= 1.0
        assert len(analysis.reasoning) > 0
        assert len(analysis.evidence) > 0
        assert len(analysis.alternatives_considered) > 0
        assert len(analysis.recommended_actions) > 0
    
    @pytest.mark.asyncio
    async def test_degradation_manager_tracks_multiple_services(self):
        """Test that manager can track multiple degraded services."""
        manager = GracefulDegradationManager()
        
        # Degrade all services
        manager.set_degraded("claude_api", True)
        manager.set_degraded("elasticsearch", True)
        manager.set_degraded("kafka", True)
        
        # All should be degraded
        assert manager.is_degraded("claude_api")
        assert manager.is_degraded("elasticsearch")
        assert manager.is_degraded("kafka")
        assert manager.is_any_degraded()
        
        # Recover one service
        manager.set_degraded("claude_api", False)
        
        # Should still have degraded services
        assert not manager.is_degraded("claude_api")
        assert manager.is_any_degraded()
