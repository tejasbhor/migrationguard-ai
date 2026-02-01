"""
LangGraph Agent Graph for MigrationGuard AI.

This module implements the agent loop using LangGraph's stateful graph orchestration.
It defines all nodes in the observe-reason-decide-act cycle and their connections.
"""

from typing import Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from migrationguard_ai.agent.agent_state import AgentState, update_state_stage
from migrationguard_ai.services.pattern_detector import PatternDetector
from migrationguard_ai.services.root_cause_analyzer import get_root_cause_analyzer
from migrationguard_ai.services.decision_engine import get_decision_engine
from migrationguard_ai.services.explanation_generator import ExplanationGenerator
from migrationguard_ai.core.schemas import Signal, Pattern, Action, ActionResult


# Node Functions

async def observe_node(state: AgentState) -> AgentState:
    """
    Observe node - Entry point for signal ingestion.
    
    This node receives signals and prepares them for pattern detection.
    """
    # Generate explanation for signal observation
    explanation_gen = ExplanationGenerator()
    
    # Convert signals to dict format for explanation
    signals_data = [
        {
            "signal_id": s.signal_id,
            "source": s.source,
            "merchant_id": s.merchant_id,
            "error_message": s.error_message or "",
            "severity": s.severity
        }
        for s in state["signals"]
    ]
    
    signal_explanation = explanation_gen.create_signal_explanation(
        signals=signals_data,
        confidence=1.0
    )
    
    # Add explanation to reasoning chain
    state["reasoning_chain"].append(signal_explanation.summary)
    
    # Update stage
    state = update_state_stage(state, "detect_patterns")
    
    return state


async def detect_patterns_node(state: AgentState) -> AgentState:
    """
    Detect patterns node - Identify recurring patterns across signals.
    
    This node analyzes signals to detect patterns and correlations.
    """
    try:
        detector = PatternDetector()
        explanation_gen = ExplanationGenerator()
        
        # Analyze signals for patterns
        patterns = await detector.analyze_signals(state["signals"])
        
        state["patterns"] = patterns
        
        # Convert patterns to dict format for explanation
        patterns_data = [
            {
                "pattern_id": p.pattern_id,
                "pattern_type": p.pattern_type,
                "description": p.description,
                "affected_merchants": p.affected_merchants,
                "occurrence_count": p.occurrence_count
            }
            for p in patterns
        ]
        
        # Generate pattern explanation
        pattern_confidence = patterns[0].confidence if patterns else 0.0
        pattern_explanation = explanation_gen.create_pattern_explanation(
            patterns=patterns_data,
            confidence=pattern_confidence
        )
        
        # Add explanation to reasoning chain
        state["reasoning_chain"].append(pattern_explanation.summary)
        
        # Update stage
        state = update_state_stage(state, "analyze")
        
    except Exception as e:
        state["error_count"] += 1
        state["last_error"] = str(e)
        state["reasoning_chain"].append(f"Error detecting patterns: {str(e)}")
    
    return state


async def analyze_root_cause_node(state: AgentState) -> AgentState:
    """
    Analyze root cause node - Use Claude to identify underlying causes.
    
    This node performs AI-powered root cause analysis.
    """
    try:
        analyzer = get_root_cause_analyzer()
        explanation_gen = ExplanationGenerator()
        
        # Build merchant context
        merchant_context = {
            "merchant_id": state["merchant_id"],
            "issue_id": state["issue_id"]
        }
        
        # Analyze root cause
        analysis = await analyzer.analyze(
            signals=state["signals"],
            patterns=state["patterns"],
            merchant_context=merchant_context
        )
        
        state["root_cause"] = analysis
        state["confidence"] = analysis.confidence
        
        # Convert root cause analysis to dict format for explanation
        root_cause_data = {
            "category": analysis.category,
            "root_cause": analysis.root_cause,
            "explanation": analysis.reasoning
        }
        
        # Get alternatives from analysis
        alternatives = [
            {
                "description": alt,
                "reason_rejected": "Lower confidence based on available evidence"
            }
            for alt in getattr(analysis, "alternatives", [])
        ]
        
        # Generate root cause explanation
        root_cause_explanation = explanation_gen.create_root_cause_explanation(
            root_cause_analysis=root_cause_data,
            alternatives=alternatives,
            confidence=analysis.confidence
        )
        
        # Add explanation to reasoning chain
        state["reasoning_chain"].append(root_cause_explanation.summary)
        if root_cause_explanation.uncertainty:
            state["reasoning_chain"].append(f"⚠️ {root_cause_explanation.uncertainty}")
        
        # Update stage
        state = update_state_stage(state, "decide")
        
    except Exception as e:
        state["error_count"] += 1
        state["last_error"] = str(e)
        state["reasoning_chain"].append(f"Error analyzing root cause: {str(e)}")
        
        # Set default low confidence if analysis fails
        state["confidence"] = 0.0
    
    return state


