"""
JWT Authentication and Authorization.

This module implements JWT token generation, validation, and refresh
for secure API authentication.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger


logger = get_logger(__name__)
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData:
    """Token payload data."""
    
    def __init__(
        self,
        user_id: str,
        username: str,
        role: str,
        exp: Optional[datetime] = None
    ):
        """Initialize token data."""
        self.user_id = user_id
        self.username = username
        self.role = role
        self.exp = exp


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User identifier
        username: Username
        role: User role
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token
    """
    settings = get_settings()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expiration_minutes)
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    logger.info(
        "access_token_created",
        user_id=user_id,
        username=username,
        role=role,
        expires_at=expire.isoformat()
    )
    
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    username: str,
    role: str
) -> str:
    """
    Create a JWT refresh token with longer expiration.
    
    Args:
        user_id: User identifier
        username: Username
        role: User role
        
    Returns:
        Encoded JWT refresh token
    """
    settings = get_settings()
    
    # Refresh tokens expire after 7 days
    expire = datetime.utcnow() + timedelta(days=7)
    
    to_encode = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    
    logger.info(
        "refresh_token_created",
        user_id=user_id,
        username=username,
        expires_at=expire.isoformat()
    )
    
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData object
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        user_id: str = payload.get("sub")
        username: str = payload.get("username")
        role: str = payload.get("role")
        exp_timestamp = payload.get("exp")
        
        if user_id is None or username is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        exp: Optional[datetime] = None
        if exp_timestamp:
            exp = datetime.fromtimestamp(exp_timestamp)
        
        return TokenData(
            user_id=user_id,
            username=username,
            role=role,
            exp=exp
        )
        
    except jwt.ExpiredSignatureError:
        logger.warning("token_expired", token=token[:20] + "...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("invalid_token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def refresh_access_token(refresh_token: str) -> str:
    """
    Create a new access token from a refresh token.
    
    Args:
        refresh_token: Valid refresh token
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        token_data = decode_token(refresh_token)
        
        # Create new access token
        new_token = create_access_token(
            user_id=token_data.user_id,
            username=token_data.username,
            role=token_data.role
        )
        
        logger.info(
            "access_token_refreshed",
            user_id=token_data.user_id,
            username=token_data.username
        )
        
        return new_token
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("token_refresh_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenData:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials
        
    Returns:
        TokenData for authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    return decode_token(token)


async def get_current_active_user(
    current_user: TokenData = Security(get_current_user)
) -> TokenData:
    """
    Dependency to get current active user.
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenData for active user
    """
    # In a real system, you would check if user is active in database
    # For now, we just return the user
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to require specific role.
    
    Args:
        required_role: Required role name
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has required role."""
        if current_user.role != required_role:
            logger.warning(
                "insufficient_permissions",
                user_id=current_user.user_id,
                user_role=current_user.role,
                required_role=required_role
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        return current_user
    
    return role_checker


def require_any_role(*allowed_roles: str):
    """
    Dependency factory to require any of the specified roles.
    
    Args:
        *allowed_roles: Allowed role names
        
    Returns:
        Dependency function
    """
    async def role_checker(
        current_user: TokenData = Security(get_current_user)
    ) -> TokenData:
        """Check if user has any of the allowed roles."""
        if current_user.role not in allowed_roles:
            logger.warning(
                "insufficient_permissions",
                user_id=current_user.user_id,
                user_role=current_user.role,
                allowed_roles=list(allowed_roles)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    
    return role_checker
