"""Tests for the explanation generator."""

import pytest
from datetime import datetime
from migrationguard_ai.services.explanation_generator import (
    ExplanationGenerator,
    ExplanationStep,
    Explanation,
)


@pytest.fixture
def generator():
    """Create an explanation generator instance."""
    return ExplanationGenerator()


@pytest.fixture
def sample_signals():
    """Sample signals for testing."""
    return [
        {
            "signal_id": "sig-001",
            "source": "api_failure",
            "merchant_id": "merchant-123",
            "error_message": "Authentication failed",
            "error_code": "AUTH_001",
        }
    ]


@pytest.fixture
def sample_patterns():
    """Sample patterns for testing."""
    return [
        {
            "pattern_id": "pat-001",
            "description": "Multiple authentication failures",
            "affected_merchants": ["merchant-123"],
            "occurrence_count": 5,
        }
    ]


@pytest.fixture
def sample_root_cause():
    """Sample root cause analysis."""
    return {
        "category": "migration_misstep",
        "root_cause": "API key format changed",
        "explanation": "The merchant is using old API key format",
    }


@pytest.fixture
def sample_alternatives():
    """Sample alternative hypotheses."""
    return [
        {
            "description": "Platform regression in authentication",
            "reason_rejected": "No recent platform changes detected",
        },
        {
            "description": "Merchant configuration error",
            "reason_rejected": "Configuration validated as correct",
        },
    ]


@pytest.fixture
def sample_decision():
    """Sample decision."""
    return {
        "action_type": "support_guidance",
        "rationale": "Issue can be resolved with guidance",
        "expected_outcome": "Merchant updates API key",
    }


@pytest.fixture
def sample_risk_assessment():
    """Sample risk assessment."""
    return {
        "risk_level": "low",
        "requires_approval": False,
    }


def test_create_signal_explanation_single(generator, sample_signals):
    """Test creating explanation for a single signal."""
    step = generator.create_signal_explanation(sample_signals, confidence=1.0)
    
    assert step.stage == "signals"
    assert "api_failure" in step.summary
    assert "merchant-123" in step.summary
    assert "Authentication failed" in step.summary
    assert step.confidence == 1.0
    assert "sig-001" in step.evidence_refs
    assert step.data["signal_count"] == 1


def test_create_signal_explanation_multiple(generator):
    """Test creating explanation for multiple signals."""
    signals = [
        {"signal_id": "sig-001", "source": "api_failure", "merchant_id": "m1"},
        {"signal_id": "sig-002", "source": "checkout_error", "merchant_id": "m2"},
    ]
    
    step = generator.create_signal_explanation(signals, confidence=1.0)
    
    assert step.stage == "signals"
    assert "2 signals" in step.summary
    assert step.data["signal_count"] == 2
    assert len(step.evidence_refs) == 2


def test_create_pattern_explanation_with_patterns(generator, sample_patterns):
    """Test creating explanation with detected patterns."""
    step = generator.create_pattern_explanation(sample_patterns, confidence=0.95)
    
    assert step.stage == "patterns"
    assert "Multiple authentication failures" in step.summary
    assert step.confidence == 0.95
    assert "pat-001" in step.evidence_refs
    assert step.data["pattern_count"] == 1


def test_create_pattern_explanation_no_patterns(generator):
    """Test creating explanation with no patterns."""
    step = generator.create_pattern_explanation([], confidence=0.0)
    
    assert step.stage == "patterns"
    assert "No recurring patterns" in step.summary
    assert step.uncertainty is not None
    assert "isolated incident" in step.summary


def test_create_root_cause_explanation_high_confidence(generator, sample_root_cause, sample_alternatives):
    """Test root cause explanation with high confidence."""
    step = generator.create_root_cause_explanation(
        sample_root_cause,
        sample_alternatives,
        confidence=0.92
    )
    
    assert step.stage == "root_cause"
    assert "migration configuration issue" in step.summary
    assert "API key format changed" in step.summary
    assert step.confidence == 0.92
    assert step.data["category"] == "migration_misstep"


def test_create_root_cause_explanation_low_confidence(generator, sample_root_cause, sample_alternatives):
    """Test root cause explanation with low confidence."""
    step = generator.create_root_cause_explanation(
        sample_root_cause,
        sample_alternatives,
        confidence=0.65
    )
    
    assert step.stage == "root_cause"
    assert step.uncertainty is not None
    assert "below the 70% threshold" in step.uncertainty
    assert "reviewed by a human operator" in step.uncertainty


def test_create_root_cause_explanation_medium_confidence(generator, sample_root_cause, sample_alternatives):
    """Test root cause explanation with medium confidence."""
    step = generator.create_root_cause_explanation(
        sample_root_cause,
        sample_alternatives,
        confidence=0.75
    )
    
    assert step.stage == "root_cause"
    assert step.uncertainty is not None
    assert "Moderate confidence" in step.uncertainty


