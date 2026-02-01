"""
Property-based tests for pattern detection.

Tests:
- Property 3: Cross-merchant pattern correlation
- Property 4: Pattern confidence bounds

Validates: Requirements 2.2, 2.4
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from migrationguard_ai.core.schemas import Signal, Pattern
from migrationguard_ai.services.pattern_detector import PatternDetector


# Hypothesis strategies for generating test data

@st.composite
def signal_strategy(draw, merchant_id=None, error_code=None, source=None):
    """Generate a valid Signal for testing."""
    # Draw from strategies if they are strategies, otherwise use the value
    from hypothesis.strategies import SearchStrategy
    
    if source is None:
        source_val = draw(st.sampled_from([
            "support_ticket", "api_failure", "checkout_error", "webhook_failure"
        ]))
    elif isinstance(source, SearchStrategy):
        source_val = draw(source)
    else:
        source_val = source
    
    if merchant_id is None:
        merchant_id_val = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"))))
    elif isinstance(merchant_id, SearchStrategy):
        merchant_id_val = draw(merchant_id)
    else:
        merchant_id_val = merchant_id
    
    if error_code is None:
        error_code_val = draw(st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))))
    elif isinstance(error_code, SearchStrategy):
        error_code_val = draw(error_code)
    else:
        error_code_val = error_code
    
    return Signal(
        source=source_val,
        merchant_id=merchant_id_val,
        severity=draw(st.sampled_from(["low", "medium", "high", "critical"])),
        error_message=draw(st.text(min_size=10, max_size=100)),
        error_code=error_code_val,
        raw_data={},
        context={},
    )


@st.composite
def cross_merchant_signals_strategy(draw):
    """Generate signals for cross-merchant pattern testing."""
    # Generate a common error code
    error_code = draw(st.text(min_size=5, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "Nd"))))
    
    # Generate 2-5 different merchants
    num_merchants = draw(st.integers(min_value=2, max_value=5))
    merchant_ids = [f"merchant_{i}" for i in range(num_merchants)]
    
    # Generate 3-10 signals with the same error code across different merchants
    num_signals = draw(st.integers(min_value=3, max_value=10))
    
    signals = []
    for _ in range(num_signals):
        merchant_id = draw(st.sampled_from(merchant_ids))
        # Use draw instead of .example()
        signal = draw(signal_strategy(
            merchant_id=merchant_id,
            error_code=error_code,
            source="api_failure",
        ))
        signals.append(signal)
    
    return signals, error_code, merchant_ids


class TestCrossMerchantCorrelation:
    """
    Property 3: Cross-merchant pattern correlation
    
    Validates: Requirements 2.2
    
    When multiple merchants experience the same error within a time window,
    the system MUST detect a cross-merchant pattern.
    """
    
    def _create_pattern_detector(self):
        """Create a pattern detector with mocked ES client."""
        mock_es_client = AsyncMock()
        mock_es_client.index_document = AsyncMock()
        mock_es_client.search = AsyncMock(return_value={"hits": {"hits": []}})
        return PatternDetector(mock_es_client)
    
    @settings(max_examples=100, deadline=None)
    @given(cross_merchant_signals_strategy())
    @pytest.mark.asyncio
    async def test_cross_merchant_pattern_detected(
        self,
        signals_and_metadata,
    ):
        """
        Property: When N merchants (N >= 2) experience the same error code,
        a cross-merchant pattern MUST be detected.
        
        **Validates: Requirements 2.2**
        """
        signals, error_code, merchant_ids = signals_and_metadata
        pattern_detector = self._create_pattern_detector()
        
        # Count unique merchants in signals
        unique_merchants = set(s.merchant_id for s in signals)
        
        # Skip if all signals are from same merchant (edge case)
        if len(unique_merchants) < 2:
            return
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Should detect at least one pattern
        assert len(patterns) > 0, "No patterns detected for cross-merchant signals"
        
        # Find cross-merchant patterns
        cross_merchant_patterns = [
            p for p in patterns
            if p.characteristics.get("cross_merchant", False)
        ]
        
        # Should have at least one cross-merchant pattern
        assert len(cross_merchant_patterns) > 0, \
            f"No cross-merchant pattern detected for {len(unique_merchants)} merchants"
        
        # Verify pattern properties
        pattern = cross_merchant_patterns[0]
        
        # Pattern should include signals from multiple merchants
        assert len(pattern.merchant_ids) >= 2, \
            f"Pattern should include at least 2 merchants, got {len(pattern.merchant_ids)}"
        
        # Pattern should have the correct error code
        assert pattern.characteristics.get("error_code") == error_code, \
            f"Pattern error code mismatch: expected {error_code}, got {pattern.characteristics.get('error_code')}"
        
        # Pattern should include all signals
        assert len(pattern.signal_ids) == len(signals), \
            f"Pattern should include all {len(signals)} signals, got {len(pattern.signal_ids)}"
    
    @settings(max_examples=100, deadline=None)
    @given(cross_merchant_signals_strategy())
    @pytest.mark.asyncio
    async def test_cross_merchant_confidence_increases_with_merchants(
        self,
        signals_and_metadata,
    ):
        """
        Property: Cross-merchant pattern confidence MUST increase with
        the number of affected merchants.
        
        **Validates: Requirements 2.2, 2.4**
        """
        signals, error_code, merchant_ids = signals_and_metadata
        pattern_detector = self._create_pattern_detector()
        
        # Count unique merchants in signals
        unique_merchants = set(s.merchant_id for s in signals)
        
        # Skip if all signals are from same merchant (edge case)
        if len(unique_merchants) < 2:
            return
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Find cross-merchant pattern
        cross_merchant_patterns = [
            p for p in patterns
            if p.characteristics.get("cross_merchant", False)
        ]
        
        if cross_merchant_patterns:
            pattern = cross_merchant_patterns[0]
            
            # Confidence should increase with merchant count
            # Base: 0.6, +0.05 per merchant, +0.02 per signal
            expected_min_confidence = 0.6 + (len(pattern.merchant_ids) * 0.05)
            
            assert pattern.confidence >= expected_min_confidence, \
                f"Confidence {pattern.confidence} should be >= {expected_min_confidence} for {len(pattern.merchant_ids)} merchants"
            
            # Confidence should not exceed 0.95
            assert pattern.confidence <= 0.95, \
                f"Confidence {pattern.confidence} should not exceed 0.95"


class TestPatternConfidenceBounds:
    """
    Property 4: Pattern confidence bounds
    
    Validates: Requirements 2.4
    
    Pattern confidence scores MUST always be between 0.0 and 1.0,
    and MUST increase with pattern frequency.
    """
    
    def _create_pattern_detector(self):
        """Create a pattern detector with mocked ES client."""
        mock_es_client = AsyncMock()
        mock_es_client.index_document = AsyncMock()
        mock_es_client.search = AsyncMock(return_value={"hits": {"hits": []}})
        return PatternDetector(mock_es_client)
    
    @settings(max_examples=100, deadline=None)
    @given(
        signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("TEST_ERROR"),
                source=st.just("api_failure"),
            ),
            min_size=3,
            max_size=50
        )
    )
    @pytest.mark.asyncio
    async def test_confidence_within_bounds(
        self,
        signals,
    ):
        """
        Property: Pattern confidence MUST always be between 0.0 and 1.0.
        
        **Validates: Requirements 2.4**
        """
        pattern_detector = self._create_pattern_detector()
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Check all patterns have valid confidence
        for pattern in patterns:
            assert 0.0 <= pattern.confidence <= 1.0, \
                f"Pattern confidence {pattern.confidence} is out of bounds [0.0, 1.0]"
    
    @settings(max_examples=100, deadline=None)
    @given(
        # Generate two sets of signals with different frequencies
        small_signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("FREQ_TEST"),
                source=st.just("api_failure"),
            ),
            min_size=3,
            max_size=5
        ),
        large_signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("FREQ_TEST"),
                source=st.just("api_failure"),
            ),
            min_size=10,
            max_size=20
        )
    )
    @pytest.mark.asyncio
    async def test_confidence_increases_with_frequency(
        self,
        small_signals,
        large_signals,
    ):
        """
        Property: Pattern confidence MUST increase monotonically with frequency.
        
        **Validates: Requirements 2.4**
        """
        pattern_detector = self._create_pattern_detector()
        
        # Analyze small set
        small_patterns = await pattern_detector.analyze_signals(small_signals)
        
        # Analyze large set
        large_patterns = await pattern_detector.analyze_signals(large_signals)
        
        # Find frequency-based patterns
        small_freq_patterns = [
            p for p in small_patterns
            if p.characteristics.get("frequency_based", False)
        ]
        
        large_freq_patterns = [
            p for p in large_patterns
            if p.characteristics.get("frequency_based", False)
        ]
        
        # If both have frequency patterns, verify confidence increases
        if small_freq_patterns and large_freq_patterns:
            small_confidence = small_freq_patterns[0].confidence
            large_confidence = large_freq_patterns[0].confidence
            
            assert small_confidence <= large_confidence, \
                f"Confidence should increase with frequency: {small_confidence} <= {large_confidence}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("HIGH_FREQ_ERROR"),
                source=st.just("api_failure"),
            ),
            min_size=3,
            max_size=100
        )
    )
    @pytest.mark.asyncio
    async def test_confidence_caps_at_maximum(
        self,
        signals,
    ):
        """
        Property: Pattern confidence MUST be capped at a maximum value (0.95).
        
        **Validates: Requirements 2.4**
        """
        pattern_detector = self._create_pattern_detector()
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # All patterns should have confidence <= 0.95
        for pattern in patterns:
            assert pattern.confidence <= 0.95, \
                f"Pattern confidence {pattern.confidence} exceeds maximum of 0.95"
    
    @settings(max_examples=100, deadline=None)
    @given(
        signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("FREQ_TEST"),
                source=st.just("api_failure"),
            ),
            min_size=3,
            max_size=20
        )
    )
    @pytest.mark.asyncio
    async def test_pattern_frequency_matches_signal_count(
        self,
        signals,
    ):
        """
        Property: Pattern frequency MUST equal the number of signals in the pattern.
        
        **Validates: Requirements 2.4**
        """
        pattern_detector = self._create_pattern_detector()
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Verify frequency matches signal count
        for pattern in patterns:
            assert pattern.frequency == len(pattern.signal_ids), \
                f"Pattern frequency {pattern.frequency} should equal signal count {len(pattern.signal_ids)}"
            
            # Frequency should be at least min_pattern_frequency (3)
            assert pattern.frequency >= 3, \
                f"Pattern frequency {pattern.frequency} should be at least 3"


class TestPatternTypeValidity:
    """
    Additional property tests for pattern type validity.
    """
    
    def _create_pattern_detector(self):
        """Create a pattern detector with mocked ES client."""
        mock_es_client = AsyncMock()
        mock_es_client.index_document = AsyncMock()
        mock_es_client.search = AsyncMock(return_value={"hits": {"hits": []}})
        return PatternDetector(mock_es_client)
    
    @settings(max_examples=100, deadline=None)
    @given(
        source=st.sampled_from([
            "support_ticket", "api_failure", "checkout_error", "webhook_failure"
        ]),
        signals=st.lists(
            signal_strategy(
                merchant_id=st.just("test_merchant"),
                error_code=st.just("TYPE_TEST"),
            ),
            min_size=3,
            max_size=10
        )
    )
    @pytest.mark.asyncio
    async def test_pattern_type_matches_signal_source(
        self,
        source,
        signals,
    ):
        """
        Property: Pattern type MUST be correctly mapped from signal source.
        
        **Validates: Requirements 2.1**
        """
        pattern_detector = self._create_pattern_detector()
        
        # Override source for all signals
        for signal in signals:
            signal.source = source
        
        # Analyze signals
        patterns = await pattern_detector.analyze_signals(signals)
        
        # Expected pattern type mapping
        expected_types = {
            "api_failure": "api_failure",
            "checkout_error": "checkout_issue",
            "webhook_failure": "webhook_problem",
            "support_ticket": "migration_stage_issue",
        }
        
        expected_type = expected_types[source]
        
        # Verify pattern types
        for pattern in patterns:
            assert pattern.pattern_type == expected_type, \
                f"Pattern type {pattern.pattern_type} should be {expected_type} for source {source}"