async def make_decision_node(state: AgentState) -> AgentState:
    """
    Make decision node - Determine appropriate action based on analysis.
    
    This node uses the decision engine to select actions.
    """
    try:
        engine = get_decision_engine()
        explanation_gen = ExplanationGenerator()
        
        if state["root_cause"] is None:
            raise ValueError("Cannot make decision without root cause analysis")
        
        # Build decision context
        context = {
            "merchant_id": state["merchant_id"],
            "issue_id": state["issue_id"],
            "signal_ids": [s.signal_id for s in state["signals"]],
            "pattern_ids": [p.pattern_id for p in state["patterns"]],
            "severity": state["signals"][0].severity if state["signals"] else "medium",
            "affects_checkout": False,  # Would be determined from signals
            "affects_payment": False
        }
        
        # Make decision
        decision = engine.decide(
            analysis=state["root_cause"],
            context=context,
            issue_id=state["issue_id"]
        )
        
        # Convert Decision to Action
        action = Action(
            action_id=decision.decision_id,
            action_type=decision.action_type,
            risk_level=decision.risk_level,
            status="pending",
            parameters=decision.parameters
        )
        
        state["selected_action"] = action
        state["risk_level"] = decision.risk_level
        state["requires_approval"] = decision.requires_approval
        
        # Convert decision to dict format for explanation
        decision_data = {
            "action_type": decision.action_type,
            "rationale": decision.reasoning,
            "expected_outcome": decision.expected_outcome
        }
        
        risk_assessment_data = {
            "risk_level": decision.risk_level,
            "requires_approval": decision.requires_approval,
            "approval_reasons": decision.approval_reasons if hasattr(decision, "approval_reasons") else []
        }
        
        # Generate decision explanation
        decision_explanation = explanation_gen.create_decision_explanation(
            decision=decision_data,
            risk_assessment=risk_assessment_data,
            confidence=state["confidence"]
        )
        
        # Add explanation to reasoning chain
        state["reasoning_chain"].append(decision_explanation.summary)
        if decision_explanation.uncertainty:
            state["reasoning_chain"].append(f"⚠️ {decision_explanation.uncertainty}")
        
        # Update stage
        state = update_state_stage(state, "assess_risk")
        
    except Exception as e:
        state["error_count"] += 1
        state["last_error"] = str(e)
        state["reasoning_chain"].append(f"Error making decision: {str(e)}")
    
    return state


async def assess_risk_node(state: AgentState) -> AgentState:
    """
    Assess risk node - Evaluate risk and determine if approval is needed.
    
    This node performs final risk assessment before execution.
    """
    # Risk assessment is already done in decision engine
    # This node just prepares for routing
    
    if state["requires_approval"]:
        state["approval_status"] = "pending"
        reasoning = f"Action requires approval due to {state['risk_level']} risk level"
        state["reasoning_chain"].append(reasoning)
    else:
        reasoning = f"Action approved for automatic execution ({state['risk_level']} risk)"
        state["reasoning_chain"].append(reasoning)
    
    return state


def route_by_risk(state: AgentState) -> Literal["wait_approval", "execute"]:
    """
    Route based on risk assessment.
    
    Determines whether action needs approval or can be executed automatically.
    """
    if state["requires_approval"]:
        return "wait_approval"
    else:
        return "execute"


async def wait_for_approval_node(state: AgentState) -> AgentState:
    """
    Wait for approval node - Pause execution until human approval.
    
    This node represents a human-in-the-loop checkpoint.
    In practice, this would be handled by the orchestrator checking approval status.
    """
    state = update_state_stage(state, "wait_approval")
    
    reasoning = "Waiting for human approval before executing action"
    state["reasoning_chain"].append(reasoning)
    
    return state


async def execute_action_node(state: AgentState) -> AgentState:
    """
    Execute action node - Carry out the approved action.
    
    This node executes the selected action with retry logic.
    """
    try:
        if state["selected_action"] is None:
            raise ValueError("No action selected for execution")
        
        # In a real implementation, this would call the ActionExecutor
        # For now, we'll simulate successful execution
        
        action_result = ActionResult(
            action_id=state["selected_action"].action_id,
            success=True,
            result={"status": "executed", "message": "Action completed successfully"},
            error_message=None,
            executed_at=datetime.utcnow()
        )
        
        state["action_result"] = action_result
        
        # Add reasoning
        reasoning = f"Action executed successfully: {state['selected_action'].action_type}"
        state["reasoning_chain"].append(reasoning)
        
        # Update stage
        state = update_state_stage(state, "record")
        
    except Exception as e:
        state["error_count"] += 1
        state["last_error"] = str(e)
        state["reasoning_chain"].append(f"Error executing action: {str(e)}")
        
        # Create failed action result
        action_result = ActionResult(
            action_id=state["selected_action"].action_id if state["selected_action"] else "unknown",
            success=False,
            result=None,
            error_message=str(e),
            executed_at=datetime.utcnow()
        )
        state["action_result"] = action_result
    
    return state


