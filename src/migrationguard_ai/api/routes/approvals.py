"""
Approval workflow API routes for MigrationGuard AI.

This module implements the approval workflow endpoints for human oversight:
- GET /api/v1/approvals - List pending approvals
- POST /api/v1/approvals/{approval_id} - Approve or reject an action
- WebSocket /api/v1/approvals/ws - Real-time approval notifications
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from migrationguard_ai.db.models import Action as ActionModel, Issue as IssueModel
from migrationguard_ai.core.schemas import Action, ActionResult
from migrationguard_ai.services.action_executor import get_action_executor
from migrationguard_ai.api.dependencies import get_db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to WebSocket: {e}")


manager = ConnectionManager()


# Request/Response models
class ApprovalRequest(BaseModel):
    """Request to approve or reject an action."""
    decision: str = Field(..., description="'approve' or 'reject'")
    feedback: Optional[str] = Field(None, description="Optional feedback from operator")
    operator_id: str = Field(..., description="ID of the operator making the decision")


class ApprovalResponse(BaseModel):
    """Response after approval/rejection."""
    approval_id: str
    decision: str
    executed: bool
    result: Optional[dict] = None
    error: Optional[str] = None
    timestamp: datetime


class PendingApproval(BaseModel):
    """Pending approval details."""
    approval_id: str
    issue_id: str
    action_type: str
    risk_level: str
    parameters: dict
    reasoning: dict
    created_at: datetime
    merchant_id: Optional[str] = None
    priority: str = "normal"


@router.get("", response_model=List[PendingApproval])
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get all pending approval requests.
    
    Returns actions that require human approval, sorted by priority and creation time.
    
    Requirements: 6.1
    """
    try:
        # Build query for pending actions
        query = select(ActionModel).where(
            ActionModel.status == "pending_approval"
        )
        
        # Apply filters
        if merchant_id:
            query = query.where(ActionModel.parameters["merchant_id"].astext == merchant_id)
        
        if risk_level:
            query = query.where(ActionModel.risk_level == risk_level)
        
        # Order by priority and creation time
        query = query.order_by(
            ActionModel.risk_level.desc(),  # critical > high > medium > low
            ActionModel.created_at.asc()
        ).limit(limit)
        
        result = await db.execute(query)
        actions = result.scalars().all()
        
        # Convert to response model
        pending_approvals = []
        for action in actions:
            pending_approvals.append(PendingApproval(
                approval_id=action.action_id,
                issue_id=action.issue_id or "unknown",
                action_type=action.action_type,
                risk_level=action.risk_level,
                parameters=action.parameters,
                reasoning=action.reasoning or {},
                created_at=action.created_at,
                merchant_id=action.parameters.get("merchant_id"),
                priority=_calculate_priority(action.risk_level)
            ))
        
        logger.info(f"Retrieved {len(pending_approvals)} pending approvals")
        return pending_approvals
        
    except Exception as e:
        logger.error(f"Failed to retrieve pending approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve approvals: {str(e)}")


@router.post("/{approval_id}", response_model=ApprovalResponse)
async def approve_or_reject_action(
    approval_id: str,
    request: ApprovalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or reject a pending action.
    
    When approved, the action is executed immediately.
    When rejected, feedback is recorded for learning.
    
    Requirements: 6.4, 6.5
    """
    try:
        # Validate decision
        if request.decision not in ["approve", "reject"]:
            raise HTTPException(
                status_code=400,
                detail="Decision must be 'approve' or 'reject'"
            )
        
        # Retrieve action from database
        query = select(ActionModel).where(ActionModel.action_id == approval_id)
        result = await db.execute(query)
        action_model = result.scalar_one_or_none()
        
        if not action_model:
            raise HTTPException(status_code=404, detail=f"Approval {approval_id} not found")
        
        if action_model.status != "pending_approval":
            raise HTTPException(
                status_code=400,
                detail=f"Action is not pending approval (status: {action_model.status})"
            )
        
        # Convert to Action schema
        action = Action(
            action_id=action_model.action_id,
            action_type=action_model.action_type,
            risk_level=action_model.risk_level,
            status=action_model.status,
            parameters=action_model.parameters
        )
        
        timestamp = datetime.utcnow()
        
        if request.decision == "approve":
            # Execute the action (Requirement 6.4)
            logger.info(f"Executing approved action: {approval_id}")
            action_executor = get_action_executor()
            result = await action_executor.execute(action, issue_id=action_model.issue_id)
            
            # Update action status in database
            action_model.status = "completed" if result.success else "failed"
            action_model.executed_at = result.executed_at
            action_model.result = result.result
            action_model.error_message = result.error_message
            
            await db.commit()
            
            # Broadcast notification
            await manager.broadcast({
                "type": "approval_executed",
                "approval_id": approval_id,
                "decision": "approve",
                "success": result.success,
                "timestamp": timestamp.isoformat()
            })
            
            return ApprovalResponse(
                approval_id=approval_id,
                decision="approve",
                executed=True,
                result=result.result,
                error=result.error_message,
                timestamp=timestamp
            )
        
        else:  # reject
            # Record rejection feedback (Requirement 6.5)
            logger.info(f"Rejecting action: {approval_id}")
            action_model.status = "rejected"
            action_model.executed_at = timestamp
            action_model.error_message = f"Rejected by operator {request.operator_id}"
            
            # Store feedback for learning (Requirement 12.2)
            if request.feedback:
                if not action_model.reasoning:
                    action_model.reasoning = {}
                action_model.reasoning["operator_feedback"] = {
                    "operator_id": request.operator_id,
                    "feedback": request.feedback,
                    "timestamp": timestamp.isoformat()
                }
            
            await db.commit()
            
            # Broadcast notification
            await manager.broadcast({
                "type": "approval_rejected",
                "approval_id": approval_id,
                "decision": "reject",
                "operator_id": request.operator_id,
                "timestamp": timestamp.isoformat()
            })
            
            return ApprovalResponse(
                approval_id=approval_id,
                decision="reject",
                executed=False,
                result=None,
                error=f"Rejected by operator {request.operator_id}",
                timestamp=timestamp
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process approval: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process approval: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time approval notifications.
    
    Clients connect to receive notifications when:
    - New approvals are pending
    - Approvals are executed or rejected
    - System status changes
    
    Requirements: 6.1, 6.2
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            
            # Echo back for heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


def _calculate_priority(risk_level: str) -> str:
    """Calculate priority based on risk level."""
    priority_map = {
        "critical": "urgent",
        "high": "high",
        "medium": "normal",
        "low": "low"
    }
    return priority_map.get(risk_level, "normal")


async def notify_new_approval(approval_id: str, action_type: str, risk_level: str):
    """
    Notify connected clients of a new approval request.
    
    This function should be called when a new action requires approval.
    
    Requirements: 6.2
    """
    await manager.broadcast({
        "type": "new_approval",
        "approval_id": approval_id,
        "action_type": action_type,
        "risk_level": risk_level,
        "timestamp": datetime.utcnow().isoformat()
    })
