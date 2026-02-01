"""
Rate Limiter for MigrationGuard AI.

This module provides Redis-based rate limiting for actions:
- Per-merchant rate limits
- Per-action-type rate limits
- Excessive action flagging
"""

import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis

from migrationguard_ai.core.config import get_settings


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter for action execution.
    
    Implements:
    - Per-merchant, per-action-type rate limits
    - Sliding window rate limiting
    - Excessive action flagging
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Optional Redis client (for testing)
        """
        self.redis_client = redis_client
        self.settings = get_settings()
        
        # Default rate limits (actions per minute)
        self.default_limits = {
            "support_guidance": 10,
            "proactive_communication": 5,
            "engineering_escalation": 3,
            "temporary_mitigation": 2,
            "documentation_update": 5
        }
        
        # Window size in seconds
        self.window_size = 60  # 1 minute
    
    async def _get_redis_client(self) -> redis.Redis:
        """Get or create Redis client."""
        if self.redis_client:
            return self.redis_client
        
        # Create new client
        redis_url = getattr(self.settings, 'REDIS_URL', 'redis://localhost:6379')
        return await redis.from_url(redis_url, decode_responses=True)
    
    async def check_rate_limit(
        self,
        merchant_id: str,
        action_type: str
    ) -> Tuple[bool, int, int]:
        """
        Check if action is within rate limit.
        
        Args:
            merchant_id: Merchant identifier
            action_type: Type of action
            
        Returns:
            Tuple of (is_allowed, current_count, limit)
        """
        try:
            client = await self._get_redis_client()
            
            # Get rate limit for action type
            limit = self.default_limits.get(action_type, 10)
            
            # Create key for rate limiting
            key = f"ratelimit:action:{action_type}:{merchant_id}"
            
            # Get current count
            current_count = await client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Check if within limit
            is_allowed = current_count < limit
            
            if is_allowed:
                # Increment counter
                await client.incr(key)
                
                # Set expiry if this is the first action in the window
                if current_count == 0:
                    await client.expire(key, self.window_size)
                
                current_count += 1
            
            logger.debug(
                f"Rate limit check: {action_type} for {merchant_id}",
                extra={
                    "merchant_id": merchant_id,
                    "action_type": action_type,
                    "current_count": current_count,
                    "limit": limit,
                    "is_allowed": is_allowed
                }
            )
            
            return is_allowed, current_count, limit
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open - allow action if rate limiting fails
            return True, 0, 0
    
    async def flag_excessive_actions(
        self,
        merchant_id: str,
        action_type: str,
        threshold: int = 10
    ) -> bool:
        """
        Check if merchant has exceeded action threshold.
        
        Flags merchants with excessive actions for review (Requirement 10.7).
        
        Args:
            merchant_id: Merchant identifier
            action_type: Type of action
            threshold: Threshold for flagging (default: 10)
            
        Returns:
            True if should be flagged, False otherwise
        """
        try:
            client = await self._get_redis_client()
            
            # Create key for tracking
            key = f"ratelimit:action:{action_type}:{merchant_id}"
            
            # Get current count
            current_count = await client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Check if exceeds threshold
            should_flag = current_count >= threshold
            
            if should_flag:
                # Store flag
                flag_key = f"ratelimit:flagged:{merchant_id}:{action_type}"
                await client.setex(
                    flag_key,
                    3600,  # 1 hour
                    current_count
                )
                
                logger.warning(
                    f"Flagged excessive actions: {action_type} for {merchant_id}",
                    extra={
                        "merchant_id": merchant_id,
                        "action_type": action_type,
                        "count": current_count,
                        "threshold": threshold
                    }
                )
            
            return should_flag
            
        except Exception as e:
            logger.error(f"Failed to flag excessive actions: {e}", exc_info=True)
            return False
    
    async def is_flagged(
        self,
        merchant_id: str,
        action_type: str
    ) -> bool:
        """
        Check if merchant is flagged for excessive actions.
        
        Args:
            merchant_id: Merchant identifier
            action_type: Type of action
            
        Returns:
            True if flagged, False otherwise
        """
        try:
            client = await self._get_redis_client()
            
            flag_key = f"ratelimit:flagged:{merchant_id}:{action_type}"
            is_flagged = await client.exists(flag_key)
            
            return bool(is_flagged)
            
        except Exception as e:
            logger.error(f"Failed to check flag status: {e}", exc_info=True)
            return False
    
    async def reset_rate_limit(
        self,
        merchant_id: str,
        action_type: str
    ) -> bool:
        """
        Reset rate limit for a merchant and action type.
        
        Args:
            merchant_id: Merchant identifier
            action_type: Type of action
            
        Returns:
            True if reset successful, False otherwise
        """
        try:
            client = await self._get_redis_client()
            
            # Delete rate limit key
            key = f"ratelimit:action:{action_type}:{merchant_id}"
            await client.delete(key)
            
            # Delete flag key
            flag_key = f"ratelimit:flagged:{merchant_id}:{action_type}"
            await client.delete(flag_key)
            
            logger.info(
                f"Reset rate limit: {action_type} for {merchant_id}",
                extra={
                    "merchant_id": merchant_id,
                    "action_type": action_type
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}", exc_info=True)
            return False
    
    async def get_rate_limit_status(
        self,
        merchant_id: str,
        action_type: str
    ) -> dict:
        """
        Get current rate limit status.
        
        Args:
            merchant_id: Merchant identifier
            action_type: Type of action
            
        Returns:
            Dictionary with rate limit status
        """
        try:
            client = await self._get_redis_client()
            
            key = f"ratelimit:action:{action_type}:{merchant_id}"
            
            # Get current count
            current_count = await client.get(key)
            current_count = int(current_count) if current_count else 0
            
            # Get TTL
            ttl = await client.ttl(key)
            
            # Get limit
            limit = self.default_limits.get(action_type, 10)
            
            # Check if flagged
            is_flagged = await self.is_flagged(merchant_id, action_type)
            
            return {
                "merchant_id": merchant_id,
                "action_type": action_type,
                "current_count": current_count,
                "limit": limit,
                "remaining": max(0, limit - current_count),
                "reset_in_seconds": ttl if ttl > 0 else 0,
                "is_flagged": is_flagged
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}", exc_info=True)
            return {
                "merchant_id": merchant_id,
                "action_type": action_type,
                "error": str(e)
            }
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    redis_client: Optional[redis.Redis] = None
) -> RateLimiter:
    """
    Get rate limiter instance.
    
    Args:
        redis_client: Optional Redis client
        
    Returns:
        Rate limiter instance
    """
    if redis_client:
        return RateLimiter(redis_client)
    
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
