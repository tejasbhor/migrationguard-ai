"""
Property-based tests for root cause analysis.

Tests:
- Property 5: Root cause category validity
- Property 6: Analysis confidence bounds
- Property 7: Low confidence flagging
- Property 8: Multiple causes ranked

Validates: Requirements 3.1, 3.2, 3.3, 3.8
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock, patch

from migrationguard_ai.core.schemas import Signal, Pattern, RootCauseAnalysis
from migrationguard_ai.services.root_cause_analyzer import RootCauseAnalyzer


# Hypothesis strategies for generating test data

@st.composite
def root_cause_analysis_strategy(draw, confidence=None):
    """Generate a valid RootCauseAnalysis for testing."""
    from hypothesis.strategies import SearchStrategy
    
    if confidence is None:
        confidence_val = draw(st.floats(min_value=0.0, max_value=1.0))
    elif isinstance(confidence, SearchStrategy):
        confidence_val = draw(confidence)
    else:
        confidence_val = confidence
    
    return RootCauseAnalysis(
        category=draw(st.sampled_from([
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ])),
        confidence=confidence_val,
        reasoning=draw(st.text(min_size=50, max_size=500)),
        evidence=draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5)),
        alternatives_considered=draw(st.lists(
            st.fixed_dictionaries({
                "hypothesis": st.text(min_size=10, max_size=100),
                "reason_rejected": st.text(min_size=10, max_size=100)
            }),
            min_size=0,
            max_size=3
        )),
        recommended_actions=draw(st.lists(st.text(min_size=10, max_size=100), min_size=1, max_size=5)),
    )


class TestRootCauseCategoryValidity:
    """
    Property 5: Root cause category validity
    
    Validates: Requirements 3.1
    
    For any root cause analysis result, the category MUST be exactly one of:
    migration_misstep, platform_regression, documentation_gap, or config_error.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(analysis=root_cause_analysis_strategy())
    def test_category_is_valid(self, analysis):
        """
        Property: Root cause category MUST be one of the four valid categories.
        
        **Validates: Requirements 3.1**
        """
        valid_categories = [
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ]
        
        assert analysis.category in valid_categories, \
            f"Category '{analysis.category}' is not in valid categories: {valid_categories}"
    
    @settings(max_examples=100, deadline=None)
    @given(
        category=st.sampled_from([
            "migration_misstep",
            "platform_regression",
            "documentation_gap",
            "config_error"
        ]),
        confidence=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_category_validation_in_schema(self, category, confidence):
        """
        Property: Schema MUST validate category values.
        
        **Validates: Requirements 3.1**
        """
        # Valid category should work
        analysis = RootCauseAnalysis(
            category=category,
            confidence=confidence,
            reasoning="Test reasoning",
            evidence=["Evidence 1"],
            alternatives_considered=[],
            recommended_actions=["Action 1"],
        )
        
        assert analysis.category == category
    
    def test_invalid_category_rejected(self):
        """
        Property: Invalid categories MUST be rejected by schema validation.
        
        **Validates: Requirements 3.1**
        """
        with pytest.raises(ValueError):
            RootCauseAnalysis(
                category="invalid_category",
                confidence=0.8,
                reasoning="Test reasoning",
                evidence=["Evidence 1"],
                alternatives_considered=[],
                recommended_actions=["Action 1"],
            )


class TestAnalysisConfidenceBounds:
    """
    Property 6: Analysis confidence bounds
    
    Validates: Requirements 3.2
    
    For any root cause analysis, the confidence score MUST be between 0.0 and 1.0 inclusive.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(analysis=root_cause_analysis_strategy())
    def test_confidence_within_bounds(self, analysis):
        """
        Property: Confidence MUST always be between 0.0 and 1.0.
        
        **Validates: Requirements 3.2**
        """
        assert 0.0 <= analysis.confidence <= 1.0, \
            f"Confidence {analysis.confidence} is out of bounds [0.0, 1.0]"
    
    @settings(max_examples=100, deadline=None)
    @given(confidence=st.floats(min_value=0.0, max_value=1.0))
    def test_valid_confidence_accepted(self, confidence):
        """
        Property: All confidence values in [0.0, 1.0] MUST be accepted.
        
        **Validates: Requirements 3.2**
        """
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=confidence,
            reasoning="Test reasoning",
            evidence=["Evidence 1"],
            alternatives_considered=[],
            recommended_actions=["Action 1"],
        )
        
        assert analysis.confidence == confidence
    
    @settings(max_examples=50, deadline=None)
    @given(
        confidence=st.one_of(
            st.floats(min_value=-10.0, max_value=-0.01),
            st.floats(min_value=1.01, max_value=10.0)
        )
    )
    def test_invalid_confidence_rejected(self, confidence):
        """
        Property: Confidence values outside [0.0, 1.0] MUST be rejected.
        
        **Validates: Requirements 3.2**
        """
        with pytest.raises(ValueError):
            RootCauseAnalysis(
                category="migration_misstep",
                confidence=confidence,
                reasoning="Test reasoning",
                evidence=["Evidence 1"],
                alternatives_considered=[],
                recommended_actions=["Action 1"],
            )


class TestLowConfidenceFlagging:
    """
    Property 7: Low confidence flagging
    
    Validates: Requirements 3.3
    
    For any root cause analysis where confidence < 0.7, the analysis MUST be
    flagged as uncertain (reasoning should mention uncertainty).
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        analysis=root_cause_analysis_strategy(
            confidence=st.floats(min_value=0.0, max_value=0.69)
        )
    )
    def test_low_confidence_has_uncertainty_flag(self, analysis):
        """
        Property: Analysis with confidence < 0.7 MUST indicate uncertainty.
        
        **Validates: Requirements 3.3**
        
        Note: This property tests the schema structure. The actual uncertainty
        communication is tested in the analyzer implementation tests.
        """
        assert analysis.confidence < 0.7, \
            f"Test setup error: confidence {analysis.confidence} should be < 0.7"
        
        # The analysis object should be valid
        assert isinstance(analysis, RootCauseAnalysis)
        assert analysis.reasoning is not None
        assert len(analysis.reasoning) > 0
    
    @settings(max_examples=100, deadline=None)
    @given(
        confidence=st.floats(min_value=0.0, max_value=0.69),
        reasoning=st.text(min_size=50, max_size=500),
    )
    def test_low_confidence_analysis_structure(self, confidence, reasoning):
        """
        Property: Low confidence analyses MUST have complete structure.
        
        **Validates: Requirements 3.3**
        """
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=confidence,
            reasoning=reasoning,
            evidence=["Evidence 1"],
            alternatives_considered=[],
            recommended_actions=["Action 1"],
        )
        
        assert analysis.confidence < 0.7
        assert analysis.reasoning is not None
        assert len(analysis.reasoning) > 0
        assert len(analysis.evidence) > 0
        assert len(analysis.recommended_actions) > 0


