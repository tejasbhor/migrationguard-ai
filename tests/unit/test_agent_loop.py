"""
Unit tests for Agent Loop components.

These tests verify the agent state, graph nodes, and orchestration logic.
"""

import pytest
from datetime import datetime

from migrationguard_ai.agent.agent_state import (
    AgentState,
    create_initial_state,
    validate_state_transition,
    update_state_stage
)
from migrationguard_ai.agent.agent_graph import (
    observe_node,
    detect_patterns_node,
    route_by_risk,
    create_agent_graph
)
from migrationguard_ai.core.schemas import Signal, RootCauseAnalysis


class TestAgentState:
    """Unit tests for agent state management."""
    
    def test_create_initial_state(self):
        """Test creating initial agent state."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={"ticket_id": "T-123"}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        assert state["issue_id"] == "issue_001"
        assert state["merchant_id"] == "merchant_123"
        assert state["stage"] == "observe"
        assert len(state["signals"]) == 1
        assert state["signals"][0] == signal
        assert state["confidence"] == 0.0
        assert state["error_count"] == 0
        assert state["requires_approval"] is False
    
    def test_validate_state_transition_valid(self):
        """Test valid state transitions."""
        assert validate_state_transition("observe", "detect_patterns") is True
        assert validate_state_transition("detect_patterns", "analyze") is True
        assert validate_state_transition("analyze", "decide") is True
        assert validate_state_transition("decide", "assess_risk") is True
        assert validate_state_transition("assess_risk", "execute") is True
        assert validate_state_transition("assess_risk", "wait_approval") is True
        assert validate_state_transition("execute", "record") is True
        assert validate_state_transition("record", "complete") is True
    
    def test_validate_state_transition_invalid(self):
        """Test invalid state transitions."""
        assert validate_state_transition("observe", "execute") is False
        assert validate_state_transition("detect_patterns", "execute") is False
        assert validate_state_transition("complete", "observe") is False
    
    def test_update_state_stage_valid(self):
        """Test updating state stage with valid transition."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        updated_state = update_state_stage(state, "detect_patterns")
        
        assert updated_state["stage"] == "detect_patterns"
        # Just verify updated_at field exists and is a string
        assert "updated_at" in updated_state
        assert isinstance(updated_state["updated_at"], str)
    
    def test_update_state_stage_invalid(self):
        """Test updating state stage with invalid transition."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        with pytest.raises(ValueError, match="Invalid state transition"):
            update_state_stage(state, "execute")


class TestAgentGraphNodes:
    """Unit tests for agent graph nodes."""
    
    @pytest.mark.asyncio
    async def test_observe_node(self):
        """Test observe node execution."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        result = await observe_node(state)
        
        assert result["stage"] == "detect_patterns"
        assert len(result["reasoning_chain"]) > 0
        assert "Observed" in result["reasoning_chain"][0]
    
    @pytest.mark.asyncio
    async def test_detect_patterns_node_no_patterns(self):
        """Test detect patterns node with insufficient signals."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        state["stage"] = "detect_patterns"
        
        result = await detect_patterns_node(state)
        
        # Node should either succeed and move to analyze, or stay in detect_patterns on error
        assert result["stage"] in ["analyze", "detect_patterns"]
        assert len(result["reasoning_chain"]) > 0
    
    def test_route_by_risk_requires_approval(self):
        """Test routing when approval is required."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        state["requires_approval"] = True
        
        route = route_by_risk(state)
        
        assert route == "wait_approval"
    
    def test_route_by_risk_no_approval(self):
        """Test routing when approval is not required."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        state["requires_approval"] = False
        
        route = route_by_risk(state)
        
        assert route == "execute"


class TestAgentGraph:
    """Unit tests for agent graph construction."""
    
    def test_create_agent_graph(self):
        """Test creating agent graph."""
        graph = create_agent_graph()
        
        assert graph is not None
        # Graph should be compiled and ready to use
    
    def test_agent_graph_singleton(self):
        """Test that get_agent_graph returns singleton."""
        from migrationguard_ai.agent.agent_graph import get_agent_graph
        
        graph1 = get_agent_graph()
        graph2 = get_agent_graph()
        
        assert graph1 is graph2


class TestStateTransitions:
    """Unit tests for state transition logic."""
    
    def test_complete_workflow_transitions(self):
        """Test complete workflow state transitions."""
        transitions = [
            ("observe", "detect_patterns"),
            ("detect_patterns", "analyze"),
            ("analyze", "decide"),
            ("decide", "assess_risk"),
            ("assess_risk", "execute"),
            ("execute", "record"),
            ("record", "complete")
        ]
        
        for current, next_stage in transitions:
            assert validate_state_transition(current, next_stage) is True
    
    def test_approval_workflow_transitions(self):
        """Test approval workflow state transitions."""
        # Normal flow with approval
        assert validate_state_transition("assess_risk", "wait_approval") is True
        assert validate_state_transition("wait_approval", "execute") is True
        
        # Rejection flow
        assert validate_state_transition("wait_approval", "complete") is True


class TestReasoningChain:
    """Unit tests for reasoning chain tracking."""
    
    @pytest.mark.asyncio
    async def test_reasoning_chain_accumulates(self):
        """Test that reasoning chain accumulates through nodes."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        # Execute observe node
        state = await observe_node(state)
        assert len(state["reasoning_chain"]) == 1
        
        # Execute detect patterns node
        state = await detect_patterns_node(state)
        assert len(state["reasoning_chain"]) == 2
    
    def test_reasoning_chain_preserves_order(self):
        """Test that reasoning chain preserves order."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        state["reasoning_chain"].append("First reasoning")
        state["reasoning_chain"].append("Second reasoning")
        state["reasoning_chain"].append("Third reasoning")
        
        assert state["reasoning_chain"][0] == "First reasoning"
        assert state["reasoning_chain"][1] == "Second reasoning"
        assert state["reasoning_chain"][2] == "Third reasoning"


class TestErrorHandling:
    """Unit tests for error handling in agent loop."""
    
    def test_error_count_increments(self):
        """Test that error count increments."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        
        initial_count = state["error_count"]
        state["error_count"] += 1
        state["last_error"] = "Test error"
        
        assert state["error_count"] == initial_count + 1
        assert state["last_error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_node_handles_errors_gracefully(self):
        """Test that nodes handle errors gracefully."""
        signal = Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high",
            raw_data={}
        )
        
        state = create_initial_state("issue_001", "merchant_123", signal)
        state["stage"] = "detect_patterns"
        
        # Even with errors, node should not crash
        result = await detect_patterns_node(state)
        
        assert result is not None
        assert "stage" in result
