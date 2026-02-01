"""
Unit Tests for Role-Based Access Control (RBAC).

This module tests RBAC functionality including role definitions,
permission checking, and access control dependencies.
"""

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock

from migrationguard_ai.core.rbac import (
    Role,
    Permission,
    get_role_permissions,
    has_permission,
    has_any_permission,
    has_all_permissions,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    require_any_role,
)
from migrationguard_ai.core.auth import TokenData


class TestRoleDefinitions:
    """Test role definitions and enums."""
    
    def test_role_enum_values(self):
        """Test that all roles are defined."""
        assert Role.ADMIN.value == "admin"
        assert Role.OPERATOR.value == "operator"
        assert Role.VIEWER.value == "viewer"
    
    def test_permission_enum_values(self):
        """Test that permissions are defined."""
        assert Permission.VIEW_SIGNALS.value == "view_signals"
        assert Permission.APPROVE_ACTIONS.value == "approve_actions"
        assert Permission.MANAGE_SYSTEM.value == "manage_system"


class TestRolePermissions:
    """Test role-permission mappings."""
    
    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        admin_perms = get_role_permissions(Role.ADMIN)
        
        # Admin should have all permissions
        assert Permission.VIEW_SIGNALS in admin_perms
        assert Permission.APPROVE_ACTIONS in admin_perms
        assert Permission.MANAGE_SYSTEM in admin_perms
        assert Permission.MANAGE_USERS in admin_perms
        assert len(admin_perms) > 10  # Should have many permissions
    
    def test_operator_has_operational_permissions(self):
        """Test that operator role has operational permissions."""
        operator_perms = get_role_permissions(Role.OPERATOR)
        
        # Operator should have operational permissions
        assert Permission.VIEW_SIGNALS in operator_perms
        assert Permission.APPROVE_ACTIONS in operator_perms
        assert Permission.VIEW_METRICS in operator_perms
        
        # But not system management
        assert Permission.MANAGE_SYSTEM not in operator_perms
        assert Permission.MANAGE_USERS not in operator_perms
    
    def test_viewer_has_read_only_permissions(self):
        """Test that viewer role has only read permissions."""
        viewer_perms = get_role_permissions(Role.VIEWER)
        
        # Viewer should have view permissions
        assert Permission.VIEW_SIGNALS in viewer_perms
        assert Permission.VIEW_ISSUES in viewer_perms
        assert Permission.VIEW_METRICS in viewer_perms
        
        # But not write permissions
        assert Permission.APPROVE_ACTIONS not in viewer_perms
        assert Permission.EXECUTE_ACTIONS not in viewer_perms
        assert Permission.UPDATE_CONFIG not in viewer_perms
    
    def test_role_permission_hierarchy(self):
        """Test that admin has more permissions than operator, and operator more than viewer."""
        admin_perms = get_role_permissions(Role.ADMIN)
        operator_perms = get_role_permissions(Role.OPERATOR)
        viewer_perms = get_role_permissions(Role.VIEWER)
        
        assert len(admin_perms) > len(operator_perms)
        assert len(operator_perms) > len(viewer_perms)


class TestPermissionChecking:
    """Test permission checking functions."""
    
    def test_has_permission_admin(self):
        """Test permission checking for admin role."""
        assert has_permission(Role.ADMIN, Permission.MANAGE_SYSTEM) is True
        assert has_permission(Role.ADMIN, Permission.VIEW_SIGNALS) is True
    
    def test_has_permission_operator(self):
        """Test permission checking for operator role."""
        assert has_permission(Role.OPERATOR, Permission.APPROVE_ACTIONS) is True
        assert has_permission(Role.OPERATOR, Permission.MANAGE_SYSTEM) is False
    
    def test_has_permission_viewer(self):
        """Test permission checking for viewer role."""
        assert has_permission(Role.VIEWER, Permission.VIEW_SIGNALS) is True
        assert has_permission(Role.VIEWER, Permission.APPROVE_ACTIONS) is False
    
    def test_has_any_permission_true(self):
        """Test has_any_permission returns True when role has at least one permission."""
        permissions = [Permission.VIEW_SIGNALS, Permission.MANAGE_SYSTEM]
        
        assert has_any_permission(Role.VIEWER, permissions) is True  # Has VIEW_SIGNALS
        assert has_any_permission(Role.ADMIN, permissions) is True  # Has both
    
    def test_has_any_permission_false(self):
        """Test has_any_permission returns False when role has none of the permissions."""
        permissions = [Permission.MANAGE_SYSTEM, Permission.MANAGE_USERS]
        
        assert has_any_permission(Role.VIEWER, permissions) is False
    
    def test_has_all_permissions_true(self):
        """Test has_all_permissions returns True when role has all permissions."""
        permissions = [Permission.VIEW_SIGNALS, Permission.VIEW_ISSUES]
        
        assert has_all_permissions(Role.ADMIN, permissions) is True
        assert has_all_permissions(Role.VIEWER, permissions) is True
    
    def test_has_all_permissions_false(self):
        """Test has_all_permissions returns False when role is missing any permission."""
        permissions = [Permission.VIEW_SIGNALS, Permission.MANAGE_SYSTEM]
        
        assert has_all_permissions(Role.VIEWER, permissions) is False  # Missing MANAGE_SYSTEM


