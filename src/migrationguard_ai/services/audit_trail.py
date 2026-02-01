"""
Audit Trail Service for MigrationGuard AI.

This module provides audit trail recording with:
- Immutable audit entries
- Tamper-evident hashing
- Hash chaining for integrity
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from migrationguard_ai.db.models.audit_trail import AuditTrail as AuditTrailModel
from migrationguard_ai.core.schemas import Action, ActionResult


logger = logging.getLogger(__name__)


class AuditTrailService:
    """
    Audit trail service for recording all system actions.
    
    Provides:
    - Immutable audit entries
    - Tamper-evident hashing (SHA-256)
    - Hash chaining for integrity verification
    - Complete action history
    """
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        """
        Initialize audit trail service.
        
        Args:
            db_session: Optional database session (for testing)
        """
        self.db_session = db_session
        self._last_hash: Optional[str] = None
    
    def _compute_hash(
        self,
        timestamp: datetime,
        issue_id: str,
        event_type: str,
        actor: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        reasoning: Dict[str, Any],
        previous_hash: Optional[str]
    ) -> str:
        """
        Compute SHA-256 hash for audit entry.
        
        Includes previous hash for chain integrity.
        
        Args:
            timestamp: Entry timestamp
            issue_id: Issue identifier
            event_type: Type of event
            actor: Who performed the action
            inputs: Input data
            outputs: Output data
            reasoning: Reasoning/explanation
            previous_hash: Hash of previous entry
            
        Returns:
            SHA-256 hash as hex string
        """
        # Create deterministic string representation
        data = {
            "timestamp": timestamp.isoformat(),
            "issue_id": issue_id,
            "event_type": event_type,
            "actor": actor,
            "inputs": inputs,
            "outputs": outputs,
            "reasoning": reasoning,
            "previous_hash": previous_hash or ""
        }
        
        # Convert to JSON with sorted keys for consistency
        data_json = json.dumps(data, sort_keys=True)
        
        # Compute SHA-256 hash
        return hashlib.sha256(data_json.encode()).hexdigest()
    
    async def record_action(
        self,
        issue_id: str,
        action: Action,
        result: ActionResult,
        reasoning: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record an action execution in the audit trail.
        
        Args:
            issue_id: Issue identifier
            action: Action that was executed
            result: Result of action execution
            reasoning: Optional reasoning/explanation
            
        Returns:
            Audit entry ID
        """
        try:
            timestamp = datetime.utcnow()
            event_type = f"action_{action.action_type}"
            actor = "system"  # Could be operator_id for manual actions
            
            # Prepare inputs
            inputs = {
                "action_id": action.action_id,
                "action_type": action.action_type,
                "risk_level": action.risk_level,
                "parameters": action.parameters
            }
            
            # Prepare outputs
            outputs = {
                "success": result.success,
                "result": result.result,
                "error_message": result.error_message,
                "executed_at": result.executed_at.isoformat()
            }
            
            # Prepare reasoning
            reasoning_data = reasoning or {}
            if not reasoning_data:
                reasoning_data = {
                    "action_type": action.action_type,
                    "risk_level": action.risk_level
                }
            
            # Get previous hash for chaining
            previous_hash = await self._get_last_hash(issue_id)
            
            # Compute hash
            entry_hash = self._compute_hash(
                timestamp=timestamp,
                issue_id=issue_id,
                event_type=event_type,
                actor=actor,
                inputs=inputs,
                outputs=outputs,
                reasoning=reasoning_data,
                previous_hash=previous_hash
            )
            
            # Create audit entry
            audit_entry = AuditTrailModel(
                timestamp=timestamp,
                issue_id=issue_id,
                event_type=event_type,
                actor=actor,
                inputs=inputs,
                outputs=outputs,
                reasoning=reasoning_data,
                hash=entry_hash,
                previous_hash=previous_hash
            )
            
            # Store in database (if session provided)
            if self.db_session:
                self.db_session.add(audit_entry)
                await self.db_session.commit()
                await self.db_session.refresh(audit_entry)
            
            # Update last hash
            self._last_hash = entry_hash
            
            logger.info(
                f"Recorded audit entry: {audit_entry.audit_id}",
                extra={
                    "issue_id": issue_id,
                    "event_type": event_type,
                    "hash": entry_hash
                }
            )
            
            return str(audit_entry.audit_id)
            
        except Exception as e:
            logger.error(f"Failed to record audit entry: {e}", exc_info=True)
            raise
    
    async def record_event(
        self,
        issue_id: str,
        event_type: str,
        actor: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        reasoning: Dict[str, Any]
    ) -> str:
        """
        Record a generic event in the audit trail.
        
        Args:
            issue_id: Issue identifier
            event_type: Type of event
            actor: Who performed the action
            inputs: Input data
            outputs: Output data
            reasoning: Reasoning/explanation
            
        Returns:
            Audit entry ID
        """
        try:
            timestamp = datetime.utcnow()
            
            # Get previous hash for chaining
            previous_hash = await self._get_last_hash(issue_id)
            
            # Compute hash
            entry_hash = self._compute_hash(
                timestamp=timestamp,
                issue_id=issue_id,
                event_type=event_type,
                actor=actor,
                inputs=inputs,
                outputs=outputs,
                reasoning=reasoning,
                previous_hash=previous_hash
            )
            
            # Create audit entry
            audit_entry = AuditTrailModel(
                timestamp=timestamp,
                issue_id=issue_id,
                event_type=event_type,
                actor=actor,
                inputs=inputs,
                outputs=outputs,
                reasoning=reasoning,
                hash=entry_hash,
                previous_hash=previous_hash
            )
            
            # Store in database (if session provided)
            if self.db_session:
                self.db_session.add(audit_entry)
                await self.db_session.commit()
                await self.db_session.refresh(audit_entry)
            
            # Update last hash
            self._last_hash = entry_hash
            
            logger.info(
                f"Recorded audit entry: {audit_entry.audit_id}",
                extra={
                    "issue_id": issue_id,
                    "event_type": event_type,
                    "hash": entry_hash
                }
            )
            
            return str(audit_entry.audit_id)
            
        except Exception as e:
            logger.error(f"Failed to record audit entry: {e}", exc_info=True)
            raise
    
    async def _get_last_hash(self, issue_id: str) -> Optional[str]:
        """
        Get the hash of the last audit entry for an issue.
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Last hash or None if no previous entries
        """
        if not self.db_session:
            return self._last_hash
        
        try:
            # Query for last entry
            stmt = (
                select(AuditTrailModel)
                .where(AuditTrailModel.issue_id == issue_id)
                .order_by(AuditTrailModel.timestamp.desc())
                .limit(1)
            )
            
            result = await self.db_session.execute(stmt)
            last_entry = result.scalar_one_or_none()
            
            if last_entry:
                return last_entry.hash
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get last hash: {e}")
            return None
    
    async def verify_chain_integrity(
        self,
        issue_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Verify the integrity of the audit trail chain for an issue.
        
        Checks:
        1. Each entry's hash is correct
        2. Each entry's previous_hash matches the previous entry's hash
        
        Args:
            issue_id: Issue identifier
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.db_session:
            return True, None
        
        try:
            # Get all entries for issue, ordered by timestamp
            stmt = (
                select(AuditTrailModel)
                .where(AuditTrailModel.issue_id == issue_id)
                .order_by(AuditTrailModel.timestamp.asc())
            )
            
            result = await self.db_session.execute(stmt)
            entries = result.scalars().all()
            
            if not entries:
                return True, None
            
            previous_hash = None
            
            for entry in entries:
                # Verify hash
                computed_hash = self._compute_hash(
                    timestamp=entry.timestamp,
                    issue_id=entry.issue_id,
                    event_type=entry.event_type,
                    actor=entry.actor,
                    inputs=entry.inputs,
                    outputs=entry.outputs,
                    reasoning=entry.reasoning,
                    previous_hash=entry.previous_hash
                )
                
                if computed_hash != entry.hash:
                    return False, f"Hash mismatch for entry {entry.audit_id}"
                
                # Verify chain
                if entry.previous_hash != previous_hash:
                    return False, f"Chain broken at entry {entry.audit_id}"
                
                previous_hash = entry.hash
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to verify chain integrity: {e}", exc_info=True)
            return False, str(e)
    
    async def get_audit_trail(
        self,
        issue_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail entries for an issue.
        
        Args:
            issue_id: Issue identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of audit entries
        """
        if not self.db_session:
            return []
        
        try:
            stmt = (
                select(AuditTrailModel)
                .where(AuditTrailModel.issue_id == issue_id)
                .order_by(AuditTrailModel.timestamp.desc())
                .limit(limit)
            )
            
            result = await self.db_session.execute(stmt)
            entries = result.scalars().all()
            
            return [
                {
                    "audit_id": str(entry.audit_id),
                    "timestamp": entry.timestamp.isoformat(),
                    "issue_id": entry.issue_id,
                    "event_type": entry.event_type,
                    "actor": entry.actor,
                    "inputs": entry.inputs,
                    "outputs": entry.outputs,
                    "reasoning": entry.reasoning,
                    "hash": entry.hash,
                    "previous_hash": entry.previous_hash
                }
                for entry in entries
            ]
            
        except Exception as e:
            logger.error(f"Failed to get audit trail: {e}", exc_info=True)
            return []


# Singleton instance (without DB session - will be created per request)
_audit_trail_service: Optional[AuditTrailService] = None


def get_audit_trail_service(
    db_session: Optional[AsyncSession] = None
) -> AuditTrailService:
    """
    Get audit trail service instance.
    
    Args:
        db_session: Optional database session
        
    Returns:
        Audit trail service instance
    """
    if db_session:
        return AuditTrailService(db_session)
    
    global _audit_trail_service
    if _audit_trail_service is None:
        _audit_trail_service = AuditTrailService()
    return _audit_trail_service
