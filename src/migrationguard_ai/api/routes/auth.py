"""
Authentication API Routes.

This module provides endpoints for user authentication including
login, token refresh, and user information.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional

from migrationguard_ai.core.auth import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    verify_password,
    get_current_user,
    TokenData,
)
from migrationguard_ai.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class RefreshRequest(BaseModel):
    """Token refresh request model."""
    refresh_token: str


class UserResponse(BaseModel):
    """User information response model."""
    user_id: str
    username: str
    role: str


# Mock user database (in production, this would be a real database)
MOCK_USERS = {
    "admin": {
        "user_id": "user_001",
        "username": "admin",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEiUM2",  # "admin123"
        "role": "admin"
    },
    "operator": {
        "user_id": "user_002",
        "username": "operator",
        "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "operator123"
        "role": "operator"
    },
    "viewer": {
        "user_id": "user_003",
        "username": "viewer",
        "password_hash": "$2b$12$V/6VhCq3tXhQKZXfYmKmyOehqdkMbC.FihZgdqCWHPvtrXU5HDW.u",  # "viewer123"
        "role": "viewer"
    }
}


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.
    
    Args:
        request: Login credentials
        
    Returns:
        Access and refresh tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    # Get user from mock database
    user = MOCK_USERS.get(request.username)
    
    if not user:
        logger.warning("login_failed", username=request.username, reason="user_not_found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        logger.warning("login_failed", username=request.username, reason="invalid_password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create tokens
    access_token = create_access_token(
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"]
    )
    
    refresh_token = create_refresh_token(
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"]
    )
    
    logger.info(
        "login_successful",
        user_id=user["user_id"],
        username=user["username"],
        role=user["role"]
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=3600  # 1 hour
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(request: RefreshRequest) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Create new access token
        new_access_token = refresh_access_token(request.refresh_token)
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=request.refresh_token,  # Return same refresh token
            expires_in=3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_refresh_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current user from JWT token
        
    Returns:
        User information
    """
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: TokenData = Depends(get_current_user)
) -> dict:
    """
    Logout current user.
    
    Note: JWT tokens are stateless, so logout is handled client-side
    by discarding the token. In production, you might implement
    token blacklisting.
    
    Args:
        current_user: Current user from JWT token
        
    Returns:
        Success message
    """
    logger.info(
        "user_logged_out",
        user_id=current_user.user_id,
        username=current_user.username
    )
    
    return {"message": "Successfully logged out"}