class TestPermissionDependencies:
    """Test permission-based dependency functions."""
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test require_permission allows access with correct permission."""
        token_data = TokenData(
            user_id="user_123",
            username="admin",
            role="admin"
        )
        
        checker = require_permission(Permission.MANAGE_SYSTEM)
        result = await checker(current_user=token_data)
        
        assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_permission_denied(self):
        """Test require_permission denies access without permission."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_permission(Permission.MANAGE_SYSTEM)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403
        assert "permission denied" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_require_permission_invalid_role(self):
        """Test require_permission handles invalid role."""
        token_data = TokenData(
            user_id="user_123",
            username="test",
            role="invalid_role"
        )
        
        checker = require_permission(Permission.VIEW_SIGNALS)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_require_any_permission_success(self):
        """Test require_any_permission allows access with any permission."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_any_permission(
            Permission.VIEW_SIGNALS,
            Permission.MANAGE_SYSTEM
        )
        result = await checker(current_user=token_data)
        
        assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_any_permission_denied(self):
        """Test require_any_permission denies access without any permission."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_any_permission(
            Permission.MANAGE_SYSTEM,
            Permission.MANAGE_USERS
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_require_all_permissions_success(self):
        """Test require_all_permissions allows access with all permissions."""
        token_data = TokenData(
            user_id="user_123",
            username="admin",
            role="admin"
        )
        
        checker = require_all_permissions(
            Permission.VIEW_SIGNALS,
            Permission.MANAGE_SYSTEM
        )
        result = await checker(current_user=token_data)
        
        assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_all_permissions_denied(self):
        """Test require_all_permissions denies access without all permissions."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_all_permissions(
            Permission.VIEW_SIGNALS,
            Permission.MANAGE_SYSTEM
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403


class TestRoleDependencies:
    """Test role-based dependency functions."""
    
    @pytest.mark.asyncio
    async def test_require_role_success(self):
        """Test require_role allows access with correct role."""
        token_data = TokenData(
            user_id="user_123",
            username="admin",
            role="admin"
        )
        
        checker = require_role(Role.ADMIN)
        result = await checker(current_user=token_data)
        
        assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_role_denied(self):
        """Test require_role denies access with wrong role."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_role(Role.ADMIN)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403
        assert "role" in exc_info.value.detail.lower()
    
    @pytest.mark.asyncio
    async def test_require_any_role_success(self):
        """Test require_any_role allows access with any role."""
        token_data = TokenData(
            user_id="user_123",
            username="operator",
            role="operator"
        )
        
        checker = require_any_role(Role.ADMIN, Role.OPERATOR)
        result = await checker(current_user=token_data)
        
        assert result == token_data
    
    @pytest.mark.asyncio
    async def test_require_any_role_denied(self):
        """Test require_any_role denies access without any role."""
        token_data = TokenData(
            user_id="user_123",
            username="viewer",
            role="viewer"
        )
        
        checker = require_any_role(Role.ADMIN, Role.OPERATOR)
        
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=token_data)
        
        assert exc_info.value.status_code == 403


class TestIntegration:
    """Integration tests for RBAC system."""
    
    @pytest.mark.asyncio
    async def test_admin_can_access_all_endpoints(self):
        """Test that admin can access all protected endpoints."""
        admin_token = TokenData(
            user_id="admin_123",
            username="admin",
            role="admin"
        )
        
        # Test various permission checkers
        checkers = [
            require_permission(Permission.VIEW_SIGNALS),
            require_permission(Permission.MANAGE_SYSTEM),
            require_permission(Permission.APPROVE_ACTIONS),
            require_role(Role.ADMIN),
        ]
        
        for checker in checkers:
            result = await checker(current_user=admin_token)
            assert result == admin_token
    
    @pytest.mark.asyncio
    async def test_viewer_limited_access(self):
        """Test that viewer has limited access."""
        viewer_token = TokenData(
            user_id="viewer_123",
            username="viewer",
            role="viewer"
        )
        
        # Should succeed
        view_checker = require_permission(Permission.VIEW_SIGNALS)
        result = await view_checker(current_user=viewer_token)
        assert result == viewer_token
        
        # Should fail
        manage_checker = require_permission(Permission.MANAGE_SYSTEM)
        with pytest.raises(HTTPException):
            await manage_checker(current_user=viewer_token)
    
    @pytest.mark.asyncio
    async def test_operator_operational_access(self):
        """Test that operator has operational access."""
        operator_token = TokenData(
            user_id="operator_123",
            username="operator",
            role="operator"
        )
        
        # Should succeed - operational permissions
        operational_checkers = [
            require_permission(Permission.VIEW_SIGNALS),
            require_permission(Permission.APPROVE_ACTIONS),
            require_permission(Permission.VIEW_METRICS),
        ]
        
        for checker in operational_checkers:
            result = await checker(current_user=operator_token)
            assert result == operator_token
        
        # Should fail - system management
        system_checker = require_permission(Permission.MANAGE_SYSTEM)
        with pytest.raises(HTTPException):
            await system_checker(current_user=operator_token)
