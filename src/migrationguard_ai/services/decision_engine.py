"""
Decision Engine for MigrationGuard AI.

This module implements the decision-making logic that determines appropriate actions
based on root cause analysis. It includes rule-based decision trees, risk assessment,
and approval requirement determination.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from migrationguard_ai.core.schemas import RootCauseAnalysis
from migrationguard_ai.core.safe_mode import get_safe_mode_manager


# Decision and Action Models
class Decision(BaseModel):
    """Represents a decision made by the decision engine."""
    
    decision_id: str = Field(..., description="Unique identifier for the decision")
    issue_id: str = Field(..., description="Associated issue ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Action details
    action_type: Literal[
        "support_guidance",
        "proactive_communication",
        "engineering_escalation",
        "temporary_mitigation",
        "documentation_update"
    ]
    
    # Risk assessment
    risk_level: Literal["low", "medium", "high", "critical"]
    requires_approval: bool = Field(default=False)
    
    # Decision context
    confidence: float = Field(..., ge=0.0, le=1.0)
    root_cause_category: str
    reasoning: str
    estimated_outcome: str
    
    # Action parameters
    parameters: dict = Field(default_factory=dict)
    
    # Metadata
    alternatives_considered: list[dict] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Risk assessment for a proposed action."""
    
    risk_level: Literal["low", "medium", "high", "critical"]
    risk_factors: list[str] = Field(default_factory=list)
    requires_approval: bool
    reasoning: str


