"""
Unit tests for root cause analyzer with Claude integration.

Tests cover:
- Analyzer initialization
- Prompt building with various inputs
- Response parsing with sample Claude outputs
- Error handling for API failures
- Circuit breaker behavior

Validates: Requirements 3.1, 3.2, 3.3
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from migrationguard_ai.core.schemas import Signal, Pattern, RootCauseAnalysis
from migrationguard_ai.services.root_cause_analyzer import RootCauseAnalyzer


@pytest.fixture
def sample_signals():
    """Create sample signals for testing."""
    return [
        Signal(
            signal_id="sig_1",
            timestamp=datetime.utcnow(),
            source="api_failure",
            merchant_id="merchant_123",
            severity="high",
            error_message="API request failed with 500 error",
            error_code="API_500",
            raw_data={},
            context={},
        ),
        Signal(
            signal_id="sig_2",
            timestamp=datetime.utcnow(),
            source="api_failure",
            merchant_id="merchant_123",
            severity="high",
            error_message="Internal server error",
            error_code="API_500",
            raw_data={},
            context={},
        ),
    ]


@pytest.fixture
def sample_patterns():
    """Create sample patterns for testing."""
    return [
        Pattern(
            pattern_id="pat_1",
            pattern_type="api_failure",
            confidence=0.85,
            signal_ids=["sig_1", "sig_2"],
            merchant_ids=["merchant_123"],
            first_seen=datetime.utcnow(),
            last_seen=datetime.utcnow(),
            frequency=2,
            characteristics={"error_code": "API_500", "frequency_based": True},
        )
    ]


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = AsyncMock()
    return client


@pytest.fixture
def analyzer_with_mock(mock_anthropic_client):
    """Create analyzer with mocked Anthropic client."""
    with patch('migrationguard_ai.services.root_cause_analyzer.AsyncAnthropic') as mock_class:
        mock_class.return_value = mock_anthropic_client
        analyzer = RootCauseAnalyzer(api_key="test_key")
        analyzer.client = mock_anthropic_client
        return analyzer


class TestAnalyzerInitialization:
    """Test analyzer initialization and configuration."""
    
    def test_initialization_with_api_key(self):
        """Test that analyzer initializes with provided API key."""
        with patch('migrationguard_ai.services.root_cause_analyzer.AsyncAnthropic'):
            analyzer = RootCauseAnalyzer(api_key="test_key")
            
            assert analyzer.api_key == "test_key"
            assert analyzer.model == "claude-sonnet-4.5-20250514"
            assert analyzer.max_tokens == 4096
            assert analyzer.temperature == 0.3
    
    def test_initialization_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch('migrationguard_ai.services.root_cause_analyzer.get_settings') as mock_settings:
            mock_settings.return_value.anthropic_api_key = ""
            
            with pytest.raises(ValueError, match="Anthropic API key is required"):
                RootCauseAnalyzer()


class TestPromptBuilding:
    """Test prompt building functionality."""
    
    def test_build_prompt_with_signals_only(self, analyzer_with_mock, sample_signals):
        """Test building prompt with only signals."""
        prompt = analyzer_with_mock._build_analysis_prompt(
            signals=sample_signals,
            patterns=[],
            merchant_context=None
        )
        
        assert "## Signals (2 total)" in prompt
        assert "Signal 1" in prompt
        assert "Signal 2" in prompt
        assert "API_500" in prompt
        assert "api_failure" in prompt
    
    def test_build_prompt_with_patterns(self, analyzer_with_mock, sample_signals, sample_patterns):
        """Test building prompt with signals and patterns."""
        prompt = analyzer_with_mock._build_analysis_prompt(
            signals=sample_signals,
            patterns=sample_patterns,
            merchant_context=None
        )
        
        assert "## Signals (2 total)" in prompt
        assert "## Detected Patterns (1 total)" in prompt
        assert "Pattern 1" in prompt
        assert "api_failure" in prompt
        assert "0.85" in prompt
    
    def test_build_prompt_with_merchant_context(self, analyzer_with_mock, sample_signals):
        """Test building prompt with merchant context."""
        merchant_context = {
            "merchant_id": "merchant_123",
            "migration_stage": "testing",
            "platform_version": "v2.5.0"
        }
        
        prompt = analyzer_with_mock._build_analysis_prompt(
            signals=sample_signals,
            patterns=[],
            merchant_context=merchant_context
        )
        
        assert "## Merchant Context" in prompt
        assert "merchant_123" in prompt
        assert "testing" in prompt
        assert "v2.5.0" in prompt
    
    def test_build_prompt_limits_signals_to_10(self, analyzer_with_mock):
        """Test that prompt building limits signals to first 10."""
        signals = [
            Signal(
                signal_id=f"sig_{i}",
                source="api_failure",
                merchant_id="merchant_123",
                severity="high",
                error_code="ERR",
                raw_data={},
                context={},
            )
            for i in range(15)
        ]
        
        prompt = analyzer_with_mock._build_analysis_prompt(
            signals=signals,
            patterns=[],
            merchant_context=None
        )
        
        assert "## Signals (15 total)" in prompt
        assert "Signal 10" in prompt
        assert "Signal 11" not in prompt
        assert "and 5 more signals" in prompt


class TestResponseParsing:
    """Test Claude response parsing."""
    
    def test_parse_valid_json_response(self, analyzer_with_mock):
        """Test parsing a valid JSON response."""
        response_data = {
            "category": "platform_regression",
            "confidence": 0.85,
            "reasoning": "The API is returning 500 errors consistently, indicating a server-side issue.",
            "evidence": ["Multiple 500 errors", "Same error code across signals"],
            "alternatives_considered": [
                {
                    "hypothesis": "Merchant configuration error",
                    "reason_rejected": "Error occurs across multiple merchants"
                }
            ],
            "recommended_actions": ["Escalate to engineering", "Check server logs"]
        }
        
        # Mock response content
        mock_content = [MagicMock(text=json.dumps(response_data))]
        
        analysis = analyzer_with_mock._parse_analysis(mock_content)
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.category == "platform_regression"
        assert analysis.confidence == 0.85
        assert len(analysis.evidence) == 2
        assert len(analysis.alternatives_considered) == 1
        assert len(analysis.recommended_actions) == 2
    
    def test_parse_response_with_markdown_code_blocks(self, analyzer_with_mock):
        """Test parsing response wrapped in markdown code blocks."""
        response_data = {
            "category": "migration_misstep",
            "confidence": 0.75,
            "reasoning": "Merchant likely misconfigured API credentials.",
            "evidence": ["Authentication errors"],
            "alternatives_considered": [],
            "recommended_actions": ["Verify API credentials"]
        }
        
        # Wrap in markdown code blocks
        text = f"```json\n{json.dumps(response_data)}\n```"
        mock_content = [MagicMock(text=text)]
        
        analysis = analyzer_with_mock._parse_analysis(mock_content)
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.category == "migration_misstep"
        assert analysis.confidence == 0.75
    
    def test_parse_response_with_dict_content(self, analyzer_with_mock):
        """Test parsing response when content is dict format."""
        response_data = {
            "category": "documentation_gap",
            "confidence": 0.65,
            "reasoning": "Documentation doesn't cover this scenario.",
            "evidence": ["Common error pattern"],
            "alternatives_considered": [],
            "recommended_actions": ["Update documentation"]
        }
        
        # Content as dict
        mock_content = [{"text": json.dumps(response_data)}]
        
        analysis = analyzer_with_mock._parse_analysis(mock_content)
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.category == "documentation_gap"
    
    def test_parse_invalid_json_raises_error(self, analyzer_with_mock):
        """Test that invalid JSON raises ValueError."""
        mock_content = [MagicMock(text="This is not valid JSON")]
        
        with pytest.raises(ValueError, match="Invalid JSON response"):
            analyzer_with_mock._parse_analysis(mock_content)
    
    def test_parse_missing_required_field_raises_error(self, analyzer_with_mock):
        """Test that missing required fields raises ValueError."""
        # Missing 'reasoning' field
        response_data = {
            "category": "config_error",
            "confidence": 0.8,
            "evidence": ["Evidence"],
            "recommended_actions": ["Action"]
        }
        
        mock_content = [MagicMock(text=json.dumps(response_data))]
        
        with pytest.raises(ValueError):
            analyzer_with_mock._parse_analysis(mock_content)


class TestAnalyzeMethod:
    """Test the main analyze method."""
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, analyzer_with_mock, sample_signals, sample_patterns):
        """Test successful analysis."""
        # Mock Claude API response
        response_data = {
            "category": "platform_regression",
            "confidence": 0.85,
            "reasoning": "Server-side error pattern detected.",
            "evidence": ["500 errors", "Multiple occurrences"],
            "alternatives_considered": [],
            "recommended_actions": ["Escalate to engineering"]
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        analyzer_with_mock.client.messages.create = AsyncMock(return_value=mock_response)
        
        analysis = await analyzer_with_mock.analyze(
            signals=sample_signals,
            patterns=sample_patterns,
            merchant_context={"merchant_id": "merchant_123"}
        )
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.category == "platform_regression"
        assert analysis.confidence == 0.85
        
        # Verify API was called
        analyzer_with_mock.client.messages.create.assert_called_once()
        call_kwargs = analyzer_with_mock.client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4.5-20250514"
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 4096
    
    @pytest.mark.asyncio
    async def test_analyze_without_signals_raises_error(self, analyzer_with_mock):
        """Test that analyzing without signals raises ValueError."""
        with pytest.raises(ValueError, match="At least one signal is required"):
            await analyzer_with_mock.analyze(
                signals=[],
                patterns=[],
                merchant_context=None
            )
    
    @pytest.mark.asyncio
    async def test_analyze_with_api_error(self, analyzer_with_mock, sample_signals):
        """Test handling of API errors with graceful degradation."""
        # Mock API error
        analyzer_with_mock.client.messages.create = AsyncMock(
            side_effect=Exception("API connection failed")
        )
        
        # Should not raise exception, but use fallback instead
        result = await analyzer_with_mock.analyze(
            signals=sample_signals,
            patterns=[],
            merchant_context=None
        )
        
        # Verify fallback was used
        assert result is not None
        assert result.category in [
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ]
        assert 0.0 <= result.confidence <= 1.0

    
    @pytest.mark.asyncio
    async def test_analyze_builds_correct_prompt(self, analyzer_with_mock, sample_signals):
        """Test that analyze builds the prompt correctly."""
        response_data = {
            "category": "config_error",
            "confidence": 0.7,
            "reasoning": "Configuration issue detected.",
            "evidence": ["Config mismatch"],
            "alternatives_considered": [],
            "recommended_actions": ["Fix configuration"]
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        analyzer_with_mock.client.messages.create = AsyncMock(return_value=mock_response)
        
        await analyzer_with_mock.analyze(
            signals=sample_signals,
            patterns=[],
            merchant_context={"merchant_id": "test_merchant"}
        )
        
        # Check that the prompt was built with correct content
        call_kwargs = analyzer_with_mock.client.messages.create.call_args.kwargs
        prompt = call_kwargs["messages"][0]["content"]
        
        assert "test_merchant" in prompt
        assert "API_500" in prompt
        assert "## Signals" in prompt


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_analyze_with_empty_patterns(self, analyzer_with_mock, sample_signals):
        """Test analysis with empty patterns list."""
        response_data = {
            "category": "migration_misstep",
            "confidence": 0.6,
            "reasoning": "Analysis without patterns.",
            "evidence": ["Signal evidence"],
            "alternatives_considered": [],
            "recommended_actions": ["Action"]
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        analyzer_with_mock.client.messages.create = AsyncMock(return_value=mock_response)
        
        analysis = await analyzer_with_mock.analyze(
            signals=sample_signals,
            patterns=[],
            merchant_context=None
        )
        
        assert isinstance(analysis, RootCauseAnalysis)
    
    @pytest.mark.asyncio
    async def test_analyze_with_low_confidence(self, analyzer_with_mock, sample_signals):
        """Test analysis that returns low confidence."""
        response_data = {
            "category": "documentation_gap",
            "confidence": 0.45,
            "reasoning": "Uncertain analysis with limited evidence.",
            "evidence": ["Weak signal"],
            "alternatives_considered": [
                {"hypothesis": "Alt 1", "reason_rejected": "Insufficient evidence"}
            ],
            "recommended_actions": ["Gather more data"]
        }
        
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(response_data))]
        analyzer_with_mock.client.messages.create = AsyncMock(return_value=mock_response)
        
        analysis = await analyzer_with_mock.analyze(
            signals=sample_signals,
            patterns=[],
            merchant_context=None
        )
        
        assert analysis.confidence < 0.7
        assert len(analysis.alternatives_considered) > 0
    
    def test_parse_response_with_multiple_content_blocks(self, analyzer_with_mock):
        """Test parsing response with multiple content blocks."""
        response_data = {
            "category": "platform_regression",
            "confidence": 0.8,
            "reasoning": "Multi-block response.",
            "evidence": ["Evidence"],
            "alternatives_considered": [],
            "recommended_actions": ["Action"]
        }
        
        # Split JSON across multiple blocks
        json_str = json.dumps(response_data)
        mid = len(json_str) // 2
        
        mock_content = [
            MagicMock(text=json_str[:mid]),
            MagicMock(text=json_str[mid:])
        ]
        
        analysis = analyzer_with_mock._parse_analysis(mock_content)
        
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.category == "platform_regression"


class TestCircuitBreaker:
    """Test circuit breaker behavior."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_annotation_present(self, analyzer_with_mock):
        """Test that analyze method has circuit breaker decorator."""
        # Check that the method has the circuit decorator
        assert hasattr(analyzer_with_mock.analyze, '__wrapped__')
    
    @pytest.mark.asyncio
    async def test_multiple_failures_trigger_circuit_breaker(self, analyzer_with_mock, sample_signals):
        """Test that multiple failures trigger graceful degradation."""
        # Mock repeated failures
        analyzer_with_mock.client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )
        
        # All calls should use fallback instead of raising exceptions
        for _ in range(3):
            result = await analyzer_with_mock.analyze(
                signals=sample_signals,
                patterns=[],
                merchant_context=None
            )
            
            # Verify fallback was used
            assert result is not None
            assert result.category in [
                "migration_misstep",
                "platform_regression",
                "documentation_gap",
                "config_error"
            ]

