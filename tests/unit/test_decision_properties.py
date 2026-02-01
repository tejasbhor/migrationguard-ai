"""
Property-based tests for Decision Engine.

These tests verify universal properties that should hold for all decisions
made by the decision engine, regardless of input.
"""

import pytest
from hypothesis import given, settings, strategies as st
from hypothesis.strategies import SearchStrategy

from migrationguard_ai.services.decision_engine import DecisionEngine, Decision, RiskAssessment
from migrationguard_ai.core.schemas import RootCauseAnalysis


# Strategy for generating root cause categories
root_cause_category_strategy = st.sampled_from([
    "migration_misstep",
    "platform_regression",
    "documentation_gap",
    "config_error"
])


# Strategy for generating confidence scores
confidence_strategy = st.floats(min_value=0.0, max_value=1.0)


# Strategy for generating RootCauseAnalysis
def root_cause_analysis_strategy():
    return st.builds(
        RootCauseAnalysis,
        category=root_cause_category_strategy,
        confidence=confidence_strategy,
        reasoning=st.text(min_size=10, max_size=200),
        evidence=st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5),
        alternatives_considered=st.lists(
            st.fixed_dictionaries({
                "hypothesis": st.text(min_size=5, max_size=50),
                "confidence": confidence_strategy,
                "rejected_reason": st.text(min_size=5, max_size=50)
            }),
            max_size=3
        ),
        recommended_actions=st.lists(st.text(min_size=5, max_size=50), min_size=1, max_size=5)
    )


# Strategy for generating decision context
def context_strategy():
    return st.fixed_dictionaries({
        "merchant_id": st.text(min_size=5, max_size=20),
        "migration_stage": st.sampled_from(["phase_1", "phase_2", "phase_3", "complete"]),
        "severity": st.sampled_from(["low", "medium", "high", "critical"]),
        "affects_checkout": st.booleans(),
        "affects_payment": st.booleans(),
        "support_system": st.sampled_from(["zendesk", "intercom", "freshdesk"]),
        "ticket_id": st.text(min_size=5, max_size=20),
        "signal_ids": st.lists(st.text(min_size=5, max_size=20), min_size=1, max_size=5),
        "pattern_ids": st.lists(st.text(min_size=5, max_size=20), max_size=3),
        "affected_merchants": st.lists(st.text(min_size=5, max_size=20), min_size=1, max_size=10),
        "error_message": st.text(min_size=10, max_size=100),
        "affected_resource": st.text(min_size=5, max_size=50),
        "documentation_section": st.text(min_size=5, max_size=30)
    })


class TestDecisionEngineProperties:
    """Property-based tests for Decision Engine."""
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_property_11_high_risk_approval_requirement(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Feature: migrationguard-ai, Property 11: High-risk approval requirement
        
        For any decision where risk_level is "high" or "critical", 
        the requires_approval field must be true.
        
        Validates: Requirements 4.3
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: High or critical risk requires approval
        if decision.risk_level in ["high", "critical"]:
            assert decision.requires_approval is True, \
                f"Decision with risk_level={decision.risk_level} must require approval"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_property_12_low_confidence_approval_requirement(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Feature: migrationguard-ai, Property 12: Low-confidence approval requirement
        
        For any decision where the confidence score < 0.7, 
        the requires_approval field must be true.
        
        Validates: Requirements 4.4
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Low confidence requires approval
        if decision.confidence < 0.7:
            assert decision.requires_approval is True, \
                f"Decision with confidence={decision.confidence} must require approval"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_property_13_revenue_affecting_decisions_require_approval(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Feature: migrationguard-ai, Property 13: Revenue-affecting decisions require approval
        
        For any decision that could affect merchant revenue (affects_checkout = true 
        or action_type = temporary_mitigation affecting checkout), the risk_level 
        must be "high" or "critical" and requires_approval must be true.
        
        Validates: Requirements 4.8, 10.2
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Revenue-affecting decisions require approval
        affects_revenue = (
            context.get("affects_checkout", False) or
            context.get("affects_payment", False) or
            (decision.action_type == "temporary_mitigation" and 
             "checkout" in context.get("affected_resource", "").lower())
        )
        
        if affects_revenue:
            assert decision.risk_level in ["high", "critical"], \
                f"Revenue-affecting decision must have high/critical risk, got {decision.risk_level}"
            assert decision.requires_approval is True, \
                "Revenue-affecting decision must require approval"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_property_15_config_modification_approval_requirement(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Feature: migrationguard-ai, Property 15: Config modification approval requirement
        
        For any decision where action_type = "temporary_mitigation", 
        the requires_approval field must be true.
        
        Validates: Requirements 10.3
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Config modifications require approval
        if decision.action_type == "temporary_mitigation":
            assert decision.requires_approval is True, \
                "temporary_mitigation action must require approval"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_action_type_validity(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Test that all decisions have valid action types.
        
        Property 9: Action type validity
        Validates: Requirements 4.1
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Action type must be valid
        valid_action_types = [
            "support_guidance",
            "proactive_communication",
            "engineering_escalation",
            "temporary_mitigation",
            "documentation_update"
        ]
        
        assert decision.action_type in valid_action_types, \
            f"Invalid action_type: {decision.action_type}"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_risk_level_validity(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Test that all decisions have valid risk levels.
        
        Property 10: Risk level validity
        Validates: Requirements 4.2
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Risk level must be valid
        valid_risk_levels = ["low", "medium", "high", "critical"]
        
        assert decision.risk_level in valid_risk_levels, \
            f"Invalid risk_level: {decision.risk_level}"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_estimated_outcome_presence(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Test that all decisions have estimated outcomes.
        
        Property 14: Expected outcome presence
        Validates: Requirements 4.7
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Estimated outcome must be present and non-empty
        assert decision.estimated_outcome is not None, \
            "Decision must have estimated_outcome"
        assert len(decision.estimated_outcome) > 0, \
            "Decision estimated_outcome must be non-empty"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_confidence_bounds(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Test that decision confidence is within valid bounds.
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: Confidence must be between 0 and 1
        assert 0.0 <= decision.confidence <= 1.0, \
            f"Decision confidence must be between 0 and 1, got {decision.confidence}"
    
    @given(
        analysis=root_cause_analysis_strategy(),
        context=context_strategy(),
        issue_id=st.text(min_size=5, max_size=20)
    )
    @settings(max_examples=100)
    def test_decision_completeness(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ):
        """
        Test that decisions have all required fields populated.
        """
        engine = DecisionEngine()
        
        # Make decision
        decision = engine.decide(analysis, context, issue_id)
        
        # Property: All required fields must be present
        assert decision.decision_id is not None
        assert decision.issue_id == issue_id
        assert decision.action_type is not None
        assert decision.risk_level is not None
        assert decision.requires_approval is not None
        assert decision.confidence is not None
        assert decision.root_cause_category is not None
        assert decision.reasoning is not None
        assert decision.estimated_outcome is not None
        assert decision.parameters is not None
        assert isinstance(decision.parameters, dict)
