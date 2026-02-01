"""
Property-Based Tests for Explainability Requirements.

This module contains property tests that validate explainability and transparency
requirements for the MigrationGuard AI system.
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime

from migrationguard_ai.services.explanation_generator import (
    ExplanationGenerator,
    ExplanationStep,
    Explanation
)


# Strategies for generating test data

@st.composite
def signal_data(draw):
    """Generate signal data for testing."""
    return {
        "signal_id": draw(st.text(min_size=1, max_size=50)),
        "source": draw(st.sampled_from(["zendesk", "intercom", "freshdesk", "api", "webhook"])),
        "merchant_id": draw(st.text(min_size=1, max_size=50)),
        "error_message": draw(st.text(min_size=0, max_size=200)),
        "severity": draw(st.sampled_from(["low", "medium", "high", "critical"]))
    }


@st.composite
def pattern_data(draw):
    """Generate pattern data for testing."""
    return {
        "pattern_id": draw(st.text(min_size=1, max_size=50)),
        "pattern_type": draw(st.sampled_from(["api_failure", "checkout_issue", "webhook_problem", "config_error", "migration_issue"])),
        "description": draw(st.text(min_size=1, max_size=200)),
        "affected_merchants": draw(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10)),
        "occurrence_count": draw(st.integers(min_value=1, max_value=1000))
    }


@st.composite
def root_cause_data(draw):
    """Generate root cause analysis data for testing."""
    return {
        "category": draw(st.sampled_from(["migration_misstep", "platform_regression", "documentation_gap", "merchant_config_error"])),
        "root_cause": draw(st.text(min_size=1, max_size=200)),
        "explanation": draw(st.text(min_size=1, max_size=500))
    }


@st.composite
def decision_data(draw):
    """Generate decision data for testing."""
    return {
        "action_type": draw(st.sampled_from(["support_guidance", "proactive_communication", "engineering_escalation", "temporary_mitigation", "documentation_update"])),
        "rationale": draw(st.text(min_size=1, max_size=200)),
        "expected_outcome": draw(st.text(min_size=1, max_size=200))
    }


@st.composite
def risk_assessment_data(draw):
    """Generate risk assessment data for testing."""
    return {
        "risk_level": draw(st.sampled_from(["low", "medium", "high", "critical"])),
        "requires_approval": draw(st.booleans()),
        "approval_reasons": draw(st.lists(st.text(min_size=1, max_size=100), max_size=5))
    }


# Property 27: Decision explanation presence
# Validates: Requirements 7.1

class TestDecisionExplanationPresence:
    """Test that every decision has a human-readable explanation."""
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_explanation_always_generated(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property 27: Decision explanation presence.
        
        WHEN the system makes a decision
        THEN it SHALL generate a human-readable explanation
        
        Validates: Requirements 7.1
        """
        generator = ExplanationGenerator()
        
        # Generate explanation
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Explanation must exist
        assert explanation is not None
        assert isinstance(explanation, Explanation)
        
        # Explanation must have reasoning chain
        assert len(explanation.reasoning_chain) > 0
        
        # Each step in reasoning chain must have a summary
        for step in explanation.reasoning_chain:
            assert step.summary is not None
            assert len(step.summary) > 0
            assert isinstance(step.summary, str)
        
        # Explanation must have final decision
        assert explanation.final_decision is not None
        assert len(explanation.final_decision) > 0
        
        # Explanation must have confidence level
        assert explanation.confidence_level in ["low", "medium", "high"]
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_explanation_includes_all_stages(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property: Explanation includes all decision stages.
        
        WHEN an explanation is generated
        THEN it SHALL include all stages: signals, patterns, root_cause, decision
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Must have exactly 4 stages
        assert len(explanation.reasoning_chain) == 4
        
        # Stages must be in correct order
        stages = [step.stage for step in explanation.reasoning_chain]
        assert stages == ["signals", "patterns", "root_cause", "decision"]
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_explanation_is_human_readable(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property: Explanation is human-readable.
        
        WHEN an explanation is formatted
        THEN it SHALL produce human-readable text
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Format as text
        text = generator.format_explanation_text(explanation)
        
        # Must be non-empty string
        assert isinstance(text, str)
        assert len(text) > 0
        
        # Must contain key sections
        assert "Explanation for Issue" in text
        assert "Reasoning Chain" in text
        assert "Final Decision" in text
        
        # Must contain stage information
        assert "Signals" in text or "signals" in text
        assert "Patterns" in text or "patterns" in text
        assert "Root Cause" in text or "root cause" in text or "Root cause" in text
        assert "Decision" in text or "decision" in text


# Property 28: Uncertainty communication
# Validates: Requirements 7.3

class TestUncertaintyCommunication:
    """Test that uncertainty is clearly communicated in explanations."""
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        low_confidence=st.floats(min_value=0.0, max_value=0.69)
    )
    def test_low_confidence_flagged(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        low_confidence
    ):
        """
        Property 28: Uncertainty communication.
        
        WHEN confidence is below 0.7
        THEN the explanation SHALL clearly state the uncertainty
        
        Validates: Requirements 7.3
        """
        generator = ExplanationGenerator()
        
        confidences = {
            "signals": 1.0,
            "patterns": 0.5,
            "root_cause": low_confidence,
            "decision": low_confidence
        }
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Low confidence should result in "low" or "medium" confidence level
        assert explanation.confidence_level in ["low", "medium"]
        
        # Should have uncertainty factors
        assert len(explanation.uncertainty_factors) > 0
        
        # Uncertainty should be mentioned in reasoning chain
        uncertainty_mentioned = any(
            "uncertainty" in step.summary.lower() or 
            "confidence" in step.summary.lower() or
            step.uncertainty is not None
            for step in explanation.reasoning_chain
        )
        assert uncertainty_mentioned
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        high_confidence=st.floats(min_value=0.85, max_value=1.0)
    )
    def test_high_confidence_no_unnecessary_warnings(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        high_confidence
    ):
        """
        Property: High confidence doesn't generate unnecessary uncertainty warnings.
        
        WHEN confidence is high (>= 0.85)
        THEN the explanation SHOULD NOT have excessive uncertainty warnings
        """
        generator = ExplanationGenerator()
        
        confidences = {
            "signals": 1.0,
            "patterns": 0.9,
            "root_cause": high_confidence,
            "decision": high_confidence
        }
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # High confidence should result in "high" confidence level
        assert explanation.confidence_level == "high"


