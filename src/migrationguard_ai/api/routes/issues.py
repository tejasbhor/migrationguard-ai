"""
Issues and signals query API routes for MigrationGuard AI.

This module implements endpoints for querying issues and signals:
- GET /api/v1/issues - List issues with filtering
- GET /api/v1/issues/{issue_id} - Get issue details
- GET /api/v1/signals/search - Search signals (already in signals.py, enhanced here)
"""

import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func

from migrationguard_ai.db.models import (
    Issue as IssueModel,
    Signal as SignalModel,
    Action as ActionModel
)
from migrationguard_ai.api.dependencies import get_db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/issues", tags=["issues"])


# Response models
class IssueListItem(BaseModel):
    """Issue list item."""
    issue_id: str
    status: str
    merchant_id: Optional[str] = None
    root_cause_category: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    signal_count: int = 0


class ActionDetail(BaseModel):
    """Action detail for issue."""
    action_id: str
    action_type: str
    risk_level: str
    status: str
    parameters: dict
    created_at: datetime
    executed_at: Optional[datetime] = None
    result: Optional[dict] = None


class SignalDetail(BaseModel):
    """Signal detail for issue."""
    signal_id: str
    source: str
    merchant_id: str
    error_message: Optional[str] = None
    timestamp: datetime
    metadata: dict


class IssueDetail(BaseModel):
    """Detailed issue information."""
    issue_id: str
    status: str
    merchant_id: Optional[str] = None
    root_cause_category: Optional[str] = None
    root_cause_reasoning: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_type: Optional[str] = None
    signals: List[SignalDetail] = []
    actions: List[ActionDetail] = []
    reasoning_chain: List[dict] = []


@router.get("", response_model=List[IssueListItem])
async def list_issues(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status"),
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    root_cause_category: Optional[str] = Query(None, description="Filter by root cause category"),
    resolution_type: Optional[str] = Query(None, description="Filter by resolution type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List issues with filtering and pagination.
    
    Supports filtering by:
    - Status (open, in_progress, resolved)
    - Merchant ID
    - Root cause category
    - Resolution type (automated, escalated)
    
    Requirements: 6.8, 16.6
    """
    try:
        # Build query
        query = select(IssueModel)
        
        # Apply filters
        filters = []
        if status:
            filters.append(IssueModel.status == status)
        if merchant_id:
            filters.append(IssueModel.merchant_id == merchant_id)
        if root_cause_category:
            filters.append(IssueModel.root_cause_category == root_cause_category)
        if resolution_type:
            filters.append(IssueModel.resolution_type == resolution_type)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Order by creation time (newest first)
        query = query.order_by(desc(IssueModel.created_at))
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        issues = result.scalars().all()
        
        # Convert to response model
        issue_list = []
        for issue in issues:
            # Count signals for this issue
            signal_count_query = select(func.count(SignalModel.signal_id)).where(
                SignalModel.issue_id == issue.issue_id
            )
            signal_count_result = await db.execute(signal_count_query)
            signal_count = signal_count_result.scalar() or 0
            
            issue_list.append(IssueListItem(
                issue_id=issue.issue_id,
                status=issue.status,
                merchant_id=issue.merchant_id,
                root_cause_category=issue.root_cause_category,
                confidence=issue.confidence,
                created_at=issue.created_at,
                resolved_at=issue.resolved_at,
                resolution_type=issue.resolution_type,
                signal_count=signal_count
            ))
        
        logger.info(f"Retrieved {len(issue_list)} issues")
        return issue_list
        
    except Exception as e:
        logger.error(f"Failed to list issues: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list issues: {str(e)}")


@router.get("/{issue_id}", response_model=IssueDetail)
async def get_issue_detail(
    issue_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific issue.
    
    Returns complete issue details including:
    - Root cause analysis
    - All related signals
    - All actions taken
    - Complete reasoning chain
    
    Requirements: 6.8, 16.6
    """
    try:
        # Get issue
        issue_query = select(IssueModel).where(IssueModel.issue_id == issue_id)
        issue_result = await db.execute(issue_query)
        issue = issue_result.scalar_one_or_none()
        
        if not issue:
            raise HTTPException(status_code=404, detail=f"Issue {issue_id} not found")
        
        # Get related signals
        signals_query = select(SignalModel).where(
            SignalModel.issue_id == issue_id
        ).order_by(SignalModel.timestamp)
        signals_result = await db.execute(signals_query)
        signals = signals_result.scalars().all()
        
        signal_details = [
            SignalDetail(
                signal_id=signal.signal_id,
                source=signal.source,
                merchant_id=signal.merchant_id,
                error_message=signal.error_message,
                timestamp=signal.timestamp,
                metadata=signal.metadata or {}
            )
            for signal in signals
        ]
        
        # Get related actions
        actions_query = select(ActionModel).where(
            ActionModel.issue_id == issue_id
        ).order_by(ActionModel.created_at)
        actions_result = await db.execute(actions_query)
        actions = actions_result.scalars().all()
        
        action_details = [
            ActionDetail(
                action_id=action.action_id,
                action_type=action.action_type,
                risk_level=action.risk_level,
                status=action.status,
                parameters=action.parameters,
                created_at=action.created_at,
                executed_at=action.executed_at,
                result=action.result
            )
            for action in actions
        ]
        
        # Build reasoning chain from issue and actions
        reasoning_chain = []
        if issue.reasoning_chain:
            reasoning_chain = issue.reasoning_chain
        
        return IssueDetail(
            issue_id=issue.issue_id,
            status=issue.status,
            merchant_id=issue.merchant_id,
            root_cause_category=issue.root_cause_category,
            root_cause_reasoning=issue.root_cause_reasoning,
            confidence=issue.confidence,
            created_at=issue.created_at,
            resolved_at=issue.resolved_at,
            resolution_type=issue.resolution_type,
            signals=signal_details,
            actions=action_details,
            reasoning_chain=reasoning_chain
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get issue detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get issue detail: {str(e)}")
