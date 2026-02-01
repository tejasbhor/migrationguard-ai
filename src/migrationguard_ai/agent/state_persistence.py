"""
State Persistence for LangGraph Agent.

This module implements PostgreSQL-based state persistence for the agent loop,
allowing state to be saved and resumed across restarts.
"""

import json
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from migrationguard_ai.agent.agent_state import AgentState
from migrationguard_ai.db.models.agent_state import AgentStateModel
from migrationguard_ai.core.schemas import Signal, Pattern, RootCauseAnalysis, Action, ActionResult


class StatePersistence:
    """
    Handles saving and loading agent state to/from PostgreSQL.
    
    Implements LangGraph checkpointing interface for state persistence.
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize state persistence.
        
        Args:
            db_session: Database session for persistence operations
        """
        self.db_session = db_session
    
    async def save_state(self, state: AgentState) -> None:
        """
        Save agent state to database.
        
        Args:
            state: Agent state to save
        """
        # Serialize complex objects to JSON
        state_data = self._serialize_state(state)
        
        # Check if state already exists
        result = await self.db_session.execute(
            select(AgentStateModel).where(
                AgentStateModel.issue_id == state["issue_id"]
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing state
            await self.db_session.execute(
                update(AgentStateModel)
                .where(AgentStateModel.issue_id == state["issue_id"])
                .values(
                    stage=state["stage"],
                    state_data=state_data,
                    updated_at=datetime.utcnow()
                )
            )
        else:
            # Create new state
            new_state = AgentStateModel(
                issue_id=state["issue_id"],
                stage=state["stage"],
                state_data=state_data
            )
            self.db_session.add(new_state)
        
        await self.db_session.commit()
    
    async def load_state(self, issue_id: str) -> Optional[AgentState]:
        """
        Load agent state from database.
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Agent state if found, None otherwise
        """
        result = await self.db_session.execute(
            select(AgentStateModel).where(
                AgentStateModel.issue_id == issue_id
            )
        )
        state_model = result.scalar_one_or_none()
        
        if state_model is None:
            return None
        
        # Deserialize state data
        state = self._deserialize_state(state_model.state_data)
        
        return state
    
    async def get_active_issues(self) -> list[str]:
        """
        Get list of active issue IDs that need processing.
        
        Returns:
            List of issue IDs in non-terminal stages
        """
        result = await self.db_session.execute(
            select(AgentStateModel.issue_id).where(
                AgentStateModel.stage.in_([
                    "observe", "detect_patterns", "analyze", "decide",
                    "assess_risk", "wait_approval", "execute", "record"
                ])
            )
        )
        
        return [row[0] for row in result.all()]
    
    def _serialize_state(self, state: AgentState) -> dict:
        """
        Serialize agent state to JSON-compatible dict.
        
        Args:
            state: Agent state
            
        Returns:
            JSON-serializable dict
        """
        return {
            "signals": [s.model_dump() for s in state["signals"]],
            "patterns": [p.model_dump() for p in state["patterns"]],
            "root_cause": state["root_cause"].model_dump() if state["root_cause"] else None,
            "confidence": state["confidence"],
            "selected_action": state["selected_action"].model_dump() if state["selected_action"] else None,
            "risk_level": state["risk_level"],
            "action_result": state["action_result"].model_dump() if state["action_result"] else None,
            "issue_id": state["issue_id"],
            "merchant_id": state["merchant_id"],
            "stage": state["stage"],
            "requires_approval": state["requires_approval"],
            "approval_status": state["approval_status"],
            "reasoning_chain": state["reasoning_chain"],
            "error_count": state["error_count"],
            "last_error": state["last_error"],
            "created_at": state["created_at"],
            "updated_at": state["updated_at"]
        }
    
    def _deserialize_state(self, state_data: dict) -> AgentState:
        """
        Deserialize agent state from JSON dict.
        
        Args:
            state_data: JSON dict
            
        Returns:
            Agent state
        """
        return AgentState(
            signals=[Signal(**s) for s in state_data["signals"]],
            patterns=[Pattern(**p) for p in state_data["patterns"]],
            root_cause=RootCauseAnalysis(**state_data["root_cause"]) if state_data["root_cause"] else None,
            confidence=state_data["confidence"],
            selected_action=Action(**state_data["selected_action"]) if state_data["selected_action"] else None,
            risk_level=state_data["risk_level"],
            action_result=ActionResult(**state_data["action_result"]) if state_data["action_result"] else None,
            issue_id=state_data["issue_id"],
            merchant_id=state_data["merchant_id"],
            stage=state_data["stage"],
            requires_approval=state_data["requires_approval"],
            approval_status=state_data["approval_status"],
            reasoning_chain=state_data["reasoning_chain"],
            error_count=state_data["error_count"],
            last_error=state_data["last_error"],
            created_at=state_data["created_at"],
            updated_at=state_data["updated_at"]
        )


async def create_state_persistence(db_session: AsyncSession) -> StatePersistence:
    """
    Factory function to create state persistence instance.
    
    Args:
        db_session: Database session
        
    Returns:
        State persistence instance
    """
    return StatePersistence(db_session)