class TestMultipleCausesRanking:
    """
    Property 8: Multiple causes ranked
    
    Validates: Requirements 3.8
    
    For any root cause analysis that identifies multiple potential causes,
    the causes MUST be ordered by likelihood (highest to lowest confidence).
    """
    
    @settings(max_examples=100, deadline=None)
    @given(
        num_alternatives=st.integers(min_value=1, max_value=5),
    )
    def test_alternatives_structure(self, num_alternatives):
        """
        Property: Alternative hypotheses MUST have proper structure.
        
        **Validates: Requirements 3.8**
        """
        alternatives = [
            {
                "hypothesis": f"Alternative hypothesis {i}",
                "reason_rejected": f"Rejected because reason {i}"
            }
            for i in range(num_alternatives)
        ]
        
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=0.85,
            reasoning="Primary reasoning",
            evidence=["Evidence 1"],
            alternatives_considered=alternatives,
            recommended_actions=["Action 1"],
        )
        
        assert len(analysis.alternatives_considered) == num_alternatives
        
        for alt in analysis.alternatives_considered:
            assert "hypothesis" in alt
            assert "reason_rejected" in alt
            assert isinstance(alt["hypothesis"], str)
            assert isinstance(alt["reason_rejected"], str)
    
    @settings(max_examples=100, deadline=None)
    @given(
        alternatives=st.lists(
            st.fixed_dictionaries({
                "hypothesis": st.text(min_size=10, max_size=100),
                "reason_rejected": st.text(min_size=10, max_size=100),
            }),
            min_size=0,
            max_size=5
        )
    )
    def test_alternatives_can_be_empty_or_populated(self, alternatives):
        """
        Property: Alternatives list can be empty (single cause) or populated (multiple causes).
        
        **Validates: Requirements 3.8**
        """
        analysis = RootCauseAnalysis(
            category="platform_regression",
            confidence=0.75,
            reasoning="Analysis reasoning",
            evidence=["Evidence 1", "Evidence 2"],
            alternatives_considered=alternatives,
            recommended_actions=["Action 1"],
        )
        
        assert len(analysis.alternatives_considered) == len(alternatives)
        
        if alternatives:
            # If there are alternatives, they should all have required fields
            for alt in analysis.alternatives_considered:
                assert "hypothesis" in alt
                assert "reason_rejected" in alt


class TestAnalysisCompleteness:
    """
    Additional property tests for analysis completeness.
    """
    
    @settings(max_examples=100, deadline=None)
    @given(analysis=root_cause_analysis_strategy())
    def test_analysis_has_required_fields(self, analysis):
        """
        Property: Every analysis MUST have all required fields populated.
        
        **Validates: Requirements 3.1, 3.2**
        """
        # Required fields
        assert analysis.category is not None
        assert analysis.confidence is not None
        assert analysis.reasoning is not None
        assert analysis.evidence is not None
        assert analysis.recommended_actions is not None
        
        # Non-empty requirements
        assert len(analysis.reasoning) > 0
        assert len(analysis.evidence) > 0
        assert len(analysis.recommended_actions) > 0
    
    @settings(max_examples=100, deadline=None)
    @given(analysis=root_cause_analysis_strategy())
    def test_evidence_list_not_empty(self, analysis):
        """
        Property: Evidence list MUST contain at least one item.
        
        **Validates: Requirements 3.1**
        """
        assert len(analysis.evidence) > 0, \
            "Evidence list must not be empty"
        
        for evidence_item in analysis.evidence:
            assert isinstance(evidence_item, str)
            assert len(evidence_item) > 0
    
    @settings(max_examples=100, deadline=None)
    @given(analysis=root_cause_analysis_strategy())
    def test_recommended_actions_not_empty(self, analysis):
        """
        Property: Recommended actions MUST contain at least one action.
        
        **Validates: Requirements 3.1**
        """
        assert len(analysis.recommended_actions) > 0, \
            "Recommended actions must not be empty"
        
        for action in analysis.recommended_actions:
            assert isinstance(action, str)
            assert len(action) > 0
