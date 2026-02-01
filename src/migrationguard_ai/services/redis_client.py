"""
Redis client wrapper for caching and fast lookups.

This module provides a wrapper around the Redis client with:
- Connection management
- Key-value operations
- JSON serialization
- TTL management
- Error handling
"""

from typing import Any, Optional
import json

from redis.asyncio import Redis
from redis.exceptions import RedisError

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Async Redis client with caching capabilities."""

    def __init__(self) -> None:
        """Initialize Redis client wrapper."""
        self.settings = get_settings()
        self.client: Optional[Redis] = None
        self._started = False

    async def start(self) -> None:
        """Start the Redis client."""
        if self._started:
            logger.warning("Redis client already started")
            return

        try:
            self.client = Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                password=self.settings.redis_password if hasattr(self.settings, 'redis_password') else None,
                decode_responses=False,  # We'll handle encoding/decoding
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            
            # Test connection
            await self.client.ping()
            
            self._started = True
            logger.info(
                "Redis client started",
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
            )
        except Exception as e:
            logger.error("Failed to start Redis client", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Redis client."""
        if not self._started or self.client is None:
            logger.warning("Redis client not started")
            return

        try:
            await self.client.aclose()
            self._started = False
            logger.info("Redis client stopped")
        except Exception as e:
            logger.error("Error stopping Redis client", error=str(e))
            raise

    async def get(
        self,
        key: str,
    ) -> Optional[Any]:
        """
        Get a value from Redis.

        Args:
            key: Redis key

        Returns:
            Optional[Any]: Deserialized value or None if not found

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            value = await self.client.get(key)
            if value is None:
                return None
            
            # Deserialize JSON
            return json.loads(value)

        except json.JSONDecodeError as e:
            logger.error("Failed to deserialize value", key=key, error=str(e))
            return None
        except RedisError as e:
            logger.error("Redis get failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in get", key=key, error=str(e))
            raise

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in Redis.

        Args:
            key: Redis key
            value: Value to store (will be JSON serialized)
            ttl: Optional time-to-live in seconds

        Returns:
            bool: True if successful

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            # Serialize to JSON
            serialized = json.dumps(value, default=str)
            
            if ttl:
                await self.client.setex(key, ttl, serialized)
            else:
                await self.client.set(key, serialized)
            
            logger.debug("Value set in Redis", key=key, ttl=ttl)
            return True

        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize value", key=key, error=str(e))
            raise
        except RedisError as e:
            logger.error("Redis set failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in set", key=key, error=str(e))
            raise

    async def delete(
        self,
        key: str,
    ) -> bool:
        """
        Delete a key from Redis.

        Args:
            key: Redis key

        Returns:
            bool: True if key was deleted, False if not found

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            result = await self.client.delete(key)
            logger.debug("Key deleted from Redis", key=key, deleted=result > 0)
            return result > 0

        except RedisError as e:
            logger.error("Redis delete failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in delete", key=key, error=str(e))
            raise

    async def exists(
        self,
        key: str,
    ) -> bool:
        """
        Check if a key exists in Redis.

        Args:
            key: Redis key

        Returns:
            bool: True if key exists

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            result = await self.client.exists(key)
            return result > 0

        except RedisError as e:
            logger.error("Redis exists failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in exists", key=key, error=str(e))
            raise

    async def expire(
        self,
        key: str,
        ttl: int,
    ) -> bool:
        """
        Set TTL on an existing key.

        Args:
            key: Redis key
            ttl: Time-to-live in seconds

        Returns:
            bool: True if TTL was set

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            result = await self.client.expire(key, ttl)
            logger.debug("TTL set on key", key=key, ttl=ttl)
            return result

        except RedisError as e:
            logger.error("Redis expire failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in expire", key=key, error=str(e))
            raise

    async def mget(
        self,
        keys: list[str],
    ) -> list[Optional[Any]]:
        """
        Get multiple values from Redis.

        Args:
            keys: List of Redis keys

        Returns:
            list[Optional[Any]]: List of deserialized values (None for missing keys)

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            values = await self.client.mget(keys)
            
            # Deserialize each value
            result = []
            for value in values:
                if value is None:
                    result.append(None)
                else:
                    try:
                        result.append(json.loads(value))
                    except json.JSONDecodeError:
                        result.append(None)
            
            return result

        except RedisError as e:
            logger.error("Redis mget failed", keys=keys, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in mget", keys=keys, error=str(e))
            raise

    async def mset(
        self,
        mapping: dict[str, Any],
    ) -> bool:
        """
        Set multiple key-value pairs in Redis.

        Args:
            mapping: Dictionary of key-value pairs

        Returns:
            bool: True if successful

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            # Serialize all values
            serialized_mapping = {
                key: json.dumps(value, default=str)
                for key, value in mapping.items()
            }
            
            await self.client.mset(serialized_mapping)
            logger.debug("Multiple values set in Redis", count=len(mapping))
            return True

        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize values", error=str(e))
            raise
        except RedisError as e:
            logger.error("Redis mset failed", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in mset", error=str(e))
            raise

    async def incr(
        self,
        key: str,
        amount: int = 1,
    ) -> int:
        """
        Increment a counter in Redis.

        Args:
            key: Redis key
            amount: Amount to increment by (default: 1)

        Returns:
            int: New value after increment

        Raises:
            RuntimeError: If client is not started
        """
        if not self._started or self.client is None:
            raise RuntimeError("Redis client not started. Call start() first.")

        try:
            result = await self.client.incrby(key, amount)
            logger.debug("Counter incremented", key=key, amount=amount, new_value=result)
            return result

        except RedisError as e:
            logger.error("Redis incr failed", key=key, error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in incr", key=key, error=str(e))
            raise

    async def __aenter__(self) -> "RedisClient":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


# Singleton instance
_client_instance: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    Get or create the Redis client singleton.

    Returns:
        RedisClient instance
    """
    global _client_instance

    if _client_instance is None:
        _client_instance = RedisClient()
        await _client_instance.start()

    return _client_instance


async def close_redis_client() -> None:
    """Close the Redis client singleton."""
    global _client_instance

    if _client_instance is not None:
        await _client_instance.stop()
        _client_instance = None
