"""
Explanation Generator for MigrationGuard AI.

This module generates human-readable explanations for system decisions,
including reasoning chains, uncertainty communication, and evidence references.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExplanationStep(BaseModel):
    """A single step in the reasoning chain."""
    
    stage: str = Field(..., description="Stage name (signals, patterns, root_cause, decision)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    summary: str = Field(..., description="Human-readable summary of this step")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured data for this step")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    uncertainty: Optional[str] = Field(None, description="Explanation of uncertainty if present")
    evidence_refs: List[str] = Field(default_factory=list, description="References to evidence (signal_ids, pattern_ids)")


class Explanation(BaseModel):
    """Complete explanation for a decision."""
    
    issue_id: str
    reasoning_chain: List[ExplanationStep] = Field(default_factory=list)
    alternatives_considered: List[Dict[str, Any]] = Field(default_factory=list)
    final_decision: str
    confidence_level: str  # "high", "medium", "low"
    uncertainty_factors: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExplanationGenerator:
    """Generates human-readable explanations for system decisions."""
    
    def __init__(self):
        """Initialize the explanation generator."""
        pass
    
    def create_signal_explanation(
        self,
        signals: List[Dict[str, Any]],
        confidence: float = 1.0
    ) -> ExplanationStep:
        """
        Create explanation for signal observation stage.
        
        Args:
            signals: List of signals observed
            confidence: Confidence in signal data (default 1.0)
            
        Returns:
            ExplanationStep for signal observation
        """
        signal_ids = [s.get("signal_id", "unknown") for s in signals]
        signal_sources = list(set(s.get("source", "unknown") for s in signals))
        
        if len(signals) == 1:
            signal = signals[0]
            summary = (
                f"Observed signal from {signal.get('source', 'unknown')} "
                f"for merchant {signal.get('merchant_id', 'unknown')}: "
                f"{signal.get('error_message', 'No error message')}"
            )
        else:
            summary = (
                f"Observed {len(signals)} signals from sources: {', '.join(signal_sources)}. "
                f"Signals indicate potential issues affecting merchant operations."
            )
        
        return ExplanationStep(
            stage="signals",
            summary=summary,
            data={
                "signal_count": len(signals),
                "sources": signal_sources,
                "signals": signals,
            },
            confidence=confidence,
            evidence_refs=signal_ids,
        )
    
    def create_pattern_explanation(
        self,
        patterns: List[Dict[str, Any]],
        confidence: float
    ) -> ExplanationStep:
        """
        Create explanation for pattern detection stage.
        
        Args:
            patterns: List of detected patterns
            confidence: Confidence in pattern detection
            
        Returns:
            ExplanationStep for pattern detection
        """
        pattern_ids = [p.get("pattern_id", "unknown") for p in patterns]
        
        if not patterns:
            summary = "No recurring patterns detected. This appears to be an isolated incident."
            uncertainty = "Without pattern data, root cause analysis relies solely on individual signal characteristics."
        elif len(patterns) == 1:
            pattern = patterns[0]
            affected_count = len(pattern.get("affected_merchants", []))
            summary = (
                f"Detected pattern '{pattern.get('description', 'Unknown pattern')}' "
                f"affecting {affected_count} merchant(s). "
                f"This pattern has occurred {pattern.get('occurrence_count', 0)} times."
            )
            uncertainty = None
        else:
            summary = (
                f"Detected {len(patterns)} related patterns, suggesting a systemic issue. "
                f"Multiple patterns indicate complex root cause requiring careful analysis."
            )
            uncertainty = "Multiple overlapping patterns increase analysis complexity."
        
        return ExplanationStep(
            stage="patterns",
            summary=summary,
            data={
                "pattern_count": len(patterns),
                "patterns": patterns,
            },
            confidence=confidence,
            uncertainty=uncertainty,
            evidence_refs=pattern_ids,
        )
    
    def create_root_cause_explanation(
        self,
        root_cause_analysis: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        confidence: float
    ) -> ExplanationStep:
        """
        Create explanation for root cause analysis stage.
        
        Args:
            root_cause_analysis: Root cause analysis results
            alternatives: Alternative hypotheses considered
            confidence: Confidence in root cause analysis
            
        Returns:
            ExplanationStep for root cause analysis
        """
        category = root_cause_analysis.get("category", "unknown")
        root_cause = root_cause_analysis.get("root_cause", "Unknown cause")
        explanation = root_cause_analysis.get("explanation", "")
        
        # Map categories to human-readable descriptions
        category_descriptions = {
            "migration_misstep": "a migration configuration issue",
            "platform_regression": "a platform bug or regression",
            "documentation_gap": "missing or unclear documentation",
            "merchant_config_error": "a merchant configuration error",
        }
        
        category_desc = category_descriptions.get(category, "an unknown issue type")
        
        summary = (
            f"Root cause identified as {category_desc}: {root_cause}. "
            f"{explanation}"
        )
        
        # Add uncertainty communication for low confidence
        uncertainty = None
        if confidence < 0.7:
            uncertainty = (
                f"Confidence is {confidence:.1%}, below the 70% threshold. "
                f"This analysis should be reviewed by a human operator. "
                f"Considered {len(alternatives)} alternative explanations."
            )
        elif confidence < 0.85:
            uncertainty = (
                f"Moderate confidence ({confidence:.1%}). "
                f"Alternative explanations were considered but deemed less likely."
            )
        
        return ExplanationStep(
            stage="root_cause",
            summary=summary,
            data={
                "category": category,
                "root_cause": root_cause,
                "explanation": explanation,
                "alternatives": alternatives,
            },
            confidence=confidence,
            uncertainty=uncertainty,
            evidence_refs=[],  # Root cause references the pattern/signal IDs from previous steps
        )
    
    def create_decision_explanation(
        self,
        decision: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        confidence: float
    ) -> ExplanationStep:
        """
        Create explanation for decision-making stage.
        
        Args:
            decision: Decision details
            risk_assessment: Risk assessment results
            confidence: Confidence in decision
            
        Returns:
            ExplanationStep for decision-making
        """
        action_type = decision.get("action_type", "unknown")
        risk_level = risk_assessment.get("risk_level", "unknown")
        requires_approval = risk_assessment.get("requires_approval", False)
        rationale = decision.get("rationale", "")
        
        # Map action types to human-readable descriptions
        action_descriptions = {
            "support_guidance": "provide support guidance",
            "proactive_communication": "send proactive communication to merchant",
            "engineering_escalation": "escalate to engineering team",
            "temporary_mitigation": "apply temporary mitigation",
            "documentation_update": "update documentation",
        }
        
        action_desc = action_descriptions.get(action_type, action_type)
        
        summary = (
            f"Decision: {action_desc}. "
            f"Risk level: {risk_level}. "
            f"{rationale}"
        )
        
        if requires_approval:
            summary += " This action requires human approval before execution."
        
        # Add uncertainty for approval requirements
        uncertainty = None
        if requires_approval:
            reasons = risk_assessment.get("approval_reasons", [])
            if reasons:
                uncertainty = f"Approval required due to: {', '.join(reasons)}"
        
        return ExplanationStep(
            stage="decision",
            summary=summary,
            data={
                "action_type": action_type,
                "risk_level": risk_level,
                "requires_approval": requires_approval,
                "rationale": rationale,
                "expected_outcome": decision.get("expected_outcome", ""),
            },
            confidence=confidence,
            uncertainty=uncertainty,
            evidence_refs=[],
        )
    
    def generate_explanation(
        self,
        issue_id: str,
        signals: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]],
        root_cause_analysis: Dict[str, Any],
        alternatives: List[Dict[str, Any]],
        decision: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        confidences: Dict[str, float]
    ) -> Explanation:
        """
        Generate complete explanation for a decision.
        
        Args:
            issue_id: Issue identifier
            signals: Observed signals
            patterns: Detected patterns
            root_cause_analysis: Root cause analysis results
            alternatives: Alternative hypotheses considered
            decision: Final decision
            risk_assessment: Risk assessment results
            confidences: Confidence scores for each stage
            
        Returns:
            Complete Explanation object
        """
        reasoning_chain = []
        
        # Add signal explanation
        signal_step = self.create_signal_explanation(
            signals,
            confidence=confidences.get("signals", 1.0)
        )
        reasoning_chain.append(signal_step)
        
        # Add pattern explanation
        pattern_step = self.create_pattern_explanation(
            patterns,
            confidence=confidences.get("patterns", 0.0)
        )
        reasoning_chain.append(pattern_step)
        
        # Add root cause explanation
        root_cause_step = self.create_root_cause_explanation(
            root_cause_analysis,
            alternatives,
            confidence=confidences.get("root_cause", 0.0)
        )
        reasoning_chain.append(root_cause_step)
        
        # Add decision explanation
        decision_step = self.create_decision_explanation(
            decision,
            risk_assessment,
            confidence=confidences.get("decision", 0.0)
        )
        reasoning_chain.append(decision_step)
        
        # Determine overall confidence level
        avg_confidence = sum(confidences.values()) / len(confidences) if confidences else 0.0
        if avg_confidence >= 0.85:
            confidence_level = "high"
        elif avg_confidence >= 0.70:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        # Collect uncertainty factors
        uncertainty_factors = []
        for step in reasoning_chain:
            if step.uncertainty:
                uncertainty_factors.append(f"{step.stage}: {step.uncertainty}")
        
        return Explanation(
            issue_id=issue_id,
            reasoning_chain=reasoning_chain,
            alternatives_considered=alternatives,
            final_decision=decision.get("action_type", "unknown"),
            confidence_level=confidence_level,
            uncertainty_factors=uncertainty_factors,
        )
    
    def format_explanation_text(self, explanation: Explanation) -> str:
        """
        Format explanation as human-readable text.
        
        Args:
            explanation: Explanation object
            
        Returns:
            Formatted text explanation
        """
        lines = []
        lines.append(f"# Explanation for Issue {explanation.issue_id}")
        lines.append(f"Generated at: {explanation.created_at.isoformat()}")
        lines.append(f"Overall Confidence: {explanation.confidence_level}")
        lines.append("")
        
        lines.append("## Reasoning Chain")
        for i, step in enumerate(explanation.reasoning_chain, 1):
            lines.append(f"\n### {i}. {step.stage.replace('_', ' ').title()}")
            lines.append(f"**Time:** {step.timestamp.isoformat()}")
            if step.confidence is not None:
                lines.append(f"**Confidence:** {step.confidence:.1%}")
            lines.append(f"\n{step.summary}")
            
            if step.uncertainty:
                lines.append(f"\n⚠️ **Uncertainty:** {step.uncertainty}")
            
            if step.evidence_refs:
                lines.append(f"\n**Evidence:** {', '.join(step.evidence_refs)}")
        
        if explanation.alternatives_considered:
            lines.append("\n## Alternatives Considered")
            for alt in explanation.alternatives_considered:
                lines.append(f"- {alt.get('description', 'Unknown alternative')}")
                if "reason_rejected" in alt:
                    lines.append(f"  Rejected because: {alt['reason_rejected']}")
        
        if explanation.uncertainty_factors:
            lines.append("\n## Uncertainty Factors")
            for factor in explanation.uncertainty_factors:
                lines.append(f"- {factor}")
        
        lines.append(f"\n## Final Decision")
        lines.append(f"Action: {explanation.final_decision}")
        
        return "\n".join(lines)