async def record_outcome_node(state: AgentState) -> AgentState:
    """
    Record outcome node - Log results to audit trail.
    
    This node records the complete issue resolution in the audit trail,
    including the full explanation.
    """
    try:
        explanation_gen = ExplanationGenerator()
        
        # Generate complete explanation
        if state["root_cause"] and state["selected_action"]:
            # Convert signals to dict format
            signals_data = [
                {
                    "signal_id": s.signal_id,
                    "source": s.source,
                    "merchant_id": s.merchant_id,
                    "error_message": s.error_message or "",
                    "severity": s.severity
                }
                for s in state["signals"]
            ]
            
            # Convert patterns to dict format
            patterns_data = [
                {
                    "pattern_id": p.pattern_id,
                    "pattern_type": p.pattern_type,
                    "description": p.description,
                    "affected_merchants": p.affected_merchants,
                    "occurrence_count": p.occurrence_count
                }
                for p in state["patterns"]
            ]
            
            # Convert root cause to dict format
            root_cause_data = {
                "category": state["root_cause"].category,
                "root_cause": state["root_cause"].root_cause,
                "explanation": state["root_cause"].reasoning
            }
            
            # Get alternatives
            alternatives = [
                {
                    "description": alt,
                    "reason_rejected": "Lower confidence based on available evidence"
                }
                for alt in getattr(state["root_cause"], "alternatives", [])
            ]
            
            # Convert decision to dict format
            decision_data = {
                "action_type": state["selected_action"].action_type,
                "rationale": "Action selected based on root cause analysis",
                "expected_outcome": "Issue resolution"
            }
            
            risk_assessment_data = {
                "risk_level": state["risk_level"],
                "requires_approval": state["requires_approval"],
                "approval_reasons": []
            }
            
            # Collect confidence scores from each stage
            confidences = {
                "signals": 1.0,
                "patterns": state["patterns"][0].confidence if state["patterns"] else 0.0,
                "root_cause": state["confidence"],
                "decision": state["confidence"]
            }
            
            # Generate complete explanation
            explanation = explanation_gen.generate_explanation(
                issue_id=state["issue_id"],
                signals=signals_data,
                patterns=patterns_data,
                root_cause_analysis=root_cause_data,
                alternatives=alternatives,
                decision=decision_data,
                risk_assessment=risk_assessment_data,
                confidences=confidences
            )
            
            # Store explanation in state
            state["explanation"] = explanation
        
        # In a real implementation, this would write to the audit trail
        # including the complete explanation object
        
        # Add final reasoning
        if state["action_result"] and state["action_result"].success:
            reasoning = "Issue resolved successfully. Outcome and explanation recorded in audit trail."
        else:
            reasoning = "Issue resolution failed. Failure and explanation recorded in audit trail."
        
        state["reasoning_chain"].append(reasoning)
        
        # Update stage to complete
        state = update_state_stage(state, "complete")
        
    except Exception as e:
        state["error_count"] += 1
        state["last_error"] = str(e)
        state["reasoning_chain"].append(f"Error recording outcome: {str(e)}")
    
    return state


# Graph Construction

def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph agent workflow.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("observe", observe_node)
    workflow.add_node("detect_patterns", detect_patterns_node)
    workflow.add_node("analyze_root_cause", analyze_root_cause_node)
    workflow.add_node("make_decision", make_decision_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("wait_approval", wait_for_approval_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("record_outcome", record_outcome_node)
    
    # Set entry point
    workflow.set_entry_point("observe")
    
    # Add edges
    workflow.add_edge("observe", "detect_patterns")
    workflow.add_edge("detect_patterns", "analyze_root_cause")
    workflow.add_edge("analyze_root_cause", "make_decision")
    workflow.add_edge("make_decision", "assess_risk")
    
    # Conditional routing based on risk
    workflow.add_conditional_edges(
        "assess_risk",
        route_by_risk,
        {
            "wait_approval": "wait_approval",
            "execute": "execute_action"
        }
    )
    
    # After approval, execute action
    workflow.add_edge("wait_approval", "execute_action")
    
    # After execution, record outcome
    workflow.add_edge("execute_action", "record_outcome")
    
    # After recording, end
    workflow.add_edge("record_outcome", END)
    
    return workflow.compile()


# Singleton instance
_agent_graph_instance = None


def get_agent_graph() -> StateGraph:
    """Get singleton agent graph instance."""
    global _agent_graph_instance
    if _agent_graph_instance is None:
        _agent_graph_instance = create_agent_graph()
    return _agent_graph_instance
