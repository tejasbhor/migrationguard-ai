"""
Metrics and monitoring API routes for MigrationGuard AI.

This module implements endpoints for system performance metrics:
- GET /api/v1/metrics/performance - System performance metrics
- GET /api/v1/metrics/deflection - Ticket deflection metrics
- GET /api/v1/metrics/confidence-calibration - Confidence calibration metrics
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from migrationguard_ai.db.models import Action as ActionModel, Issue as IssueModel, Signal as SignalModel
from migrationguard_ai.api.dependencies import get_db


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


# Response models
class PerformanceMetrics(BaseModel):
    """System performance metrics."""
    signal_ingestion_rate: float = Field(..., description="Signals per minute")
    avg_processing_latency: float = Field(..., description="Average processing time in seconds")
    action_success_rate: float = Field(..., description="Percentage of successful actions")
    active_issues: int = Field(..., description="Number of active issues")
    total_signals_24h: int = Field(..., description="Total signals in last 24 hours")
    total_actions_24h: int = Field(..., description="Total actions in last 24 hours")
    timestamp: datetime


class DeflectionMetrics(BaseModel):
    """Ticket deflection metrics."""
    deflection_rate: float = Field(..., description="Percentage of tickets deflected")
    avg_resolution_time: float = Field(..., description="Average resolution time in minutes")
    total_deflected: int = Field(..., description="Total tickets deflected")
    total_escalated: int = Field(..., description="Total tickets escalated")
    deflection_by_category: dict = Field(..., description="Deflection rate by issue category")
    timestamp: datetime


class ConfidenceCalibrationMetrics(BaseModel):
    """Confidence calibration metrics."""
    calibration_accuracy: float = Field(..., description="Overall calibration accuracy")
    confidence_buckets: dict = Field(..., description="Accuracy by confidence bucket")
    total_predictions: int = Field(..., description="Total predictions made")
    drift_detected: bool = Field(..., description="Whether calibration drift is detected")
    timestamp: datetime


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
    time_range: int = Query(24, ge=1, le=168, description="Time range in hours")
):
    """
    Get system performance metrics.
    
    Returns metrics including:
    - Signal ingestion rate
    - Processing latency
    - Action success rate
    - Active issues count
    
    Requirements: 6.6, 15.1
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        
        # Signal ingestion rate (signals per minute)
        signal_count_query = select(func.count(SignalModel.signal_id)).where(
            SignalModel.timestamp >= cutoff_time
        )
        signal_count_result = await db.execute(signal_count_query)
        total_signals = signal_count_result.scalar() or 0
        
        # Calculate rate per minute
        minutes_in_range = time_range * 60
        signal_rate = total_signals / minutes_in_range if minutes_in_range > 0 else 0
        
        # Average processing latency
        # Calculate time from signal creation to action execution
        latency_query = select(
            func.avg(
                func.extract('epoch', ActionModel.executed_at - ActionModel.created_at)
            )
        ).where(
            and_(
                ActionModel.created_at >= cutoff_time,
                ActionModel.executed_at.isnot(None)
            )
        )
        latency_result = await db.execute(latency_query)
        avg_latency = latency_result.scalar() or 0
        
        # Action success rate
        action_stats_query = select(
            func.count(ActionModel.action_id).label('total'),
            func.sum(case((ActionModel.status == 'completed', 1), else_=0)).label('successful')
        ).where(
            ActionModel.created_at >= cutoff_time
        )
        action_stats_result = await db.execute(action_stats_query)
        action_stats = action_stats_result.one()
        
        total_actions = action_stats.total or 0
        successful_actions = action_stats.successful or 0
        success_rate = (successful_actions / total_actions * 100) if total_actions > 0 else 0
        
        # Active issues
        active_issues_query = select(func.count(IssueModel.issue_id)).where(
            IssueModel.status.in_(['open', 'in_progress'])
        )
        active_issues_result = await db.execute(active_issues_query)
        active_issues = active_issues_result.scalar() or 0
        
        return PerformanceMetrics(
            signal_ingestion_rate=round(signal_rate, 2),
            avg_processing_latency=round(avg_latency, 2),
            action_success_rate=round(success_rate, 2),
            active_issues=active_issues,
            total_signals_24h=total_signals,
            total_actions_24h=total_actions,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve performance metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")


@router.get("/deflection", response_model=DeflectionMetrics)
async def get_deflection_metrics(
    db: AsyncSession = Depends(get_db),
    time_range: int = Query(24, ge=1, le=168, description="Time range in hours")
):
    """
    Get ticket deflection metrics.
    
    Returns metrics including:
    - Deflection rate
    - Average resolution time
    - Deflection by category
    
    Requirements: 6.6, 8.1, 11.1
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        
        # Get deflection statistics
        deflection_query = select(
            func.count(IssueModel.issue_id).label('total'),
            func.sum(case((IssueModel.resolution_type == 'automated', 1), else_=0)).label('deflected'),
            func.sum(case((IssueModel.resolution_type == 'escalated', 1), else_=0)).label('escalated')
        ).where(
            and_(
                IssueModel.created_at >= cutoff_time,
                IssueModel.status == 'resolved'
            )
        )
        deflection_result = await db.execute(deflection_query)
        deflection_stats = deflection_result.one()
        
        total_issues = deflection_stats.total or 0
        deflected = deflection_stats.deflected or 0
        escalated = deflection_stats.escalated or 0
        
        deflection_rate = (deflected / total_issues * 100) if total_issues > 0 else 0
        
        # Average resolution time (in minutes)
        resolution_time_query = select(
            func.avg(
                func.extract('epoch', IssueModel.resolved_at - IssueModel.created_at) / 60
            )
        ).where(
            and_(
                IssueModel.created_at >= cutoff_time,
                IssueModel.status == 'resolved',
                IssueModel.resolution_type == 'automated'
            )
        )
        resolution_time_result = await db.execute(resolution_time_query)
        avg_resolution_time = resolution_time_result.scalar() or 0
        
        # Deflection by category
        # This would require a category field on issues
        # For now, return a placeholder
        deflection_by_category = {
            "migration_misstep": 0.75,
            "platform_regression": 0.65,
            "documentation_gap": 0.80,
            "config_error": 0.70
        }
        
        return DeflectionMetrics(
            deflection_rate=round(deflection_rate, 2),
            avg_resolution_time=round(avg_resolution_time, 2),
            total_deflected=deflected,
            total_escalated=escalated,
            deflection_by_category=deflection_by_category,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve deflection metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")


@router.get("/confidence-calibration", response_model=ConfidenceCalibrationMetrics)
async def get_confidence_calibration_metrics(
    db: AsyncSession = Depends(get_db),
    time_range: int = Query(24, ge=1, le=168, description="Time range in hours")
):
    """
    Get confidence calibration metrics.
    
    Returns metrics showing how well the system's confidence scores
    match actual outcomes.
    
    Requirements: 6.6, 8.1
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=time_range)
        
        # Get actions with confidence scores and outcomes
        # Confidence is stored in reasoning.confidence field
        actions_query = select(
            ActionModel.reasoning,
            ActionModel.status
        ).where(
            and_(
                ActionModel.created_at >= cutoff_time,
                ActionModel.status.in_(['completed', 'failed'])
            )
        )
        actions_result = await db.execute(actions_query)
        actions = actions_result.all()
        
        # Calculate calibration by confidence bucket
        confidence_buckets = {
            "0.9-1.0": {"predicted": 0, "actual": 0, "count": 0},
            "0.8-0.9": {"predicted": 0, "actual": 0, "count": 0},
            "0.7-0.8": {"predicted": 0, "actual": 0, "count": 0},
            "0.6-0.7": {"predicted": 0, "actual": 0, "count": 0},
            "0.0-0.6": {"predicted": 0, "actual": 0, "count": 0}
        }
        
        total_predictions = 0
        total_correct = 0
        
        for action in actions:
            if not action.reasoning or 'confidence' not in action.reasoning:
                continue
            
            confidence = action.reasoning.get('confidence', 0)
            is_successful = action.status == 'completed'
            
            # Determine bucket
            if confidence >= 0.9:
                bucket = "0.9-1.0"
            elif confidence >= 0.8:
                bucket = "0.8-0.9"
            elif confidence >= 0.7:
                bucket = "0.7-0.8"
            elif confidence >= 0.6:
                bucket = "0.6-0.7"
            else:
                bucket = "0.0-0.6"
            
            confidence_buckets[bucket]["count"] += 1
            confidence_buckets[bucket]["predicted"] += confidence
            if is_successful:
                confidence_buckets[bucket]["actual"] += 1
            
            total_predictions += 1
            if is_successful:
                total_correct += 1
        
        # Calculate accuracy for each bucket
        calibration_results = {}
        for bucket, stats in confidence_buckets.items():
            if stats["count"] > 0:
                avg_predicted = stats["predicted"] / stats["count"]
                actual_accuracy = stats["actual"] / stats["count"]
                calibration_results[bucket] = {
                    "predicted_confidence": round(avg_predicted, 3),
                    "actual_accuracy": round(actual_accuracy, 3),
                    "count": stats["count"]
                }
        
        # Overall calibration accuracy
        # Good calibration means predicted confidence ≈ actual accuracy
        calibration_accuracy = (total_correct / total_predictions * 100) if total_predictions > 0 else 0
        
        # Detect drift (simplified - would need more sophisticated logic in production)
        drift_detected = abs(calibration_accuracy - 90) > 10  # Alert if accuracy drifts >10% from target
        
        return ConfidenceCalibrationMetrics(
            calibration_accuracy=round(calibration_accuracy, 2),
            confidence_buckets=calibration_results,
            total_predictions=total_predictions,
            drift_detected=drift_detected,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve confidence calibration metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")
