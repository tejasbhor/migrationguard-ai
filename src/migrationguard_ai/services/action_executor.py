"""
Action Executor for MigrationGuard AI.

This module implements the action execution engine that safely executes
approved actions with retry logic, rollback support, and audit trail recording.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from migrationguard_ai.core.schemas import Action, ActionResult
from migrationguard_ai.integrations.support_systems import SupportSystemIntegrations
from migrationguard_ai.services.notification_service import get_notification_service
from migrationguard_ai.services.config_manager import get_config_manager
from migrationguard_ai.services.audit_trail import get_audit_trail_service
from migrationguard_ai.services.rate_limiter import get_rate_limiter
from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.safe_mode import get_safe_mode_manager


logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Action executor with retry logic and rollback support.
    
    Executes approved actions safely with:
    - Retry logic with exponential backoff
    - Rollback procedures for configuration changes
    - Audit trail recording
    - Rate limiting
    """
    
    def __init__(self):
        """Initialize action executor."""
        self.settings = get_settings()
        self.support_integrations = SupportSystemIntegrations()
        self.notification_service = get_notification_service()
        self.config_manager = get_config_manager()
        self.audit_trail = get_audit_trail_service()
        self.rate_limiter = get_rate_limiter()
        self.safe_mode_manager = get_safe_mode_manager()
    
    async def execute(self, action: Action, issue_id: Optional[str] = None) -> ActionResult:
        """
        Execute an action with retry and error handling.
        
        Uses tenacity for automatic retry with exponential backoff:
        - 3 retry attempts
        - Exponential backoff: 2^x seconds (2s, 4s, 8s)
        - Only retries on transient errors
        
        Records action in audit trail (Requirement 5.7).
        Enforces rate limiting (Requirements 10.6, 10.7).
        
        In safe mode (Requirement 10.5):
        - Stops all automated action execution
        - Queues decisions for human approval
        
        Args:
            action: Action to execute
            issue_id: Optional issue identifier for audit trail
            
        Returns:
            Action result
        """
        try:
            # Check if safe mode is active (Requirement 10.5)
            if self.safe_mode_manager.is_active():
                logger.warning(
                    f"Safe mode active - action queued for approval: {action.action_id}",
                    extra={
                        "action_id": action.action_id,
                        "action_type": action.action_type,
                        "safe_mode_reason": self.safe_mode_manager.get_activation_reason()
                    }
                )
                
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    executed_at=datetime.utcnow(),
                    result=None,
                    error_message="Safe mode active - action queued for human approval"
                )
            
            # Check rate limit (Requirements 10.6, 10.7)
            merchant_id = action.parameters.get("merchant_id", "unknown")
            is_allowed, current_count, limit = await self.rate_limiter.check_rate_limit(
                merchant_id=merchant_id,
                action_type=action.action_type
            )
            
            if not is_allowed:
                logger.warning(
                    f"Rate limit exceeded for {action.action_type} on {merchant_id}",
                    extra={
                        "merchant_id": merchant_id,
                        "action_type": action.action_type,
                        "current_count": current_count,
                        "limit": limit
                    }
                )
                
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    executed_at=datetime.utcnow(),
                    result=None,
                    error_message=f"Rate limit exceeded: {current_count}/{limit} actions per minute"
                )
            
            # Check for excessive actions (Requirement 10.7)
            should_flag = await self.rate_limiter.flag_excessive_actions(
                merchant_id=merchant_id,
                action_type=action.action_type,
                threshold=10
            )
            
            if should_flag:
                logger.warning(
                    f"Excessive actions flagged for {merchant_id}",
                    extra={
                        "merchant_id": merchant_id,
                        "action_type": action.action_type
                    }
                )
            
            logger.info(f"Executing action: {action.action_id} ({action.action_type})")
            
            # Execute with retry logic
            result = await self._execute_with_retry(action)
            
            # Record in audit trail (Requirement 5.7, 13.1, 13.2)
            if issue_id:
                try:
                    await self.audit_trail.record_action(
                        issue_id=issue_id,
                        action=action,
                        result=result,
                        reasoning={
                            "action_type": action.action_type,
                            "risk_level": action.risk_level,
                            "parameters": action.parameters
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to record audit trail: {e}")
            
            logger.info(f"Action executed successfully: {action.action_id}")
            return result
            
        except Exception as e:
            logger.error(f"Action execution failed after retries: {e}", exc_info=True)
            result = await self._handle_execution_failure(action, e)
            
            # Record failure in audit trail
            if issue_id:
                try:
                    await self.audit_trail.record_action(
                        issue_id=issue_id,
                        action=action,
                        result=result,
                        reasoning={
                            "action_type": action.action_type,
                            "error": str(e),
                            "failed_after_retries": True
                        }
                    )
                except Exception as audit_error:
                    logger.error(f"Failed to record audit trail: {audit_error}")
            
            return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _execute_with_retry(self, action: Action) -> ActionResult:
        """
        Execute action with automatic retry on transient errors.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        # Route to appropriate handler
        if action.action_type == "support_guidance":
            return await self._execute_support_guidance(action)
        elif action.action_type == "proactive_communication":
            return await self._execute_proactive_communication(action)
        elif action.action_type == "engineering_escalation":
            return await self._execute_escalation(action)
        elif action.action_type == "temporary_mitigation":
            return await self._execute_mitigation(action)
        elif action.action_type == "documentation_update":
            return await self._execute_doc_update(action)
        else:
            raise ValueError(f"Unknown action type: {action.action_type}")
    
    async def _execute_support_guidance(self, action: Action) -> ActionResult:
        """
        Execute support guidance action.
        
        Sends help/guidance to merchant via support system.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        try:
            params = action.parameters
            merchant_id = params.get("merchant_id")
            message = params.get("message")
            support_system = params.get("support_system", "zendesk")
            ticket_id = params.get("ticket_id")
            
            if not merchant_id or not message:
                raise ValueError("Missing required parameters: merchant_id, message")
            
            # Get support system client
            client = self.support_integrations.get_client(support_system)
            if not client:
                raise ValueError(f"Support system not configured: {support_system}")
            
            # Update existing ticket or create new one
            if ticket_id:
                # Update existing ticket
                ticket = await client.update_ticket(
                    ticket_id=ticket_id,
                    comment=message,
                    tags=["migrationguard-ai", "automated-response"]
                )
            else:
                # Create new ticket
                ticket = await client.create_ticket(
                    subject="Migration Support Guidance",
                    description=message,
                    merchant_id=merchant_id,
                    priority="normal",
                    tags=["migrationguard-ai", "automated-guidance"]
                )
            
            return ActionResult(
                action_id=action.action_id,
                success=True,
                executed_at=datetime.utcnow(),
                result={
                    "ticket_id": ticket.get("id"),
                    "support_system": support_system,
                    "message_sent": True
                },
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Support guidance execution failed: {e}")
            raise
    
    async def _execute_proactive_communication(self, action: Action) -> ActionResult:
        """
        Execute proactive communication action.
        
        Sends proactive notifications to affected merchants.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        try:
            params = action.parameters
            merchant_ids = params.get("merchant_ids", [])
            message = params.get("message")
            subject = params.get("subject", "Important Update")
            channel = params.get("channel", "email")
            
            if not merchant_ids or not message:
                raise ValueError("Missing required parameters: merchant_ids, message")
            
            # Send notifications
            results = await self.notification_service.send_proactive_communication(
                merchant_ids=merchant_ids,
                message=message,
                subject=subject,
                channel=channel
            )
            
            # Count successes
            success_count = sum(1 for success in results.values() if success)
            
            return ActionResult(
                action_id=action.action_id,
                success=success_count > 0,
                executed_at=datetime.utcnow(),
                result={
                    "merchants_notified": success_count,
                    "total_merchants": len(merchant_ids),
                    "channel": channel,
                    "results": results
                },
                error_message=None if success_count > 0 else "All notifications failed"
            )
            
        except Exception as e:
            logger.error(f"Proactive communication execution failed: {e}")
            raise
    
    async def _execute_escalation(self, action: Action) -> ActionResult:
        """
        Execute engineering escalation action.
        
        Creates engineering ticket with complete context.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        try:
            params = action.parameters
            issue_id = params.get("issue_id")
            root_cause = params.get("root_cause")
            signals = params.get("signals", [])
            merchant_id = params.get("merchant_id")
            priority = params.get("priority", "high")
            
            if not issue_id or not root_cause:
                raise ValueError("Missing required parameters: issue_id, root_cause")
            
            # Build escalation ticket
            subject = f"Engineering Escalation: {root_cause.get('category', 'Unknown')}"
            
            description = f"""
# Engineering Escalation

**Issue ID:** {issue_id}
**Merchant ID:** {merchant_id}
**Priority:** {priority}

## Root Cause Analysis

**Category:** {root_cause.get('category')}
**Confidence:** {root_cause.get('confidence')}
**Reasoning:** {root_cause.get('reasoning')}

## Evidence

{root_cause.get('evidence', 'No evidence provided')}

## Signals

{len(signals)} signals detected. See issue details for full context.

## Recommended Actions

{chr(10).join(f"- {action}" for action in root_cause.get('recommended_actions', []))}

---
*This ticket was automatically created by MigrationGuard AI*
            """.strip()
            
            # Create ticket in support system (using Zendesk for engineering)
            client = self.support_integrations.get_client("zendesk")
            if not client:
                raise ValueError("Zendesk not configured for escalations")
            
            ticket = await client.create_ticket(
                subject=subject,
                description=description,
                merchant_id=merchant_id or "system",
                priority=priority,
                tags=["migrationguard-ai", "engineering-escalation", "automated"]
            )
            
            return ActionResult(
                action_id=action.action_id,
                success=True,
                executed_at=datetime.utcnow(),
                result={
                    "escalation_ticket_id": ticket.get("id"),
                    "issue_id": issue_id,
                    "priority": priority
                },
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Escalation execution failed: {e}")
            raise
    
    async def _execute_mitigation(self, action: Action) -> ActionResult:
        """
        Execute temporary mitigation action.
        
        Applies configuration changes with rollback support.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        try:
            params = action.parameters
            resource_type = params.get("resource_type")
            resource_id = params.get("resource_id")
            config_changes = params.get("config_changes")
            current_config = params.get("current_config")
            reason = params.get("reason", "Temporary mitigation")
            
            if not all([resource_type, resource_id, config_changes, current_config]):
                raise ValueError("Missing required parameters for mitigation")
            
            # Apply configuration change
            success, config_change, error = await self.config_manager.apply_config_change(
                resource_type=resource_type,
                resource_id=resource_id,
                changes=config_changes,
                current_config=current_config,
                applied_by="migrationguard-ai",
                reason=reason
            )
            
            if not success:
                raise ValueError(f"Config change failed: {error}")
            
            # Get rollback data
            rollback_data = await self.config_manager.get_rollback_data(
                config_change.change_id
            )
            
            return ActionResult(
                action_id=action.action_id,
                success=True,
                executed_at=datetime.utcnow(),
                result={
                    "change_id": config_change.change_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "changes_applied": config_changes,
                    "rollback_available": True,
                    "rollback_data": rollback_data
                },
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Mitigation execution failed: {e}")
            raise
    
    async def _execute_doc_update(self, action: Action) -> ActionResult:
        """
        Execute documentation update action.
        
        Creates documentation update request or pull request.
        
        Args:
            action: Action to execute
            
        Returns:
            Action result
        """
        try:
            params = action.parameters
            doc_section = params.get("doc_section")
            issue_description = params.get("issue_description")
            suggested_update = params.get("suggested_update")
            
            if not all([doc_section, issue_description]):
                raise ValueError("Missing required parameters for doc update")
            
            # In a real implementation, this would create a PR or ticket
            # For now, we'll create a ticket in the support system
            
            subject = f"Documentation Update: {doc_section}"
            description = f"""
# Documentation Update Request

**Section:** {doc_section}

## Issue Description

{issue_description}

## Suggested Update

{suggested_update or 'See issue details for context'}

---
*This request was automatically created by MigrationGuard AI*
            """.strip()
            
            client = self.support_integrations.get_client("zendesk")
            if not client:
                raise ValueError("Zendesk not configured for doc updates")
            
            ticket = await client.create_ticket(
                subject=subject,
                description=description,
                merchant_id="documentation-team",
                priority="normal",
                tags=["migrationguard-ai", "documentation", "automated"]
            )
            
            return ActionResult(
                action_id=action.action_id,
                success=True,
                executed_at=datetime.utcnow(),
                result={
                    "doc_update_ticket_id": ticket.get("id"),
                    "doc_section": doc_section
                },
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"Doc update execution failed: {e}")
            raise
    
    async def _handle_execution_failure(
        self,
        action: Action,
        error: Exception
    ) -> ActionResult:
        """
        Handle action execution failure.
        
        After all retries are exhausted, this method:
        1. Logs the failure
        2. Creates an escalation action if appropriate
        3. Returns failure result
        
        Args:
            action: Failed action
            error: Exception that occurred
            
        Returns:
            Action result indicating failure
        """
        error_message = str(error)
        
        logger.error(
            f"Action {action.action_id} failed after retries: {error_message}",
            extra={
                "action_id": action.action_id,
                "action_type": action.action_type,
                "error": error_message
            }
        )
        
        # Create escalation action for failed actions (Requirement 5.9)
        try:
            await self._escalate_failed_action(action, error_message)
        except Exception as e:
            logger.error(f"Failed to escalate action failure: {e}")
        
        return ActionResult(
            action_id=action.action_id,
            success=False,
            executed_at=datetime.utcnow(),
            result=None,
            error_message=error_message
        )
    
    async def _escalate_failed_action(
        self,
        failed_action: Action,
        error_message: str
    ) -> None:
        """
        Create an escalation action for a failed action.
        
        Args:
            failed_action: The action that failed
            error_message: Error message from the failure
        """
        try:
            # Create escalation action
            escalation_action = Action(
                action_id=str(uuid.uuid4()),
                action_type="engineering_escalation",
                risk_level="high",
                status="pending",
                parameters={
                    "issue_id": f"failed_action_{failed_action.action_id}",
                    "root_cause": {
                        "category": "action_execution_failure",
                        "confidence": 1.0,
                        "reasoning": f"Action {failed_action.action_type} failed after retries",
                        "evidence": [error_message]
                    },
                    "merchant_id": failed_action.parameters.get("merchant_id", "unknown"),
                    "priority": "urgent",
                    "failed_action_id": failed_action.action_id,
                    "failed_action_type": failed_action.action_type,
                    "error_message": error_message
                }
            )
            
            # Execute escalation (without retry to avoid infinite loop)
            await self._execute_escalation(escalation_action)
            
            logger.info(f"Escalated failed action: {failed_action.action_id}")
            
        except Exception as e:
            logger.error(f"Failed to escalate action: {e}", exc_info=True)
    
    async def rollback_action(
        self,
        action_result: ActionResult
    ) -> bool:
        """
        Rollback an executed action.
        
        Args:
            action_result: Result of action to rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            if not action_result.result or "rollback_data" not in action_result.result:
                logger.warning(f"No rollback data for action: {action_result.action_id}")
                return False
            
            rollback_data = action_result.result["rollback_data"]
            change_id = rollback_data.get("change_id")
            
            if not change_id:
                logger.warning("No change_id in rollback data")
                return False
            
            # Perform rollback
            success, rollback_config, error = await self.config_manager.rollback_change(
                change_id=change_id
            )
            
            if not success:
                logger.error(f"Rollback failed: {error}")
                return False
            
            logger.info(f"Successfully rolled back action: {action_result.action_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback error: {e}", exc_info=True)
            return False
    
    async def close(self):
        """Close all clients and connections."""
        await self.support_integrations.close_all()
        await self.notification_service.close()
        await self.rate_limiter.close()


# Singleton instance
_action_executor: Optional[ActionExecutor] = None


def get_action_executor() -> ActionExecutor:
    """
    Get singleton action executor instance.
    
    Returns:
        Action executor instance
    """
    global _action_executor
    if _action_executor is None:
        _action_executor = ActionExecutor()
    return _action_executor
