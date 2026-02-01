"""
Configuration Manager for MigrationGuard AI.

This module provides configuration management capabilities:
- Configuration snapshots
- Configuration changes with validation
- Rollback procedures
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import hashlib
from copy import deepcopy

from migrationguard_ai.core.config import get_settings


logger = logging.getLogger(__name__)


class ConfigSnapshot:
    """
    Represents a configuration snapshot.
    
    Stores the state of a configuration at a specific point in time.
    """
    
    def __init__(
        self,
        snapshot_id: str,
        resource_type: str,
        resource_id: str,
        config_data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize configuration snapshot.
        
        Args:
            snapshot_id: Unique snapshot identifier
            resource_type: Type of resource (e.g., 'merchant_config', 'api_settings')
            resource_id: Resource identifier
            config_data: Configuration data
            timestamp: Snapshot timestamp
        """
        self.snapshot_id = snapshot_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.config_data = deepcopy(config_data)
        self.timestamp = timestamp or datetime.utcnow()
        self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Compute checksum of configuration data."""
        config_json = json.dumps(self.config_data, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "config_data": self.config_data,
            "timestamp": self.timestamp.isoformat(),
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigSnapshot":
        """Create snapshot from dictionary."""
        return cls(
            snapshot_id=data["snapshot_id"],
            resource_type=data["resource_type"],
            resource_id=data["resource_id"],
            config_data=data["config_data"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class ConfigChange:
    """
    Represents a configuration change.
    
    Tracks what was changed, when, and by whom.
    """
    
    def __init__(
        self,
        change_id: str,
        resource_type: str,
        resource_id: str,
        changes: Dict[str, Any],
        applied_by: str,
        reason: str,
        snapshot_before: ConfigSnapshot,
        snapshot_after: Optional[ConfigSnapshot] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialize configuration change.
        
        Args:
            change_id: Unique change identifier
            resource_type: Type of resource
            resource_id: Resource identifier
            changes: Dictionary of changes (key -> new value)
            applied_by: Who applied the change (user or system)
            reason: Reason for the change
            snapshot_before: Snapshot before change
            snapshot_after: Snapshot after change
            timestamp: Change timestamp
        """
        self.change_id = change_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.changes = changes
        self.applied_by = applied_by
        self.reason = reason
        self.snapshot_before = snapshot_before
        self.snapshot_after = snapshot_after
        self.timestamp = timestamp or datetime.utcnow()
        self.rolled_back = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert change to dictionary."""
        return {
            "change_id": self.change_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
            "applied_by": self.applied_by,
            "reason": self.reason,
            "snapshot_before": self.snapshot_before.to_dict(),
            "snapshot_after": self.snapshot_after.to_dict() if self.snapshot_after else None,
            "timestamp": self.timestamp.isoformat(),
            "rolled_back": self.rolled_back
        }


class ConfigManager:
    """
    Configuration manager for safe configuration changes.
    
    Provides:
    - Configuration snapshots
    - Validated configuration changes
    - Rollback procedures
    - Change history
    """
    
    def __init__(self):
        """Initialize configuration manager."""
        self.settings = get_settings()
        self.snapshots: Dict[str, ConfigSnapshot] = {}
        self.changes: Dict[str, ConfigChange] = {}
        self.change_history: List[str] = []
    
    async def snapshot_config(
        self,
        resource_type: str,
        resource_id: str,
        config_data: Dict[str, Any]
    ) -> ConfigSnapshot:
        """
        Create a configuration snapshot.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            config_data: Current configuration data
            
        Returns:
            Configuration snapshot
        """
        snapshot_id = f"{resource_type}_{resource_id}_{datetime.utcnow().timestamp()}"
        
        snapshot = ConfigSnapshot(
            snapshot_id=snapshot_id,
            resource_type=resource_type,
            resource_id=resource_id,
            config_data=config_data
        )
        
        # Store snapshot
        self.snapshots[snapshot_id] = snapshot
        
        logger.info(f"Created config snapshot: {snapshot_id}")
        return snapshot
    
    async def validate_config_change(
        self,
        resource_type: str,
        resource_id: str,
        changes: Dict[str, Any],
        current_config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a proposed configuration change.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            changes: Proposed changes
            current_config: Current configuration
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Create a copy of current config
            new_config = deepcopy(current_config)
            
            # Apply changes
            for key, value in changes.items():
                if '.' in key:
                    # Handle nested keys (e.g., 'api.timeout')
                    parts = key.split('.')
                    target = new_config
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = value
                else:
                    new_config[key] = value
            
            # Validate based on resource type
            if resource_type == "merchant_config":
                return await self._validate_merchant_config(new_config)
            elif resource_type == "api_settings":
                return await self._validate_api_settings(new_config)
            elif resource_type == "webhook_config":
                return await self._validate_webhook_config(new_config)
            else:
                # Generic validation
                return True, None
            
        except Exception as e:
            logger.error(f"Config validation error: {e}", exc_info=True)
            return False, str(e)
    
    async def _validate_merchant_config(
        self,
        config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate merchant configuration."""
        required_fields = ["merchant_id", "api_key"]
        
        for field in required_fields:
            if field not in config:
                return False, f"Missing required field: {field}"
        
        # Validate API key format
        if not isinstance(config.get("api_key"), str) or len(config["api_key"]) < 10:
            return False, "Invalid API key format"
        
        return True, None
    
    async def _validate_api_settings(
        self,
        config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate API settings."""
        # Validate timeout
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                return False, "Timeout must be a positive number"
        
        # Validate rate limits
        if "rate_limit" in config:
            rate_limit = config["rate_limit"]
            if not isinstance(rate_limit, int) or rate_limit <= 0:
                return False, "Rate limit must be a positive integer"
        
        return True, None
    
    async def _validate_webhook_config(
        self,
        config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """Validate webhook configuration."""
        # Validate URL
        if "url" in config:
            url = config["url"]
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                return False, "Invalid webhook URL"
        
        return True, None
    
    async def apply_config_change(
        self,
        resource_type: str,
        resource_id: str,
        changes: Dict[str, Any],
        current_config: Dict[str, Any],
        applied_by: str,
        reason: str
    ) -> tuple[bool, Optional[ConfigChange], Optional[str]]:
        """
        Apply a configuration change with validation.
        
        Args:
            resource_type: Type of resource
            resource_id: Resource identifier
            changes: Changes to apply
            current_config: Current configuration
            applied_by: Who is applying the change
            reason: Reason for the change
            
        Returns:
            Tuple of (success, config_change, error_message)
        """
        try:
            # Validate change
            is_valid, error = await self.validate_config_change(
                resource_type, resource_id, changes, current_config
            )
            
            if not is_valid:
                logger.warning(f"Config change validation failed: {error}")
                return False, None, error
            
            # Create snapshot before change
            snapshot_before = await self.snapshot_config(
                resource_type, resource_id, current_config
            )
            
            # Apply changes
            new_config = deepcopy(current_config)
            for key, value in changes.items():
                if '.' in key:
                    parts = key.split('.')
                    target = new_config
                    for part in parts[:-1]:
                        if part not in target:
                            target[part] = {}
                        target = target[part]
                    target[parts[-1]] = value
                else:
                    new_config[key] = value
            
            # Create snapshot after change
            snapshot_after = await self.snapshot_config(
                resource_type, resource_id, new_config
            )
            
            # Create change record
            change_id = f"change_{resource_type}_{resource_id}_{datetime.utcnow().timestamp()}"
            config_change = ConfigChange(
                change_id=change_id,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes,
                applied_by=applied_by,
                reason=reason,
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after
            )
            
            # Store change
            self.changes[change_id] = config_change
            self.change_history.append(change_id)
            
            logger.info(f"Applied config change: {change_id}")
            return True, config_change, None
            
        except Exception as e:
            logger.error(f"Failed to apply config change: {e}", exc_info=True)
            return False, None, str(e)
    
    async def rollback_change(
        self,
        change_id: str
    ) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Rollback a configuration change.
        
        Args:
            change_id: Change identifier to rollback
            
        Returns:
            Tuple of (success, rollback_config, error_message)
        """
        try:
            # Get change record
            config_change = self.changes.get(change_id)
            if not config_change:
                return False, None, f"Change not found: {change_id}"
            
            if config_change.rolled_back:
                return False, None, "Change already rolled back"
            
            # Get snapshot before change
            snapshot_before = config_change.snapshot_before
            rollback_config = snapshot_before.config_data
            
            # Mark as rolled back
            config_change.rolled_back = True
            
            logger.info(f"Rolled back config change: {change_id}")
            return True, rollback_config, None
            
        except Exception as e:
            logger.error(f"Failed to rollback change: {e}", exc_info=True)
            return False, None, str(e)
    
    async def get_change_history(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ConfigChange]:
        """
        Get configuration change history.
        
        Args:
            resource_type: Optional filter by resource type
            resource_id: Optional filter by resource ID
            limit: Maximum number of changes to return
            
        Returns:
            List of configuration changes
        """
        changes = []
        
        for change_id in reversed(self.change_history[-limit:]):
            change = self.changes.get(change_id)
            if not change:
                continue
            
            # Apply filters
            if resource_type and change.resource_type != resource_type:
                continue
            if resource_id and change.resource_id != resource_id:
                continue
            
            changes.append(change)
        
        return changes
    
    async def get_rollback_data(
        self,
        change_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get rollback data for a change.
        
        Args:
            change_id: Change identifier
            
        Returns:
            Rollback data (snapshot before change) or None
        """
        config_change = self.changes.get(change_id)
        if not config_change:
            return None
        
        return {
            "change_id": change_id,
            "resource_type": config_change.resource_type,
            "resource_id": config_change.resource_id,
            "rollback_config": config_change.snapshot_before.config_data,
            "snapshot_id": config_change.snapshot_before.snapshot_id,
            "timestamp": config_change.snapshot_before.timestamp.isoformat()
        }


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    Get singleton configuration manager instance.
    
    Returns:
        Configuration manager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