def test_create_decision_explanation_no_approval(generator, sample_decision, sample_risk_assessment):
    """Test decision explanation without approval requirement."""
    step = generator.create_decision_explanation(
        sample_decision,
        sample_risk_assessment,
        confidence=0.90
    )
    
    assert step.stage == "decision"
    assert "provide support guidance" in step.summary
    assert "low" in step.summary
    assert step.confidence == 0.90
    assert step.data["action_type"] == "support_guidance"


def test_create_decision_explanation_requires_approval(generator, sample_decision):
    """Test decision explanation with approval requirement."""
    risk_assessment = {
        "risk_level": "high",
        "requires_approval": True,
        "approval_reasons": ["High risk level", "Revenue impact"],
    }
    
    step = generator.create_decision_explanation(
        sample_decision,
        risk_assessment,
        confidence=0.85
    )
    
    assert step.stage == "decision"
    assert "requires human approval" in step.summary
    assert step.uncertainty is not None
    assert "High risk level" in step.uncertainty


def test_generate_explanation_complete(
    generator,
    sample_signals,
    sample_patterns,
    sample_root_cause,
    sample_alternatives,
    sample_decision,
    sample_risk_assessment
):
    """Test generating complete explanation."""
    confidences = {
        "signals": 1.0,
        "patterns": 0.95,
        "root_cause": 0.92,
        "decision": 0.90,
    }
    
    explanation = generator.generate_explanation(
        issue_id="issue-001",
        signals=sample_signals,
        patterns=sample_patterns,
        root_cause_analysis=sample_root_cause,
        alternatives=sample_alternatives,
        decision=sample_decision,
        risk_assessment=sample_risk_assessment,
        confidences=confidences,
    )
    
    assert explanation.issue_id == "issue-001"
    assert len(explanation.reasoning_chain) == 4
    assert explanation.reasoning_chain[0].stage == "signals"
    assert explanation.reasoning_chain[1].stage == "patterns"
    assert explanation.reasoning_chain[2].stage == "root_cause"
    assert explanation.reasoning_chain[3].stage == "decision"
    assert explanation.confidence_level == "high"
    assert explanation.final_decision == "support_guidance"
    assert len(explanation.alternatives_considered) == 2


def test_generate_explanation_low_confidence(
    generator,
    sample_signals,
    sample_patterns,
    sample_root_cause,
    sample_alternatives,
    sample_decision,
    sample_risk_assessment
):
    """Test generating explanation with low confidence."""
    confidences = {
        "signals": 1.0,
        "patterns": 0.50,
        "root_cause": 0.60,
        "decision": 0.65,
    }
    
    explanation = generator.generate_explanation(
        issue_id="issue-002",
        signals=sample_signals,
        patterns=sample_patterns,
        root_cause_analysis=sample_root_cause,
        alternatives=sample_alternatives,
        decision=sample_decision,
        risk_assessment=sample_risk_assessment,
        confidences=confidences,
    )
    
    assert explanation.confidence_level == "low"
    assert len(explanation.uncertainty_factors) > 0


def test_format_explanation_text(
    generator,
    sample_signals,
    sample_patterns,
    sample_root_cause,
    sample_alternatives,
    sample_decision,
    sample_risk_assessment
):
    """Test formatting explanation as text."""
    confidences = {
        "signals": 1.0,
        "patterns": 0.95,
        "root_cause": 0.92,
        "decision": 0.90,
    }
    
    explanation = generator.generate_explanation(
        issue_id="issue-001",
        signals=sample_signals,
        patterns=sample_patterns,
        root_cause_analysis=sample_root_cause,
        alternatives=sample_alternatives,
        decision=sample_decision,
        risk_assessment=sample_risk_assessment,
        confidences=confidences,
    )
    
    text = generator.format_explanation_text(explanation)
    
    assert "Explanation for Issue issue-001" in text
    assert "Reasoning Chain" in text
    assert "Signals" in text
    assert "Patterns" in text
    assert "Root Cause" in text
    assert "Decision" in text
    assert "Alternatives Considered" in text
    assert "Final Decision" in text


def test_explanation_step_model():
    """Test ExplanationStep model validation."""
    step = ExplanationStep(
        stage="signals",
        summary="Test summary",
        confidence=0.95,
        evidence_refs=["sig-001", "sig-002"],
    )
    
    assert step.stage == "signals"
    assert step.summary == "Test summary"
    assert step.confidence == 0.95
    assert len(step.evidence_refs) == 2


def test_explanation_model():
    """Test Explanation model validation."""
    explanation = Explanation(
        issue_id="issue-001",
        final_decision="support_guidance",
        confidence_level="high",
    )
    
    assert explanation.issue_id == "issue-001"
    assert explanation.final_decision == "support_guidance"
    assert explanation.confidence_level == "high"
    assert len(explanation.reasoning_chain) == 0
    assert len(explanation.alternatives_considered) == 0
