"""
Role-Based Access Control (RBAC) System.

This module defines roles, permissions, and access control logic
for the MigrationGuard AI system.
"""

from enum import Enum
from typing import Set, Dict, List
from fastapi import HTTPException, Security, status

from migrationguard_ai.core.auth import get_current_user, TokenData
from migrationguard_ai.core.logging import get_logger


logger = get_logger(__name__)


class Role(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    """System permissions."""
    # Signal permissions
    VIEW_SIGNALS = "view_signals"
    SUBMIT_SIGNALS = "submit_signals"
    
    # Issue permissions
    VIEW_ISSUES = "view_issues"
    UPDATE_ISSUES = "update_issues"
    
    # Approval permissions
    VIEW_APPROVALS = "view_approvals"
    APPROVE_ACTIONS = "approve_actions"
    REJECT_ACTIONS = "reject_actions"
    
    # Action permissions
    VIEW_ACTIONS = "view_actions"
    EXECUTE_ACTIONS = "execute_actions"
    
    # Metrics permissions
    VIEW_METRICS = "view_metrics"
    
    # Configuration permissions
    VIEW_CONFIG = "view_config"
    UPDATE_CONFIG = "update_config"
    
    # User management permissions
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"
    
    # System permissions
    VIEW_AUDIT_TRAIL = "view_audit_trail"
    MANAGE_SYSTEM = "manage_system"


# Role-Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {
        # Admins have all permissions
        Permission.VIEW_SIGNALS,
        Permission.SUBMIT_SIGNALS,
        Permission.VIEW_ISSUES,
        Permission.UPDATE_ISSUES,
        Permission.VIEW_APPROVALS,
        Permission.APPROVE_ACTIONS,
        Permission.REJECT_ACTIONS,
        Permission.VIEW_ACTIONS,
        Permission.EXECUTE_ACTIONS,
        Permission.VIEW_METRICS,
        Permission.VIEW_CONFIG,
        Permission.UPDATE_CONFIG,
        Permission.VIEW_USERS,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_TRAIL,
        Permission.MANAGE_SYSTEM,
    },
    Role.OPERATOR: {
        # Operators can view and manage operations
        Permission.VIEW_SIGNALS,
        Permission.SUBMIT_SIGNALS,
        Permission.VIEW_ISSUES,
        Permission.UPDATE_ISSUES,
        Permission.VIEW_APPROVALS,
        Permission.APPROVE_ACTIONS,
        Permission.REJECT_ACTIONS,
        Permission.VIEW_ACTIONS,
        Permission.VIEW_METRICS,
        Permission.VIEW_CONFIG,
        Permission.VIEW_AUDIT_TRAIL,
    },
    Role.VIEWER: {
        # Viewers can only view data
        Permission.VIEW_SIGNALS,
        Permission.VIEW_ISSUES,
        Permission.VIEW_APPROVALS,
        Permission.VIEW_ACTIONS,
        Permission.VIEW_METRICS,
        Permission.VIEW_AUDIT_TRAIL,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """
    Get all permissions for a given role.
    
    Args:
        role: User role
        
    Returns:
        Set of permissions for the role
    """
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: Role, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.
    
    Args:
        role: User role
        permission: Permission to check
        
    Returns:
        True if role has permission, False otherwise
    """
    role_perms = get_role_permissions(role)
    return permission in role_perms


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """
    Check if a role has any of the specified permissions.
    
    Args:
        role: User role
        permissions: List of permissions to check
        
    Returns:
        True if role has any permission, False otherwise
    """
    role_perms = get_role_permissions(role)
    return any(perm in role_perms for perm in permissions)


def has_all_permissions(role: Role, permissions: List[Permission]) -> bool:
    """
    Check if a role has all of the specified permissions.
    
    Args:
        role: User role
        permissions: List of permissions to check
        
    Returns:
        True if role has all permissions, False otherwise
    """
    role_perms = get_role_permissions(role)
    return all(perm in role_perms for perm in permissions)


def require_permission(permission: Permission):
    """
    Dependency factory to require a specific permission.
    
    Args:
        permission: Required permission
        
    Returns:
        Dependency function
        
    Example:
        @router.get("/admin", dependencies=[Depends(require_permission(Permission.MANAGE_SYSTEM))])
        async def admin_endpoint():
            return {"message": "Admin access granted"}
    """
    async def permission_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has required permission."""
        try:
            user_role = Role(current_user.role)
        except ValueError:
            logger.warning(
                "invalid_role",
                user_id=current_user.user_id,
                role=current_user.role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        if not has_permission(user_role, permission):
            logger.warning(
                "permission_denied",
                user_id=current_user.user_id,
                username=current_user.username,
                role=current_user.role,
                required_permission=permission.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {permission.value}"
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(*permissions: Permission):
    """
    Dependency factory to require any of the specified permissions.
    
    Args:
        *permissions: Required permissions (any)
        
    Returns:
        Dependency function
        
    Example:
        @router.get("/data", dependencies=[Depends(require_any_permission(
            Permission.VIEW_SIGNALS, Permission.VIEW_ISSUES
        ))])
        async def data_endpoint():
            return {"message": "Data access granted"}
    """
    async def permission_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has any of the required permissions."""
        try:
            user_role = Role(current_user.role)
        except ValueError:
            logger.warning(
                "invalid_role",
                user_id=current_user.user_id,
                role=current_user.role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        if not has_any_permission(user_role, list(permissions)):
            logger.warning(
                "permission_denied",
                user_id=current_user.user_id,
                username=current_user.username,
                role=current_user.role,
                required_permissions=[p.value for p in permissions]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permissions (any): {', '.join(p.value for p in permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_all_permissions(*permissions: Permission):
    """
    Dependency factory to require all of the specified permissions.
    
    Args:
        *permissions: Required permissions (all)
        
    Returns:
        Dependency function
        
    Example:
        @router.post("/critical", dependencies=[Depends(require_all_permissions(
            Permission.APPROVE_ACTIONS, Permission.EXECUTE_ACTIONS
        ))])
        async def critical_endpoint():
            return {"message": "Critical access granted"}
    """
    async def permission_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has all of the required permissions."""
        try:
            user_role = Role(current_user.role)
        except ValueError:
            logger.warning(
                "invalid_role",
                user_id=current_user.user_id,
                role=current_user.role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        if not has_all_permissions(user_role, list(permissions)):
            logger.warning(
                "permission_denied",
                user_id=current_user.user_id,
                username=current_user.username,
                role=current_user.role,
                required_permissions=[p.value for p in permissions]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permissions (all): {', '.join(p.value for p in permissions)}"
            )
        
        return current_user
    
    return permission_checker


def require_role(role: Role):
    """
    Dependency factory to require a specific role.
    
    Args:
        role: Required role
        
    Returns:
        Dependency function
        
    Example:
        @router.get("/admin", dependencies=[Depends(require_role(Role.ADMIN))])
        async def admin_endpoint():
            return {"message": "Admin access granted"}
    """
    async def role_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has required role."""
        if current_user.role != role.value:
            logger.warning(
                "role_denied",
                user_id=current_user.user_id,
                username=current_user.username,
                user_role=current_user.role,
                required_role=role.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role.value}"
            )
        
        return current_user
    
    return role_checker


def require_any_role(*roles: Role):
    """
    Dependency factory to require any of the specified roles.
    
    Args:
        *roles: Required roles (any)
        
    Returns:
        Dependency function
        
    Example:
        @router.get("/ops", dependencies=[Depends(require_any_role(
            Role.ADMIN, Role.OPERATOR
        ))])
        async def ops_endpoint():
            return {"message": "Operations access granted"}
    """
    async def role_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has any of the required roles."""
        if current_user.role not in [r.value for r in roles]:
            logger.warning(
                "role_denied",
                user_id=current_user.user_id,
                username=current_user.username,
                user_role=current_user.role,
                required_roles=[r.value for r in roles]
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles (any): {', '.join(r.value for r in roles)}"
            )
        
        return current_user
    
    return role_checker
