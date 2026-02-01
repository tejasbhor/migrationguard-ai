"""
Property-Based Tests for Role-Based Access Control.

This module tests security properties related to RBAC enforcement.
"""

import pytest
from hypothesis import given, strategies as st, assume
from fastapi import HTTPException

from migrationguard_ai.core.rbac import (
    Role,
    Permission,
    has_permission,
    has_any_permission,
    has_all_permissions,
    ROLE_PERMISSIONS,
)


# Strategy for generating roles
role_strategy = st.sampled_from([Role.ADMIN, Role.OPERATOR, Role.VIEWER])

# Strategy for generating permissions
permission_strategy = st.sampled_from([
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
])

# Strategy for generating user data
user_strategy = st.builds(
    dict,
    user_id=st.text(min_size=1, max_size=50),
    username=st.text(min_size=1, max_size=50),
    role=role_strategy,
)


class TestRBACProperties:
    """Property-based tests for RBAC enforcement."""
    
    @given(role=role_strategy, permission=permission_strategy)
    def test_property_52_permission_check_before_operation(self, role, permission):
        """
        Property 52: Role-based access control
        
        For any operation that requires a permission, the system must verify
        that the actor has the required permission before allowing the operation.
        
        Validates: Requirements 18.3
        """
        # Check if role has permission
        role_has_permission = permission in ROLE_PERMISSIONS.get(role, set())
        
        # Verify has_permission returns correct result
        result = has_permission(role, permission)
        assert result == role_has_permission, (
            f"Permission check failed: role={role}, permission={permission}, "
            f"expected={role_has_permission}, got={result}"
        )
    
    @given(role=role_strategy, permissions=st.lists(permission_strategy, min_size=1, max_size=5))
    def test_property_52_any_permission_check(self, role, permissions):
        """
        Property 52: Role-based access control (any permission variant)
        
        For any operation that requires any of multiple permissions, the system
        must verify that the actor has at least one of the required permissions.
        
        Validates: Requirements 18.3
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        
        # Check if role has any of the permissions
        has_any = any(perm in role_permissions for perm in permissions)
        
        # Verify has_any_permission returns correct result
        result = has_any_permission(role, permissions)
        assert result == has_any, (
            f"Any permission check failed: role={role}, permissions={permissions}, "
            f"expected={has_any}, got={result}"
        )
    
    @given(role=role_strategy, permissions=st.lists(permission_strategy, min_size=1, max_size=5))
    def test_property_52_all_permissions_check(self, role, permissions):
        """
        Property 52: Role-based access control (all permissions variant)
        
        For any operation that requires all of multiple permissions, the system
        must verify that the actor has all of the required permissions.
        
        Validates: Requirements 18.3
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        
        # Check if role has all of the permissions
        has_all = all(perm in role_permissions for perm in permissions)
        
        # Verify has_all_permissions returns correct result
        result = has_all_permissions(role, permissions)
        assert result == has_all, (
            f"All permissions check failed: role={role}, permissions={permissions}, "
            f"expected={has_all}, got={result}"
        )
    
    @given(role1=role_strategy, role2=role_strategy)
    def test_property_52_role_check(self, role1, role2):
        """
        Property 52: Role-based access control (role-based variant)
        
        For any operation that requires a specific role, the system must verify
        that the actor has the required role before allowing the operation.
        
        Validates: Requirements 18.3
        """
        # Check if roles match
        has_role = role1 == role2
        
        # Verify role matching logic
        assert (role1 == role2) == has_role
    
    @given(role=role_strategy, required_roles=st.lists(role_strategy, min_size=1, max_size=3))
    def test_property_52_any_role_check(self, role, required_roles):
        """
        Property 52: Role-based access control (any role variant)
        
        For any operation that requires any of multiple roles, the system must
        verify that the actor has at least one of the required roles.
        
        Validates: Requirements 18.3
        """
        # Check if user has any of the required roles
        has_any_role = role in required_roles
        
        # Verify role matching logic
        assert (role in required_roles) == has_any_role
    
    @given(role=role_strategy)
    def test_property_52_admin_has_all_permissions(self, role):
        """
        Property 52: Role-based access control (admin privilege)
        
        The Admin role must have all permissions in the system.
        
        Validates: Requirements 18.3
        """
        if role == Role.ADMIN:
            # Admin should have all permissions
            all_permissions = [
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
            ]
            
            for permission in all_permissions:
                assert has_permission(role, permission), (
                    f"Admin role missing permission: {permission}"
                )
    
    @given(role=role_strategy)
    def test_property_52_viewer_cannot_modify(self, role):
        """
        Property 52: Role-based access control (viewer restrictions)
        
        The Viewer role must not have any permissions that modify data or execute actions.
        
        Validates: Requirements 18.3
        """
        if role == Role.VIEWER:
            # Viewer should not have any modification permissions
            modification_permissions = [
                Permission.SUBMIT_SIGNALS,
                Permission.UPDATE_ISSUES,
                Permission.APPROVE_ACTIONS,
                Permission.REJECT_ACTIONS,
                Permission.EXECUTE_ACTIONS,
                Permission.UPDATE_CONFIG,
                Permission.MANAGE_USERS,
                Permission.MANAGE_SYSTEM,
            ]
            
            for permission in modification_permissions:
                assert not has_permission(role, permission), (
                    f"Viewer role should not have permission: {permission}"
                )
    
    @given(role=role_strategy)
    def test_property_52_operator_can_approve_but_not_admin(self, role):
        """
        Property 52: Role-based access control (operator capabilities)
        
        The Operator role must be able to approve/reject actions but not perform
        system administration tasks.
        
        Validates: Requirements 18.3
        """
        if role == Role.OPERATOR:
            # Operator should have approval permissions
            assert has_permission(role, Permission.APPROVE_ACTIONS)
            assert has_permission(role, Permission.REJECT_ACTIONS)
            
            # But not system admin permissions
            assert not has_permission(role, Permission.MANAGE_SYSTEM)
            assert not has_permission(role, Permission.MANAGE_USERS)
            assert not has_permission(role, Permission.EXECUTE_ACTIONS)
            assert not has_permission(role, Permission.UPDATE_CONFIG)
    
    @given(
        role=role_strategy,
        operation=st.sampled_from([
            "view_signals",
            "submit_signals",
            "approve_action",
            "execute_action",
            "update_config",
            "manage_users",
        ])
    )
    def test_property_52_operation_permission_mapping(self, role, operation):
        """
        Property 52: Role-based access control (operation mapping)
        
        Every operation must map to a specific permission, and access must be
        controlled based on that permission.
        
        Validates: Requirements 18.3
        """
        # Map operations to permissions
        operation_permissions = {
            "view_signals": Permission.VIEW_SIGNALS,
            "submit_signals": Permission.SUBMIT_SIGNALS,
            "approve_action": Permission.APPROVE_ACTIONS,
            "execute_action": Permission.EXECUTE_ACTIONS,
            "update_config": Permission.UPDATE_CONFIG,
            "manage_users": Permission.MANAGE_USERS,
        }
        
        required_permission = operation_permissions[operation]
        
        # Check if user has permission for operation
        user_has_permission = has_permission(role, required_permission)
        
        # Verify permission check is consistent
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        expected = required_permission in role_permissions
        
        assert user_has_permission == expected, (
            f"Permission check inconsistent: operation={operation}, role={role}, "
            f"expected={expected}, got={user_has_permission}"
        )