# Property 29: Evidence references
# Validates: Requirements 7.4

class TestEvidenceReferences:
    """Test that explanations reference specific data points."""
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=1, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_signal_references_included(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property 29: Evidence references.
        
        WHEN an explanation is generated
        THEN it SHALL reference specific signal_ids and pattern_ids
        
        Validates: Requirements 7.4
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Signal stage should have evidence references
        signal_step = explanation.reasoning_chain[0]
        assert signal_step.stage == "signals"
        assert len(signal_step.evidence_refs) > 0
        
        # Evidence refs should match signal IDs
        signal_ids = [s["signal_id"] for s in signals]
        for ref in signal_step.evidence_refs:
            assert ref in signal_ids
        
        # Pattern stage should have evidence references if patterns exist
        pattern_step = explanation.reasoning_chain[1]
        assert pattern_step.stage == "patterns"
        if len(patterns) > 0:
            assert len(pattern_step.evidence_refs) > 0
            pattern_ids = [p["pattern_id"] for p in patterns]
            for ref in pattern_step.evidence_refs:
                assert ref in pattern_ids
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_data_included_in_steps(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property: Explanation steps include structured data.
        
        WHEN an explanation is generated
        THEN each step SHALL include relevant structured data
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Each step should have data
        for step in explanation.reasoning_chain:
            assert step.data is not None
            assert isinstance(step.data, dict)
            assert len(step.data) > 0


# Property 30: Alternative hypotheses documentation
# Validates: Requirements 7.5

class TestAlternativeHypotheses:
    """Test that alternative hypotheses are documented."""
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(
            st.fixed_dictionaries({
                "description": st.text(min_size=1, max_size=200),
                "reason_rejected": st.text(min_size=1, max_size=200)
            }),
            min_size=1,
            max_size=5
        ),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_alternatives_documented(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property 30: Alternative hypotheses documentation.
        
        WHEN multiple potential causes are considered
        THEN the explanation SHALL document alternatives and why they were rejected
        
        Validates: Requirements 7.5
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Alternatives should be stored
        assert len(explanation.alternatives_considered) > 0
        assert len(explanation.alternatives_considered) == len(alternatives)
        
        # Each alternative should have a description
        for alt in explanation.alternatives_considered:
            assert "description" in alt
            assert len(alt["description"]) > 0
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(
            st.fixed_dictionaries({
                "description": st.text(min_size=1, max_size=200),
                "reason_rejected": st.text(min_size=1, max_size=200)
            }),
            min_size=1,
            max_size=5
        ),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_alternatives_in_formatted_text(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property: Alternatives appear in formatted explanation text.
        
        WHEN alternatives are considered
        THEN they SHALL appear in the formatted explanation
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Format as text
        text = generator.format_explanation_text(explanation)
        
        # Should mention alternatives
        assert "Alternatives Considered" in text or "alternatives" in text.lower()


# Property 31: Explanation audit trail storage
# Validates: Requirements 7.6

class TestExplanationAuditTrail:
    """Test that explanations are stored with decisions."""
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_explanation_has_timestamp(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property 31: Explanation audit trail storage.
        
        WHEN an explanation is generated
        THEN it SHALL include a timestamp for audit purposes
        
        Validates: Requirements 7.6
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Explanation must have timestamp
        assert explanation.created_at is not None
        assert isinstance(explanation.created_at, datetime)
        
        # Each step must have timestamp
        for step in explanation.reasoning_chain:
            assert step.timestamp is not None
            assert isinstance(step.timestamp, datetime)
    
    @given(
        signals=st.lists(signal_data(), min_size=1, max_size=10),
        patterns=st.lists(pattern_data(), min_size=0, max_size=5),
        root_cause=root_cause_data(),
        alternatives=st.lists(st.dictionaries(
            keys=st.sampled_from(["description", "reason_rejected"]),
            values=st.text(min_size=1, max_size=200)
        ), max_size=5),
        decision=decision_data(),
        risk_assessment=risk_assessment_data(),
        confidences=st.fixed_dictionaries({
            "signals": st.floats(min_value=0.0, max_value=1.0),
            "patterns": st.floats(min_value=0.0, max_value=1.0),
            "root_cause": st.floats(min_value=0.0, max_value=1.0),
            "decision": st.floats(min_value=0.0, max_value=1.0)
        })
    )
    def test_explanation_is_serializable(
        self,
        signals,
        patterns,
        root_cause,
        alternatives,
        decision,
        risk_assessment,
        confidences
    ):
        """
        Property: Explanation can be serialized for storage.
        
        WHEN an explanation is generated
        THEN it SHALL be serializable to JSON for audit trail storage
        """
        generator = ExplanationGenerator()
        
        explanation = generator.generate_explanation(
            issue_id="test_issue",
            signals=signals,
            patterns=patterns,
            root_cause_analysis=root_cause,
            alternatives=alternatives,
            decision=decision,
            risk_assessment=risk_assessment,
            confidences=confidences
        )
        
        # Should be able to convert to dict (Pydantic model)
        explanation_dict = explanation.model_dump()
        assert isinstance(explanation_dict, dict)
        assert "issue_id" in explanation_dict
        assert "reasoning_chain" in explanation_dict
        assert "final_decision" in explanation_dict
        
        # Should be able to convert to JSON
        explanation_json = explanation.model_dump_json()
        assert isinstance(explanation_json, str)
        assert len(explanation_json) > 0
