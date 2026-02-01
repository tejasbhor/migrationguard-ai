"""
Agent Loop Orchestrator for MigrationGuard AI.

This module implements the main orchestrator that consumes signals from Kafka,
manages agent state, and executes the agent graph for each issue.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime

from migrationguard_ai.agent.agent_state import AgentState, create_initial_state
from migrationguard_ai.agent.agent_graph import get_agent_graph
from migrationguard_ai.agent.state_persistence import StatePersistence
from migrationguard_ai.services.kafka_consumer import KafkaConsumerWrapper
from migrationguard_ai.core.schemas import Signal
from migrationguard_ai.core.config import get_settings


logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the agent loop for processing signals and resolving issues.
    
    Responsibilities:
    - Consume signals from Kafka
    - Create or resume agent state for each issue
    - Execute agent graph for signal processing
    - Handle errors and state transitions
    - Manage approval workflows
    """
    
    def __init__(
        self,
        kafka_consumer: KafkaConsumerWrapper,
        state_persistence: StatePersistence
    ):
        """
        Initialize the orchestrator.
        
        Args:
            kafka_consumer: Kafka consumer for signal ingestion
            state_persistence: State persistence handler
        """
        self.kafka_consumer = kafka_consumer
        self.state_persistence = state_persistence
        self.agent_graph = get_agent_graph()
        self.settings = get_settings()
        self.running = False
        self.active_issues: dict[str, AgentState] = {}
    
    async def start(self) -> None:
        """
        Start the orchestrator main loop.
        
        This method runs continuously, consuming signals and processing issues.
        """
        self.running = True
        logger.info("Agent orchestrator starting...")
        
        # Resume any active issues from database
        await self._resume_active_issues()
        
        # Start main processing loop
        try:
            await self._main_loop()
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            raise
        finally:
            await self.stop()
    
    async def stop(self) -> None:
        """Stop the orchestrator gracefully."""
        logger.info("Agent orchestrator stopping...")
        self.running = False
        
        # Save all active states
        for issue_id, state in self.active_issues.items():
            await self.state_persistence.save_state(state)
        
        await self.kafka_consumer.close()
        logger.info("Agent orchestrator stopped")
    
    async def _main_loop(self) -> None:
        """Main processing loop."""
        while self.running:
            try:
                # Consume signals from Kafka
                messages = await self.kafka_consumer.consume(
                    timeout_ms=1000,
                    max_messages=10
                )
                
                for message in messages:
                    await self._process_signal(message)
                
                # Process issues waiting for approval
                await self._process_approval_queue()
                
                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Back off on error
    
    async def _process_signal(self, message: dict) -> None:
        """
        Process a single signal from Kafka.
        
        Args:
            message: Kafka message containing signal data
        """
        try:
            # Parse signal
            signal = Signal(**message)
            
            # Determine issue ID (group signals by merchant for now)
            issue_id = f"issue_{signal.merchant_id}_{signal.source}"
            
            # Get or create agent state
            state = await self._get_or_create_state(issue_id, signal)
            
            # Add signal to state if not already present
            if signal.signal_id not in [s.signal_id for s in state["signals"]]:
                state["signals"].append(signal)
            
            # Execute agent graph
            await self._execute_agent_graph(state)
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}", exc_info=True)
    
    async def _get_or_create_state(
        self,
        issue_id: str,
        signal: Signal
    ) -> AgentState:
        """
        Get existing state or create new one.
        
        Args:
            issue_id: Issue identifier
            signal: Initial signal
            
        Returns:
            Agent state
        """
        # Check in-memory cache
        if issue_id in self.active_issues:
            return self.active_issues[issue_id]
        
        # Try to load from database
        state = await self.state_persistence.load_state(issue_id)
        
        if state is None:
            # Create new state
            state = create_initial_state(
                issue_id=issue_id,
                merchant_id=signal.merchant_id,
                initial_signal=signal
            )
            logger.info(f"Created new issue: {issue_id}")
        else:
            logger.info(f"Resumed issue: {issue_id} at stage {state['stage']}")
        
        # Cache in memory
        self.active_issues[issue_id] = state
        
        return state
    
    async def _execute_agent_graph(self, state: AgentState) -> None:
        """
        Execute the agent graph for the given state.
        
        Args:
            state: Agent state to process
        """
        try:
            # Skip if waiting for approval
            if state["stage"] == "wait_approval" and state["approval_status"] == "pending":
                logger.info(f"Issue {state['issue_id']} waiting for approval")
                return
            
            # Skip if already complete
            if state["stage"] == "complete":
                logger.info(f"Issue {state['issue_id']} already complete")
                return
            
            # Execute graph
            logger.info(f"Executing agent graph for issue {state['issue_id']} at stage {state['stage']}")
            
            # In a real implementation, we would use LangGraph's invoke method
            # For now, we'll manually execute nodes based on current stage
            result_state = await self._execute_current_stage(state)
            
            # Update state
            self.active_issues[state["issue_id"]] = result_state
            
            # Save state to database
            await self.state_persistence.save_state(result_state)
            
            logger.info(f"Issue {state['issue_id']} progressed to stage {result_state['stage']}")
            
        except Exception as e:
            logger.error(f"Error executing agent graph: {e}", exc_info=True)
            state["error_count"] += 1
            state["last_error"] = str(e)
            await self.state_persistence.save_state(state)
    
    async def _execute_current_stage(self, state: AgentState) -> AgentState:
        """
        Execute the current stage of the agent graph.
        
        Args:
            state: Current state
            
        Returns:
            Updated state
        """
        from migrationguard_ai.agent.agent_graph import (
            observe_node,
            detect_patterns_node,
            analyze_root_cause_node,
            make_decision_node,
            assess_risk_node,
            execute_action_node,
            record_outcome_node
        )
        
        stage_handlers = {
            "observe": observe_node,
            "detect_patterns": detect_patterns_node,
            "analyze": analyze_root_cause_node,
            "decide": make_decision_node,
            "assess_risk": assess_risk_node,
            "execute": execute_action_node,
            "record": record_outcome_node
        }
        
        handler = stage_handlers.get(state["stage"])
        if handler:
            return await handler(state)
        else:
            logger.warning(f"No handler for stage: {state['stage']}")
            return state
    
    async def _process_approval_queue(self) -> None:
        """
        Process issues waiting for approval.
        
        This method checks for approved/rejected issues and continues execution.
        """
        for issue_id, state in list(self.active_issues.items()):
            if state["stage"] == "wait_approval":
                # Check if approval status has changed
                # In a real implementation, this would query the approval system
                
                if state["approval_status"] == "approved":
                    logger.info(f"Issue {issue_id} approved, continuing execution")
                    await self._execute_agent_graph(state)
                elif state["approval_status"] == "rejected":
                    logger.info(f"Issue {issue_id} rejected, marking complete")
                    state["stage"] = "complete"
                    await self.state_persistence.save_state(state)
    
    async def _resume_active_issues(self) -> None:
        """Resume processing of active issues from database."""
        try:
            active_issue_ids = await self.state_persistence.get_active_issues()
            
            logger.info(f"Resuming {len(active_issue_ids)} active issues")
            
            for issue_id in active_issue_ids:
                state = await self.state_persistence.load_state(issue_id)
                if state:
                    self.active_issues[issue_id] = state
                    logger.info(f"Resumed issue {issue_id} at stage {state['stage']}")
            
        except Exception as e:
            logger.error(f"Error resuming active issues: {e}", exc_info=True)
    
    async def approve_action(self, issue_id: str, approved: bool) -> None:
        """
        Approve or reject an action for an issue.
        
        Args:
            issue_id: Issue identifier
            approved: Whether the action is approved
        """
        state = self.active_issues.get(issue_id)
        
        if state is None:
            state = await self.state_persistence.load_state(issue_id)
        
        if state is None:
            raise ValueError(f"Issue not found: {issue_id}")
        
        if state["stage"] != "wait_approval":
            raise ValueError(f"Issue {issue_id} is not waiting for approval")
        
        # Update approval status
        state["approval_status"] = "approved" if approved else "rejected"
        
        # Save state
        await self.state_persistence.save_state(state)
        
        logger.info(f"Issue {issue_id} {'approved' if approved else 'rejected'}")


async def create_orchestrator(
    kafka_consumer: KafkaConsumerWrapper,
    state_persistence: StatePersistence
) -> AgentOrchestrator:
    """
    Factory function to create orchestrator instance.
    
    Args:
        kafka_consumer: Kafka consumer
        state_persistence: State persistence handler
        
    Returns:
        Agent orchestrator instance
    """
    return AgentOrchestrator(kafka_consumer, state_persistence)
