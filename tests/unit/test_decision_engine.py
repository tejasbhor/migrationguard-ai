"""
Unit tests for Decision Engine.

These tests verify specific examples and edge cases for the decision engine,
including decision rules for each root cause category and risk assessment logic.
"""

import pytest
from datetime import datetime

from migrationguard_ai.services.decision_engine import DecisionEngine, Decision, RiskAssessment
from migrationguard_ai.core.schemas import RootCauseAnalysis


class TestDecisionEngine:
    """Unit tests for DecisionEngine."""
    
    def test_initialization(self):
        """Test decision engine initialization."""
        engine = DecisionEngine()
        assert engine is not None
    
    def test_singleton_pattern(self):
        """Test that get_decision_engine returns singleton instance."""
        from migrationguard_ai.services.decision_engine import get_decision_engine
        
        engine1 = get_decision_engine()
        engine2 = get_decision_engine()
        
        assert engine1 is engine2
    
    def test_migration_misstep_decision(self):
        """Test decision for migration misstep category."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=0.85,
            reasoning="Webhook URL still points to old domain",
            evidence=["404 errors in webhook logs", "Migration completed 2 days ago"],
            recommended_actions=["Update webhook URL", "Test webhook delivery"]
        )
        
        context = {
            "merchant_id": "merchant_123",
            "migration_stage": "phase_2",
            "severity": "high",
            "affects_checkout": False,
            "support_system": "zendesk",
            "ticket_id": "T-12345"
        }
        
        decision = engine.decide(analysis, context, "issue_001")
        
        assert decision.action_type == "support_guidance"
        assert decision.issue_id == "issue_001"
        assert decision.confidence == 0.85
        assert decision.root_cause_category == "migration_misstep"
        assert "merchant_id" in decision.parameters
        assert decision.parameters["merchant_id"] == "merchant_123"
        assert "message" in decision.parameters
        assert len(decision.estimated_outcome) > 0
    
    def test_platform_regression_decision(self):
        """Test decision for platform regression category."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="platform_regression",
            confidence=0.92,
            reasoning="API endpoint returning 500 errors after platform update",
            evidence=["Multiple merchants affected", "Started after deployment"],
            recommended_actions=["Rollback deployment", "Fix API bug"]
        )
        
        context = {
            "merchant_id": "merchant_123",
            "error_message": "API 500 error",
            "affected_merchants": ["merchant_123", "merchant_456", "merchant_789"],
            "signal_ids": ["sig_001", "sig_002"],
            "pattern_ids": ["pat_001"]
        }
        
        decision = engine.decide(analysis, context, "issue_002")
        
        assert decision.action_type == "engineering_escalation"
        assert decision.issue_id == "issue_002"
        assert "title" in decision.parameters
        assert "description" in decision.parameters
        assert "priority" in decision.parameters
        assert "affected_merchants" in decision.parameters
        assert len(decision.parameters["affected_merchants"]) == 3
    
    def test_documentation_gap_decision(self):
        """Test decision for documentation gap category."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="documentation_gap",
            confidence=0.78,
            reasoning="Migration guide missing webhook configuration steps",
            evidence=["Multiple merchants asking same question", "No docs on webhook setup"],
            recommended_actions=["Add webhook section to migration guide", "Include examples"]
        )
        
        context = {
            "merchant_id": "merchant_123",
            "documentation_section": "migration_guide",
            "signal_ids": ["sig_001", "sig_002", "sig_003"]
        }
        
        decision = engine.decide(analysis, context, "issue_003")
        
        assert decision.action_type == "documentation_update"
        assert decision.issue_id == "issue_003"
        assert "section" in decision.parameters
        assert decision.parameters["section"] == "migration_guide"
        assert "issue_description" in decision.parameters
        assert "suggested_content" in decision.parameters
    
    def test_config_error_high_confidence_mitigation(self):
        """Test config error with high confidence triggers mitigation."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="config_error",
            confidence=0.88,
            reasoning="Webhook URL has typo in domain name",
            evidence=["URL validation failed", "Similar to resolved cases"],
            recommended_actions=["Correct webhook URL", "Verify connectivity"]
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affected_resource": "webhook_url",
            "affects_checkout": False,
            "affects_payment": False
        }
        
        decision = engine.decide(analysis, context, "issue_004")
        
        assert decision.action_type == "temporary_mitigation"
        assert decision.confidence == 0.88
        assert "config_change" in decision.parameters
        assert "merchant_id" in decision.parameters
    
    def test_config_error_low_confidence_guidance(self):
        """Test config error with low confidence provides guidance instead."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="config_error",
            confidence=0.62,
            reasoning="Possible configuration issue with API credentials",
            evidence=["Authentication failures", "Unclear error messages"],
            recommended_actions=["Check API credentials", "Verify permissions"]
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affected_resource": "api_credentials",
            "support_system": "intercom",
            "ticket_id": "T-67890"
        }
        
        decision = engine.decide(analysis, context, "issue_005")
        
        assert decision.action_type == "support_guidance"
        assert decision.confidence == 0.62
        assert "message" in decision.parameters
        assert decision.parameters["support_system"] == "intercom"
    
    def test_unknown_category_escalation(self):
        """Test unknown category triggers escalation."""
        engine = DecisionEngine()
        
        # Create analysis with invalid category (will be caught by validation)
        # For testing, we'll directly call the handler
        analysis = RootCauseAnalysis(
            category="migration_misstep",  # Valid category for creation
            confidence=0.5,
            reasoning="Unknown issue type",
            evidence=["Unclear symptoms"],
            recommended_actions=["Investigate further"]
        )
        
        # Manually set to unknown to test handler
        analysis.category = "unknown_category"
        
        context = {
            "merchant_id": "merchant_123",
            "error_message": "Unknown error"
        }
        
        decision = engine._handle_unknown_category(analysis, context, "issue_006")
        
        assert decision.action_type == "engineering_escalation"
        assert decision.risk_level == "high"
        assert decision.confidence == 0.0
        assert decision.root_cause_category == "unknown"


class TestRiskAssessment:
    """Unit tests for risk assessment logic."""
    
    def test_revenue_impact_critical_risk(self):
        """Test that revenue impact results in critical risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_001",
            issue_id="issue_001",
            action_type="support_guidance",
            risk_level="low",  # Will be updated
            requires_approval=False,
            confidence=0.85,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affects_checkout": True
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.risk_level == "critical"
        assert risk.requires_approval is True
        assert "revenue_impact" in risk.risk_factors
    
    def test_payment_impact_critical_risk(self):
        """Test that payment impact results in critical risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_002",
            issue_id="issue_002",
            action_type="temporary_mitigation",
            risk_level="low",
            requires_approval=False,
            confidence=0.90,
            root_cause_category="config_error",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affects_payment": True
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.risk_level == "critical"
        assert risk.requires_approval is True
        assert "payment_impact" in risk.risk_factors
    
    def test_config_change_requires_approval(self):
        """Test that config changes require approval."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_003",
            issue_id="issue_003",
            action_type="temporary_mitigation",
            risk_level="low",
            requires_approval=False,
            confidence=0.85,
            root_cause_category="config_error",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affects_checkout": False
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.requires_approval is True
        assert "config_change" in risk.risk_factors
    
    def test_low_confidence_high_risk(self):
        """Test that low confidence results in high risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_004",
            issue_id="issue_004",
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
            confidence=0.65,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123"
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.requires_approval is True
        assert "low_confidence" in risk.risk_factors
    
    def test_multi_merchant_impact(self):
        """Test that multi-merchant impact increases risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_005",
            issue_id="issue_005",
            action_type="engineering_escalation",
            risk_level="low",
            requires_approval=False,
            confidence=0.85,
            root_cause_category="platform_regression",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "affected_merchants": ["merchant_123", "merchant_456", "merchant_789"]
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert "multi_merchant_impact" in risk.risk_factors
    
    def test_critical_severity_factor(self):
        """Test that critical severity is a risk factor."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_006",
            issue_id="issue_006",
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
            confidence=0.85,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "severity": "critical"
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert "critical_severity" in risk.risk_factors
    
    def test_low_risk_no_factors(self):
        """Test that no risk factors results in low risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_007",
            issue_id="issue_007",
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
            confidence=0.85,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "severity": "low"
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.risk_level == "low"
        assert len(risk.risk_factors) == 0
        # Low risk support guidance doesn't require approval
    
    def test_medium_risk_single_factor(self):
        """Test that single risk factor results in medium risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_008",
            issue_id="issue_008",
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
            confidence=0.85,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "severity": "critical"
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.risk_level == "medium"
        assert len(risk.risk_factors) == 1
    
    def test_high_risk_multiple_factors(self):
        """Test that multiple risk factors result in high risk."""
        engine = DecisionEngine()
        
        decision = Decision(
            decision_id="dec_009",
            issue_id="issue_009",
            action_type="support_guidance",
            risk_level="low",
            requires_approval=False,
            confidence=0.65,
            root_cause_category="migration_misstep",
            reasoning="Test",
            estimated_outcome="Test outcome",
            parameters={}
        )
        
        context = {
            "merchant_id": "merchant_123",
            "severity": "critical",
            "affected_merchants": ["merchant_123", "merchant_456"]
        }
        
        risk = engine.assess_risk(decision, context)
        
        assert risk.risk_level == "high"
        assert len(risk.risk_factors) >= 2
        assert risk.requires_approval is True


class TestHelperMethods:
    """Unit tests for helper methods."""
    
    def test_generate_guidance(self):
        """Test guidance message generation."""
        engine = DecisionEngine()
        
        analysis = RootCauseAnalysis(
            category="migration_misstep",
            confidence=0.85,
            reasoning="Webhook URL needs updating",
            evidence=["404 errors"],
            recommended_actions=["Update webhook URL", "Test delivery"]
        )
        
        context = {"merchant_id": "merchant_123"}
        
        message = engine._generate_guidance(analysis, context)
        
        assert "Webhook URL needs updating" in message
        assert "Update webhook URL" in message
        assert "Test delivery" in message
    
    def test_determine_escalation_priority(self):
        """Test escalation priority determination."""
        engine = DecisionEngine()
        
        # Critical severity
        context1 = {"severity": "critical", "affected_merchants": ["m1"]}
        assert engine._determine_escalation_priority(context1) == "critical"
        
        # Many affected merchants
        context2 = {"severity": "medium", "affected_merchants": ["m1", "m2", "m3", "m4", "m5", "m6"]}
        assert engine._determine_escalation_priority(context2) == "critical"
        
        # High severity
        context3 = {"severity": "high", "affected_merchants": ["m1"]}
        assert engine._determine_escalation_priority(context3) == "high"
        
        # Multiple merchants
        context4 = {"severity": "medium", "affected_merchants": ["m1", "m2", "m3"]}
        assert engine._determine_escalation_priority(context4) == "high"
        
        # Default
        context5 = {"severity": "low", "affected_merchants": ["m1"]}
        assert engine._determine_escalation_priority(context5) == "medium"
    
    def test_can_auto_fix_config(self):
        """Test auto-fix configuration determination."""
        engine = DecisionEngine()
        
        # High confidence, safe resource, single merchant
        analysis1 = RootCauseAnalysis(
            category="config_error",
            confidence=0.85,
            reasoning="Test",
            evidence=["test"],
            recommended_actions=["test"]
        )
        context1 = {
            "affected_resource": "webhook_url",
            "affects_checkout": False,
            "affects_payment": False,
            "affected_merchants": ["m1"]
        }
        assert engine._can_auto_fix_config(analysis1, context1) is True
        
        # Low confidence
        analysis2 = RootCauseAnalysis(
            category="config_error",
            confidence=0.75,
            reasoning="Test",
            evidence=["test"],
            recommended_actions=["test"]
        )
        assert engine._can_auto_fix_config(analysis2, context1) is False
        
        # Affects checkout
        context3 = {
            "affected_resource": "webhook_url",
            "affects_checkout": True,
            "affected_merchants": ["m1"]
        }
        assert engine._can_auto_fix_config(analysis1, context3) is False
        
        # Multiple merchants
        context4 = {
            "affected_resource": "webhook_url",
            "affects_checkout": False,
            "affected_merchants": ["m1", "m2"]
        }
        assert engine._can_auto_fix_config(analysis1, context4) is False
        
        # Unsafe resource
        context5 = {
            "affected_resource": "payment_gateway",
            "affects_checkout": False,
            "affected_merchants": ["m1"]
        }
        assert engine._can_auto_fix_config(analysis1, context5) is False