class DecisionEngine:
    """
    Decision engine that determines appropriate actions based on root cause analysis.
    
    Implements rule-based decision trees for each root cause category and performs
    risk assessment to determine approval requirements.
    """
    
    def __init__(self):
        """Initialize the decision engine."""
        self.safe_mode_manager = get_safe_mode_manager()
    
    def decide(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Select appropriate action based on root cause analysis.
        
        Args:
            analysis: Root cause analysis result
            context: Additional context (merchant_id, migration_stage, etc.)
            issue_id: Associated issue ID
            
        Returns:
            Decision with selected action and risk assessment
        """
        # Check if safe mode is active - if so, all decisions require approval
        if self.safe_mode_manager.is_active():
            # Route to appropriate handler based on root cause category
            if analysis.category == "migration_misstep":
                decision = self._handle_migration_misstep(analysis, context, issue_id)
            elif analysis.category == "platform_regression":
                decision = self._handle_platform_regression(analysis, context, issue_id)
            elif analysis.category == "documentation_gap":
                decision = self._handle_documentation_gap(analysis, context, issue_id)
            elif analysis.category == "config_error":
                decision = self._handle_config_error(analysis, context, issue_id)
            else:
                # Fallback for unknown categories
                decision = self._handle_unknown_category(analysis, context, issue_id)
            
            # Perform risk assessment
            risk_assessment = self.assess_risk(decision, context)
            
            # Update decision with risk assessment
            decision.risk_level = risk_assessment.risk_level
            # Force approval requirement in safe mode
            decision.requires_approval = True
            
            return decision
        
        # Normal operation (not in safe mode)
        # Route to appropriate handler based on root cause category
        if analysis.category == "migration_misstep":
            decision = self._handle_migration_misstep(analysis, context, issue_id)
        elif analysis.category == "platform_regression":
            decision = self._handle_platform_regression(analysis, context, issue_id)
        elif analysis.category == "documentation_gap":
            decision = self._handle_documentation_gap(analysis, context, issue_id)
        elif analysis.category == "config_error":
            decision = self._handle_config_error(analysis, context, issue_id)
        else:
            # Fallback for unknown categories
            decision = self._handle_unknown_category(analysis, context, issue_id)
        
        # Perform risk assessment
        risk_assessment = self.assess_risk(decision, context)
        
        # Update decision with risk assessment
        decision.risk_level = risk_assessment.risk_level
        decision.requires_approval = risk_assessment.requires_approval
        
        return decision
    
    def _handle_migration_misstep(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Handle migration misstep - provide support guidance to merchant.
        
        Args:
            analysis: Root cause analysis
            context: Decision context
            issue_id: Issue ID
            
        Returns:
            Decision with support guidance action
        """
        guidance_message = self._generate_guidance(analysis, context)
        
        return Decision(
            decision_id=f"dec_{issue_id}_{int(datetime.utcnow().timestamp())}",
            issue_id=issue_id,
            action_type="support_guidance",
            risk_level="low",  # Will be updated by risk assessment
            confidence=analysis.confidence,
            root_cause_category=analysis.category,
            reasoning=f"Migration misstep detected. Providing guidance to merchant: {analysis.reasoning}",
            estimated_outcome="Merchant will receive step-by-step guidance to resolve the issue",
            parameters={
                "message": guidance_message,
                "merchant_id": context.get("merchant_id"),
                "support_system": context.get("support_system", "zendesk"),
                "ticket_id": context.get("ticket_id")
            },
            alternatives_considered=[
                {
                    "action": "proactive_communication",
                    "reason": "Rejected: Issue already reported via ticket, no need for proactive outreach"
                }
            ]
        )
    
    def _handle_platform_regression(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Handle platform regression - escalate to engineering.
        
        Args:
            analysis: Root cause analysis
            context: Decision context
            issue_id: Issue ID
            
        Returns:
            Decision with engineering escalation action
        """
        return Decision(
            decision_id=f"dec_{issue_id}_{int(datetime.utcnow().timestamp())}",
            issue_id=issue_id,
            action_type="engineering_escalation",
            risk_level="high",  # Will be updated by risk assessment
            confidence=analysis.confidence,
            root_cause_category=analysis.category,
            reasoning=f"Platform regression detected. Escalating to engineering: {analysis.reasoning}",
            estimated_outcome="Engineering team will investigate and fix the platform bug",
            parameters={
                "title": f"Platform Regression: {context.get('error_message', 'Unknown error')}",
                "description": self._build_escalation_description(analysis, context),
                "priority": self._determine_escalation_priority(context),
                "affected_merchants": context.get("affected_merchants", [context.get("merchant_id")]),
                "signals": context.get("signal_ids", []),
                "patterns": context.get("pattern_ids", [])
            },
            alternatives_considered=[
                {
                    "action": "temporary_mitigation",
                    "reason": "Rejected: Platform bug requires code fix, not configuration change"
                }
            ]
        )
    
    def _handle_documentation_gap(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Handle documentation gap - update documentation and provide guidance.
        
        Args:
            analysis: Root cause analysis
            context: Decision context
            issue_id: Issue ID
            
        Returns:
            Decision with documentation update action
        """
        return Decision(
            decision_id=f"dec_{issue_id}_{int(datetime.utcnow().timestamp())}",
            issue_id=issue_id,
            action_type="documentation_update",
            risk_level="low",  # Will be updated by risk assessment
            confidence=analysis.confidence,
            root_cause_category=analysis.category,
            reasoning=f"Documentation gap identified. Creating update request: {analysis.reasoning}",
            estimated_outcome="Documentation will be updated to prevent future confusion",
            parameters={
                "section": context.get("documentation_section", "migration_guide"),
                "issue_description": analysis.reasoning,
                "suggested_content": self._generate_doc_suggestion(analysis, context),
                "merchant_id": context.get("merchant_id"),
                "related_signals": context.get("signal_ids", [])
            },
            alternatives_considered=[
                {
                    "action": "support_guidance",
                    "reason": "Also needed: Will provide immediate guidance while doc is updated"
                }
            ]
        )
    
    def _handle_config_error(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Handle configuration error - apply temporary mitigation or provide guidance.
        
        Args:
            analysis: Root cause analysis
            context: Decision context
            issue_id: Issue ID
            
        Returns:
            Decision with mitigation or guidance action
        """
        # Determine if we can safely apply a config fix
        can_auto_fix = self._can_auto_fix_config(analysis, context)
        
        if can_auto_fix and analysis.confidence >= 0.8:
            action_type = "temporary_mitigation"
            reasoning = f"Configuration error detected with high confidence. Applying automatic fix: {analysis.reasoning}"
            estimated_outcome = "Configuration will be corrected automatically, resolving the issue"
            parameters = {
                "config_change": self._generate_config_fix(analysis, context),
                "merchant_id": context.get("merchant_id"),
                "resource": context.get("affected_resource"),
                "validation_required": True
            }
        else:
            action_type = "support_guidance"
            reasoning = f"Configuration error detected. Providing guidance for manual correction: {analysis.reasoning}"
            estimated_outcome = "Merchant will receive guidance to correct their configuration"
            parameters = {
                "message": self._generate_config_guidance(analysis, context),
                "merchant_id": context.get("merchant_id"),
                "support_system": context.get("support_system", "zendesk"),
                "ticket_id": context.get("ticket_id")
            }
        
        return Decision(
            decision_id=f"dec_{issue_id}_{int(datetime.utcnow().timestamp())}",
            issue_id=issue_id,
            action_type=action_type,
            risk_level="medium",  # Will be updated by risk assessment
            confidence=analysis.confidence,
            root_cause_category=analysis.category,
            reasoning=reasoning,
            estimated_outcome=estimated_outcome,
            parameters=parameters,
            alternatives_considered=[
                {
                    "action": "temporary_mitigation" if action_type == "support_guidance" else "support_guidance",
                    "reason": f"Rejected: {'Confidence too low for automatic fix' if action_type == 'support_guidance' else 'High confidence allows automatic fix'}"
                }
            ]
        )
    
    def _handle_unknown_category(
        self,
        analysis: RootCauseAnalysis,
        context: dict,
        issue_id: str
    ) -> Decision:
        """
        Handle unknown category - escalate for human review.
        
        Args:
            analysis: Root cause analysis
            context: Decision context
            issue_id: Issue ID
            
        Returns:
            Decision with escalation action
        """
        return Decision(
            decision_id=f"dec_{issue_id}_{int(datetime.utcnow().timestamp())}",
            issue_id=issue_id,
            action_type="engineering_escalation",
            risk_level="high",
            confidence=0.0,
            root_cause_category="unknown",
            reasoning=f"Unknown root cause category: {analysis.category}. Escalating for human review.",
            estimated_outcome="Human operator will review and determine appropriate action",
            parameters={
                "title": f"Unknown Issue Category: {context.get('error_message', 'Unknown')}",
                "description": f"Analysis: {analysis.reasoning}",
                "priority": "high",
                "merchant_id": context.get("merchant_id")
            },
            alternatives_considered=[]
        )
    
    def assess_risk(self, decision: Decision, context: dict) -> RiskAssessment:
        """
        Assess risk level of proposed action.
        
        Args:
            decision: Proposed decision
            context: Decision context
            
        Returns:
            Risk assessment with risk level and approval requirement
        """
        risk_factors = []
        
        # Check for revenue impact
        if context.get("affects_checkout", False):
            risk_factors.append("revenue_impact")
        
        if context.get("affects_payment", False):
            risk_factors.append("payment_impact")
        
        # Check for production configuration changes
        if decision.action_type == "temporary_mitigation":
            risk_factors.append("config_change")
        
        # Check confidence level
        if decision.confidence < 0.7:
            risk_factors.append("low_confidence")
        
        # Check for multiple affected merchants
        affected_merchants = context.get("affected_merchants", [context.get("merchant_id")])
        if len(affected_merchants) > 1:
            risk_factors.append("multi_merchant_impact")
        
        # Check for critical severity
        if context.get("severity") == "critical":
            risk_factors.append("critical_severity")
        
        # Determine risk level based on factors
        if "revenue_impact" in risk_factors or "payment_impact" in risk_factors:
            risk_level = "critical"
        elif len(risk_factors) >= 2:
            risk_level = "high"
        elif len(risk_factors) == 1:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Determine approval requirement
        requires_approval = (
            risk_level in ["high", "critical"] or
            decision.confidence < 0.7 or
            decision.action_type == "temporary_mitigation"
        )
        
        reasoning = self._build_risk_reasoning(risk_level, risk_factors, requires_approval)
        
        return RiskAssessment(
            risk_level=risk_level,
            risk_factors=risk_factors,
            requires_approval=requires_approval,
            reasoning=reasoning
        )
    
    # Helper methods for generating content
    
    def _generate_guidance(self, analysis: RootCauseAnalysis, context: dict) -> str:
        """Generate support guidance message."""
        return f"""Based on our analysis, we've identified the following issue:

{analysis.reasoning}

Recommended actions:
{chr(10).join(f"- {action}" for action in analysis.recommended_actions)}

If you need further assistance, please don't hesitate to reach out to our support team.
"""
    
    def _generate_config_guidance(self, analysis: RootCauseAnalysis, context: dict) -> str:
        """Generate configuration guidance message."""
        return f"""We've detected a configuration issue that needs your attention:

{analysis.reasoning}

To resolve this issue:
{chr(10).join(f"{i+1}. {action}" for i, action in enumerate(analysis.recommended_actions))}

Please review your configuration and make the necessary changes. If you need help, our support team is here to assist.
"""
    
    def _build_escalation_description(self, analysis: RootCauseAnalysis, context: dict) -> str:
        """Build escalation ticket description."""
        return f"""Platform Regression Detected

Root Cause Analysis:
{analysis.reasoning}

Evidence:
{chr(10).join(f"- {evidence}" for evidence in analysis.evidence)}

Affected Merchant(s): {context.get('merchant_id')}
Migration Stage: {context.get('migration_stage', 'Unknown')}
Severity: {context.get('severity', 'Unknown')}

Signals: {', '.join(context.get('signal_ids', []))}
Patterns: {', '.join(context.get('pattern_ids', []))}
"""
    
    def _generate_doc_suggestion(self, analysis: RootCauseAnalysis, context: dict) -> str:
        """Generate documentation update suggestion."""
        return f"""Suggested documentation update:

Issue: {analysis.reasoning}

Recommended content to add:
{chr(10).join(f"- {action}" for action in analysis.recommended_actions)}

This will help merchants avoid similar issues in the future.
"""
    
    def _determine_escalation_priority(self, context: dict) -> str:
        """Determine escalation priority."""
        severity = context.get("severity", "medium")
        affected_count = len(context.get("affected_merchants", []))
        
        if severity == "critical" or affected_count > 5:
            return "critical"
        elif severity == "high" or affected_count > 2:
            return "high"
        else:
            return "medium"
    
    def _can_auto_fix_config(self, analysis: RootCauseAnalysis, context: dict) -> bool:
        """Determine if configuration can be automatically fixed."""
        # Only auto-fix if:
        # 1. High confidence
        # 2. Known safe configuration change
        # 3. Single merchant impact
        # 4. Not affecting checkout/payment
        
        if analysis.confidence < 0.8:
            return False
        
        if context.get("affects_checkout") or context.get("affects_payment"):
            return False
        
        affected_merchants = context.get("affected_merchants", [context.get("merchant_id")])
        if len(affected_merchants) > 1:
            return False
        
        # Check if it's a known safe config type
        safe_config_types = ["webhook_url", "api_timeout", "retry_count", "log_level"]
        affected_resource = context.get("affected_resource", "")
        
        return any(config_type in affected_resource.lower() for config_type in safe_config_types)
    
    def _generate_config_fix(self, analysis: RootCauseAnalysis, context: dict) -> dict:
        """Generate configuration fix parameters."""
        return {
            "resource": context.get("affected_resource"),
            "change_type": "update",
            "new_value": "auto_detected",  # Would be extracted from analysis
            "validation_rules": ["syntax_check", "connectivity_test"],
            "rollback_on_failure": True
        }
    
    def _build_risk_reasoning(
        self,
        risk_level: str,
        risk_factors: list[str],
        requires_approval: bool
    ) -> str:
        """Build risk assessment reasoning."""
        if not risk_factors:
            return f"Risk level: {risk_level}. No significant risk factors identified. Action can proceed automatically."
        
        factors_text = ", ".join(risk_factors)
        approval_text = "Requires human approval." if requires_approval else "Can proceed automatically."
        
        return f"Risk level: {risk_level}. Risk factors: {factors_text}. {approval_text}"


# Singleton instance
_decision_engine_instance: Optional[DecisionEngine] = None


def get_decision_engine() -> DecisionEngine:
    """Get singleton decision engine instance."""
    global _decision_engine_instance
    if _decision_engine_instance is None:
        _decision_engine_instance = DecisionEngine()
    return _decision_engine_instance
