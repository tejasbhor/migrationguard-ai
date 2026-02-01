"""
Agent State Schema for LangGraph.

This module defines the state structure for the MigrationGuard AI agent loop,
including all fields needed to track issue resolution progress through the
observe-reason-decide-act cycle.
"""

from typing import Annotated, Literal, Optional, TypedDict
from operator import add

from migrationguard_ai.core.schemas import Signal, Pattern, RootCauseAnalysis, Action, ActionResult
from migrationguard_ai.services.explanation_generator import Explanation


def add_messages(existing: list, new: list) -> list:
    """Reducer function for adding messages to a list."""
    return existing + new


class AgentState(TypedDict):
    """
    State schema for the agent loop.
    
    This TypedDict defines all fields needed to track an issue through the
    observe-reason-decide-act cycle. Fields with Annotated types use reducer
    functions to merge state updates.
    """
    
    # Input signals
    signals: Annotated[list[Signal], add_messages]
    
    # Detected patterns
    patterns: list[Pattern]
    
    # Analysis results
    root_cause: Optional[RootCauseAnalysis]
    confidence: float
    
    # Decision
    selected_action: Optional[Action]
    risk_level: Literal["low", "medium", "high", "critical"]
    
    # Execution
    action_result: Optional[ActionResult]
    
    # Metadata
    issue_id: str
    merchant_id: str
    stage: Literal["observe", "detect_patterns", "analyze", "decide", "assess_risk", 
                   "wait_approval", "execute", "record", "complete"]
    requires_approval: bool
    approval_status: Optional[Literal["pending", "approved", "rejected"]]
    
    # Reasoning chain for explainability
    reasoning_chain: Annotated[list[str], add_messages]
    
    # Complete explanation object (stored for audit trail)
    explanation: Optional[Explanation]
    
    # Error handling
    error_count: Annotated[int, add]
    last_error: Optional[str]
    
    # Timestamps
    created_at: str
    updated_at: str


def create_initial_state(issue_id: str, merchant_id: str, initial_signal: Signal) -> AgentState:
    """
    Create initial agent state for a new issue.
    
    Args:
        issue_id: Unique identifier for the issue
        merchant_id: Merchant identifier
        initial_signal: First signal that triggered the issue
        
    Returns:
        Initial agent state
    """
    from datetime import datetime
    
    now = datetime.utcnow().isoformat()
    
    return AgentState(
        signals=[initial_signal],
        patterns=[],
        root_cause=None,
        confidence=0.0,
        selected_action=None,
        risk_level="low",
        action_result=None,
        issue_id=issue_id,
        merchant_id=merchant_id,
        stage="observe",
        requires_approval=False,
        approval_status=None,
        reasoning_chain=[],
        explanation=None,
        error_count=0,
        last_error=None,
        created_at=now,
        updated_at=now
    )


def validate_state_transition(
    current_stage: str,
    next_stage: str
) -> bool:
    """
    Validate that a state transition is allowed.
    
    Args:
        current_stage: Current stage
        next_stage: Proposed next stage
        
    Returns:
        True if transition is valid, False otherwise
    """
    # Define valid transitions
    valid_transitions = {
        "observe": ["detect_patterns"],
        "detect_patterns": ["analyze"],
        "analyze": ["decide"],
        "decide": ["assess_risk"],
        "assess_risk": ["wait_approval", "execute"],
        "wait_approval": ["execute", "complete"],  # Can execute after approval or reject
        "execute": ["record"],
        "record": ["complete"],
        "complete": []  # Terminal state
    }
    
    allowed_next_stages = valid_transitions.get(current_stage, [])
    return next_stage in allowed_next_stages


def update_state_stage(state: AgentState, new_stage: str) -> AgentState:
    """
    Update the state stage with validation.
    
    Args:
        state: Current state
        new_stage: New stage to transition to
        
    Returns:
        Updated state
        
    Raises:
        ValueError: If transition is invalid
    """
    from datetime import datetime
    
    if not validate_state_transition(state["stage"], new_stage):
        raise ValueError(
            f"Invalid state transition from {state['stage']} to {new_stage}"
        )
    
    state["stage"] = new_stage
    state["updated_at"] = datetime.utcnow().isoformat()
    
    return state
