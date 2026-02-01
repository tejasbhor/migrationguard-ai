"""
Unit tests for pattern detection system.

Tests cover:
- Pattern detector initialization
- Signal grouping methods (by type, by error code)
- Pattern creation methods (cross-merchant, frequency, cluster)
- Pattern matching and updates
- Edge cases and error handling
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from migrationguard_ai.core.schemas import Signal, Pattern
from migrationguard_ai.services.pattern_detector import PatternDetector


@pytest.fixture
def mock_es_client():
    """Create a mock Elasticsearch client."""
    client = AsyncMock()
    client.index_document = AsyncMock()
    client.search = AsyncMock(return_value={"hits": {"hits": []}})
    client.get_document = AsyncMock()
    client.update_document = AsyncMock()
    return client


@pytest.fixture
def pattern_detector(mock_es_client):
    """Create a pattern detector with mocked ES client."""
    return PatternDetector(mock_es_client)


@pytest.fixture
def sample_signals():
    """Create sample signals for testing."""
    base_time = datetime.utcnow()
    return [
        Signal(
            signal_id=f"signal_{i}",
            timestamp=base_time + timedelta(minutes=i),
            source="api_failure",
            merchant_id=f"merchant_{i % 3}",
            severity="high",
            error_message=f"API error {i}",
            error_code="API_ERROR_500",
            raw_data={},
            context={},
        )
        for i in range(5)
    ]


class TestPatternDetectorInitialization:
    """Test pattern detector initialization and configuration."""
    
    def test_initialization(self, mock_es_client):
        """Test that pattern detector initializes with correct defaults."""
        detector = PatternDetector(mock_es_client)
        
        assert detector.es_client == mock_es_client
        assert detector.window_size_minutes == 2
        assert detector.similarity_threshold == 0.7
        assert detector.min_pattern_frequency == 3
    
    def test_custom_configuration(self, mock_es_client):
        """Test that configuration can be customized."""
        detector = PatternDetector(mock_es_client)
        detector.window_size_minutes = 5
        detector.similarity_threshold = 0.8
        detector.min_pattern_frequency = 5
        
        assert detector.window_size_minutes == 5
        assert detector.similarity_threshold == 0.8
        assert detector.min_pattern_frequency == 5


class TestSignalGrouping:
    """Test signal grouping methods."""
    
    def test_group_signals_by_type(self, pattern_detector):
        """Test grouping signals by source type."""
        signals = [
            Signal(
                source="api_failure",
                merchant_id="m1",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="api_failure",
                merchant_id="m2",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="checkout_error",
                merchant_id="m1",
                severity="critical",
                error_code="E2",
                raw_data={},
                context={},
            ),
        ]
        
        grouped = pattern_detector._group_signals_by_type(signals)
        
        assert len(grouped) == 2
        assert len(grouped["api_failure"]) == 2
        assert len(grouped["checkout_error"]) == 1
    
    def test_group_by_error_code(self, pattern_detector):
        """Test grouping signals by error code."""
        signals = [
            Signal(
                source="api_failure",
                merchant_id="m1",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="api_failure",
                merchant_id="m2",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="api_failure",
                merchant_id="m3",
                severity="high",
                error_code="E2",
                raw_data={},
                context={},
            ),
        ]
        
        grouped = pattern_detector._group_by_error_code(signals)
        
        assert len(grouped) == 2
        assert len(grouped["E1"]) == 2
        assert len(grouped["E2"]) == 1
    
    def test_group_by_error_code_ignores_none(self, pattern_detector):
        """Test that signals without error codes are ignored."""
        signals = [
            Signal(
                source="api_failure",
                merchant_id="m1",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="api_failure",
                merchant_id="m2",
                severity="high",
                error_code=None,
                raw_data={},
                context={},
            ),
        ]
        
        grouped = pattern_detector._group_by_error_code(signals)
        
        assert len(grouped) == 1
        assert "E1" in grouped
        assert None not in grouped


class TestPatternCreation:
    """Test pattern creation methods."""
    
    @pytest.mark.asyncio
    async def test_create_cross_merchant_pattern(self, pattern_detector, mock_es_client):
        """Test creating a cross-merchant pattern."""
        signals = [
            Signal(
                signal_id=f"s{i}",
                source="api_failure",
                merchant_id=f"merchant_{i}",
                severity="high",
                error_code="API_500",
                raw_data={},
                context={},
            )
            for i in range(3)
        ]
        
        pattern = await pattern_detector._create_cross_merchant_pattern(
            signal_type="api_failure",
            error_code="API_500",
            signals=signals,
            merchant_ids=["merchant_0", "merchant_1", "merchant_2"],
        )
        
        assert pattern is not None
        assert pattern.pattern_type == "api_failure"
        assert pattern.frequency == 3
        assert len(pattern.merchant_ids) == 3
        assert pattern.characteristics["cross_merchant"] is True
        assert pattern.characteristics["error_code"] == "API_500"
        assert 0.0 <= pattern.confidence <= 0.95
        
        # Verify ES indexing was called
        mock_es_client.index_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_frequency_pattern(self, pattern_detector, mock_es_client):
        """Test creating a frequency-based pattern."""
        base_time = datetime.utcnow()
        signals = [
            Signal(
                signal_id=f"s{i}",
                timestamp=base_time + timedelta(minutes=i),
                source="checkout_error",
                merchant_id="merchant_1",
                severity="critical",
                error_code="CHECKOUT_FAIL",
                raw_data={},
                context={},
            )
            for i in range(5)
        ]
        
        pattern = await pattern_detector._create_frequency_pattern(
            signal_type="checkout_error",
            error_code="CHECKOUT_FAIL",
            signals=signals,
        )
        
        assert pattern is not None
        assert pattern.pattern_type == "checkout_issue"
        assert pattern.frequency == 5
        assert pattern.characteristics["frequency_based"] is True
        assert pattern.characteristics["error_code"] == "CHECKOUT_FAIL"
        assert 0.0 <= pattern.confidence <= 0.9
        
        mock_es_client.index_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_cluster_pattern(self, pattern_detector, mock_es_client):
        """Test creating a cluster-based pattern."""
        signals = [
            Signal(
                signal_id=f"s{i}",
                source="webhook_failure",
                merchant_id="merchant_1",
                severity="medium",
                error_message="Webhook timeout",
                raw_data={},
                context={},
            )
            for i in range(4)
        ]
        
        pattern = await pattern_detector._create_cluster_pattern(
            signal_type="webhook_failure",
            signals=signals,
            cluster_label=0,
        )
        
        assert pattern is not None
        assert pattern.pattern_type == "webhook_problem"
        assert pattern.frequency == 4
        assert pattern.characteristics["cluster_based"] is True
        assert pattern.characteristics["cluster_label"] == 0
        assert 0.0 <= pattern.confidence <= 0.85
        
        mock_es_client.index_document.assert_called_once()


class TestPatternMatching:
    """Test pattern matching functionality."""
    
    @pytest.mark.asyncio
    async def test_match_known_pattern_success(self, pattern_detector, mock_es_client):
        """Test matching a signal to a known pattern."""
        # Mock ES response with a matching pattern
        mock_pattern_data = {
            "pattern_id": "pattern_123",
            "pattern_type": "api_failure",
            "confidence": 0.85,
            "signal_ids": ["s1", "s2"],
            "merchant_ids": ["m1"],
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "frequency": 2,
            "characteristics": {"error_code": "API_500"},
        }
        
        mock_es_client.search.return_value = {
            "hits": {
                "hits": [
                    {"_source": mock_pattern_data}
                ]
            }
        }
        
        signal = Signal(
            source="api_failure",
            merchant_id="m1",
            severity="high",
            error_code="API_500",
            error_message="Internal server error",
            raw_data={},
            context={},
        )
        
        pattern = await pattern_detector.match_known_pattern(signal)
        
        assert pattern is not None
        assert pattern.pattern_id == "pattern_123"
        assert pattern.confidence == 0.85
        
        # Verify search was called
        mock_es_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_match_known_pattern_no_match(self, pattern_detector, mock_es_client):
        """Test when no matching pattern is found."""
        mock_es_client.search.return_value = {"hits": {"hits": []}}
        
        signal = Signal(
            source="api_failure",
            merchant_id="m1",
            severity="high",
            error_code="UNKNOWN_ERROR",
            raw_data={},
            context={},
        )
        
        pattern = await pattern_detector.match_known_pattern(signal)
        
        assert pattern is None
    
    @pytest.mark.asyncio
    async def test_match_known_pattern_error_handling(self, pattern_detector, mock_es_client):
        """Test error handling in pattern matching."""
        mock_es_client.search.side_effect = Exception("ES connection failed")
        
        signal = Signal(
            source="api_failure",
            merchant_id="m1",
            severity="high",
            error_code="API_500",
            raw_data={},
            context={},
        )
        
        pattern = await pattern_detector.match_known_pattern(signal)
        
        assert pattern is None


class TestPatternUpdate:
    """Test pattern update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_pattern_success(self, pattern_detector, mock_es_client):
        """Test updating an existing pattern."""
        # Mock existing pattern
        existing_pattern = {
            "pattern_id": "pattern_123",
            "pattern_type": "api_failure",
            "confidence": 0.75,
            "signal_ids": ["s1", "s2"],
            "merchant_ids": ["m1"],
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "frequency": 2,
            "characteristics": {},
        }
        
        mock_es_client.get_document.return_value = existing_pattern
        
        updated_pattern = await pattern_detector.update_pattern(
            pattern_id="pattern_123",
            new_signals=["s3", "s4"],
        )
        
        assert updated_pattern is not None
        assert updated_pattern.frequency == 4  # 2 + 2 new signals
        assert len(updated_pattern.signal_ids) == 4
        # Confidence is recalculated: 0.5 + (4 * 0.05) = 0.7
        assert updated_pattern.confidence == 0.7
        
        # Verify update was called
        mock_es_client.update_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_pattern_not_found(self, pattern_detector, mock_es_client):
        """Test updating a non-existent pattern."""
        mock_es_client.get_document.return_value = None
        
        updated_pattern = await pattern_detector.update_pattern(
            pattern_id="nonexistent",
            new_signals=["s1"],
        )
        
        assert updated_pattern is None
        mock_es_client.update_document.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_pattern_confidence_cap(self, pattern_detector, mock_es_client):
        """Test that confidence is capped at 0.95."""
        existing_pattern = {
            "pattern_id": "pattern_123",
            "pattern_type": "api_failure",
            "confidence": 0.90,
            "signal_ids": ["s1"] * 50,  # Many signals
            "merchant_ids": ["m1"],
            "first_seen": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "frequency": 50,
            "characteristics": {},
        }
        
        mock_es_client.get_document.return_value = existing_pattern
        
        updated_pattern = await pattern_detector.update_pattern(
            pattern_id="pattern_123",
            new_signals=["s51", "s52"],
        )
        
        assert updated_pattern is not None
        assert updated_pattern.confidence <= 0.95


class TestAnalyzeSignals:
    """Test the main analyze_signals method."""
    
    @pytest.mark.asyncio
    async def test_analyze_empty_signals(self, pattern_detector):
        """Test analyzing empty signal list."""
        patterns = await pattern_detector.analyze_signals([])
        
        assert patterns == []
    
    @pytest.mark.asyncio
    async def test_analyze_insufficient_signals(self, pattern_detector):
        """Test with fewer signals than minimum frequency."""
        signals = [
            Signal(
                source="api_failure",
                merchant_id="m1",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
            Signal(
                source="api_failure",
                merchant_id="m2",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            ),
        ]
        
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should return empty since we need at least 3 signals
        assert patterns == []
    
    @pytest.mark.asyncio
    async def test_analyze_signals_creates_patterns(self, pattern_detector, mock_es_client):
        """Test that analyze_signals creates patterns for sufficient signals."""
        base_time = datetime.utcnow()
        signals = [
            Signal(
                signal_id=f"s{i}",
                timestamp=base_time + timedelta(minutes=i),
                source="api_failure",
                merchant_id=f"merchant_{i % 2}",  # 2 merchants
                severity="high",
                error_code="API_500",
                raw_data={},
                context={},
            )
            for i in range(5)
        ]
        
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should create at least one pattern (cross-merchant or frequency)
        assert len(patterns) > 0
        
        # Verify ES indexing was called
        assert mock_es_client.index_document.call_count > 0


class TestHelperMethods:
    """Test helper methods."""
    
    def test_generate_pattern_id(self, pattern_detector):
        """Test pattern ID generation."""
        pattern_id = pattern_detector._generate_pattern_id("test_seed")
        
        assert pattern_id.startswith("pattern_")
        assert len(pattern_id) == 24  # "pattern_" + 16 hex chars
        
        # Same seed should produce same ID
        pattern_id2 = pattern_detector._generate_pattern_id("test_seed")
        assert pattern_id == pattern_id2
        
        # Different seed should produce different ID
        pattern_id3 = pattern_detector._generate_pattern_id("different_seed")
        assert pattern_id != pattern_id3
    
    def test_map_source_to_pattern_type(self, pattern_detector):
        """Test source to pattern type mapping."""
        assert pattern_detector._map_source_to_pattern_type("api_failure") == "api_failure"
        assert pattern_detector._map_source_to_pattern_type("checkout_error") == "checkout_issue"
        assert pattern_detector._map_source_to_pattern_type("webhook_failure") == "webhook_problem"
        assert pattern_detector._map_source_to_pattern_type("support_ticket") == "migration_stage_issue"
        assert pattern_detector._map_source_to_pattern_type("unknown") == "config_error"
    
    def test_extract_text_features(self, pattern_detector):
        """Test text feature extraction."""
        messages = [
            "API error 500",
            "API error 503",
            "Database connection failed",
        ]
        
        features = pattern_detector._extract_text_features(messages)
        
        assert features.shape[0] == 3  # 3 messages
        assert features.shape[1] > 0  # Should have features
        assert isinstance(features, np.ndarray)


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_analyze_signals_with_mixed_types(self, pattern_detector, mock_es_client):
        """Test analyzing signals with different source types."""
        signals = [
            Signal(
                signal_id=f"api_{i}",
                source="api_failure",
                merchant_id="m1",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            )
            for i in range(3)
        ] + [
            Signal(
                signal_id=f"checkout_{i}",
                source="checkout_error",
                merchant_id="m1",
                severity="critical",
                error_code="E2",
                raw_data={},
                context={},
            )
            for i in range(3)
        ]
        
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should handle mixed types correctly
        assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    async def test_analyze_signals_without_error_codes(self, pattern_detector, mock_es_client):
        """Test analyzing signals without error codes (clustering path)."""
        signals = [
            Signal(
                signal_id=f"s{i}",
                source="support_ticket",
                merchant_id="m1",
                severity="medium",
                error_message="Similar error message",
                error_code=None,
                raw_data={},
                context={},
            )
            for i in range(5)
        ]
        
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should attempt clustering
        assert isinstance(patterns, list)
    
    @pytest.mark.asyncio
    async def test_es_error_during_pattern_creation(self, pattern_detector, mock_es_client):
        """Test handling of Elasticsearch errors during pattern creation."""
        mock_es_client.index_document.side_effect = Exception("ES error")
        
        signals = [
            Signal(
                signal_id=f"s{i}",
                source="api_failure",
                merchant_id=f"m{i}",
                severity="high",
                error_code="E1",
                raw_data={},
                context={},
            )
            for i in range(3)
        ]
        
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should handle errors gracefully and return empty list
        assert patterns == []
