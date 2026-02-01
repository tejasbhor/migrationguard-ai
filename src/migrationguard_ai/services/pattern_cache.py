"""
Pattern cache service for fast pattern lookups.

This module provides caching for patterns using Redis with Elasticsearch fallback.
Implements a two-tier caching strategy:
1. Redis for fast in-memory lookups
2. Elasticsearch for persistent storage and search
"""

from typing import Optional
from datetime import datetime

from migrationguard_ai.core.schemas import Pattern
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.services.redis_client import RedisClient
from migrationguard_ai.services.elasticsearch_client import ElasticsearchClient

logger = get_logger(__name__)


class PatternCache:
    """
    Two-tier pattern cache with Redis and Elasticsearch.
    
    Provides:
    - Fast lookups from Redis cache
    - Fallback to Elasticsearch for cache misses
    - Automatic cache population
    - TTL management for cache entries
    """
    
    def __init__(
        self,
        redis_client: RedisClient,
        es_client: ElasticsearchClient,
        cache_ttl: int = 3600,  # 1 hour default TTL
    ):
        """
        Initialize pattern cache.
        
        Args:
            redis_client: Redis client for caching
            es_client: Elasticsearch client for persistent storage
            cache_ttl: Cache TTL in seconds (default: 3600)
        """
        self.redis_client = redis_client
        self.es_client = es_client
        self.cache_ttl = cache_ttl
        self.cache_key_prefix = "pattern:"
    
    async def get_pattern(
        self,
        pattern_id: str,
    ) -> Optional[Pattern]:
        """
        Get a pattern by ID from cache or storage.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Optional[Pattern]: Pattern or None if not found
        """
        cache_key = self._make_cache_key(pattern_id)
        
        try:
            # Try Redis cache first
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                logger.debug("Pattern found in cache", pattern_id=pattern_id)
                return Pattern(**cached_data)
            
            # Cache miss - fetch from Elasticsearch
            logger.debug("Pattern cache miss", pattern_id=pattern_id)
            pattern_data = await self.es_client.get_document(
                index_name="patterns",
                doc_id=pattern_id,
            )
            
            if pattern_data:
                pattern = Pattern(**pattern_data)
                
                # Populate cache
                await self._cache_pattern(pattern)
                
                logger.debug("Pattern loaded from Elasticsearch", pattern_id=pattern_id)
                return pattern
            
            logger.debug("Pattern not found", pattern_id=pattern_id)
            return None
            
        except Exception as e:
            logger.error(
                "Failed to get pattern",
                pattern_id=pattern_id,
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def store_pattern(
        self,
        pattern: Pattern,
    ) -> bool:
        """
        Store a pattern in both cache and persistent storage.
        
        Args:
            pattern: Pattern to store
            
        Returns:
            bool: True if successful
        """
        try:
            # Store in Elasticsearch
            await self.es_client.index_document(
                index_name="patterns",
                document=pattern.model_dump(mode="json"),
                doc_id=pattern.pattern_id,
            )
            
            # Cache in Redis
            await self._cache_pattern(pattern)
            
            logger.info("Pattern stored", pattern_id=pattern.pattern_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to store pattern",
                pattern_id=pattern.pattern_id,
                error=str(e),
                exc_info=True,
            )
            return False
    
    async def update_pattern(
        self,
        pattern_id: str,
        updates: dict,
    ) -> Optional[Pattern]:
        """
        Update a pattern in storage and invalidate cache.
        
        Args:
            pattern_id: Pattern ID
            updates: Fields to update
            
        Returns:
            Optional[Pattern]: Updated pattern or None if not found
        """
        try:
            # Update in Elasticsearch
            success = await self.es_client.update_document(
                index_name="patterns",
                doc_id=pattern_id,
                partial_doc=updates,
            )
            
            if not success:
                logger.warning("Pattern not found for update", pattern_id=pattern_id)
                return None
            
            # Invalidate cache
            await self.invalidate_pattern(pattern_id)
            
            # Fetch updated pattern
            pattern = await self.get_pattern(pattern_id)
            
            logger.info("Pattern updated", pattern_id=pattern_id)
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to update pattern",
                pattern_id=pattern_id,
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def invalidate_pattern(
        self,
        pattern_id: str,
    ) -> bool:
        """
        Invalidate a pattern in the cache.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            bool: True if invalidated
        """
        try:
            cache_key = self._make_cache_key(pattern_id)
            await self.redis_client.delete(cache_key)
            
            logger.debug("Pattern cache invalidated", pattern_id=pattern_id)
            return True
            
        except Exception as e:
            logger.error(
                "Failed to invalidate pattern cache",
                pattern_id=pattern_id,
                error=str(e),
            )
            return False
    
    async def get_patterns_by_type(
        self,
        pattern_type: str,
        limit: int = 100,
    ) -> list[Pattern]:
        """
        Get patterns by type from Elasticsearch.
        
        Args:
            pattern_type: Type of patterns to retrieve
            limit: Maximum number of patterns to return
            
        Returns:
            list[Pattern]: List of patterns
        """
        try:
            query = {
                "term": {"pattern_type": pattern_type}
            }
            
            response = await self.es_client.search(
                index_name="patterns",
                query=query,
                size=limit,
                sort=[{"last_seen": {"order": "desc"}}],
            )
            
            patterns = []
            for hit in response.get("hits", {}).get("hits", []):
                try:
                    pattern = Pattern(**hit["_source"])
                    patterns.append(pattern)
                    
                    # Cache each pattern
                    await self._cache_pattern(pattern)
                except Exception as e:
                    logger.warning(
                        "Failed to parse pattern",
                        pattern_id=hit.get("_id"),
                        error=str(e),
                    )
            
            logger.info(
                "Patterns retrieved by type",
                pattern_type=pattern_type,
                count=len(patterns),
            )
            return patterns
            
        except Exception as e:
            logger.error(
                "Failed to get patterns by type",
                pattern_type=pattern_type,
                error=str(e),
                exc_info=True,
            )
            return []
    
    async def get_recent_patterns(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[Pattern]:
        """
        Get recent patterns from Elasticsearch.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of patterns to return
            
        Returns:
            list[Pattern]: List of recent patterns
        """
        try:
            query = {
                "range": {
                    "last_seen": {
                        "gte": f"now-{hours}h",
                        "lte": "now",
                    }
                }
            }
            
            response = await self.es_client.search(
                index_name="patterns",
                query=query,
                size=limit,
                sort=[{"last_seen": {"order": "desc"}}],
            )
            
            patterns = []
            for hit in response.get("hits", {}).get("hits", []):
                try:
                    pattern = Pattern(**hit["_source"])
                    patterns.append(pattern)
                    
                    # Cache each pattern
                    await self._cache_pattern(pattern)
                except Exception as e:
                    logger.warning(
                        "Failed to parse pattern",
                        pattern_id=hit.get("_id"),
                        error=str(e),
                    )
            
            logger.info(
                "Recent patterns retrieved",
                hours=hours,
                count=len(patterns),
            )
            return patterns
            
        except Exception as e:
            logger.error(
                "Failed to get recent patterns",
                hours=hours,
                error=str(e),
                exc_info=True,
            )
            return []
    
    async def get_patterns_by_merchant(
        self,
        merchant_id: str,
        limit: int = 50,
    ) -> list[Pattern]:
        """
        Get patterns affecting a specific merchant.
        
        Args:
            merchant_id: Merchant ID
            limit: Maximum number of patterns to return
            
        Returns:
            list[Pattern]: List of patterns
        """
        try:
            query = {
                "term": {"merchant_ids": merchant_id}
            }
            
            response = await self.es_client.search(
                index_name="patterns",
                query=query,
                size=limit,
                sort=[{"confidence": {"order": "desc"}}],
            )
            
            patterns = []
            for hit in response.get("hits", {}).get("hits", []):
                try:
                    pattern = Pattern(**hit["_source"])
                    patterns.append(pattern)
                    
                    # Cache each pattern
                    await self._cache_pattern(pattern)
                except Exception as e:
                    logger.warning(
                        "Failed to parse pattern",
                        pattern_id=hit.get("_id"),
                        error=str(e),
                    )
            
            logger.info(
                "Patterns retrieved for merchant",
                merchant_id=merchant_id,
                count=len(patterns),
            )
            return patterns
            
        except Exception as e:
            logger.error(
                "Failed to get patterns for merchant",
                merchant_id=merchant_id,
                error=str(e),
                exc_info=True,
            )
            return []
    
    async def _cache_pattern(
        self,
        pattern: Pattern,
    ) -> bool:
        """
        Cache a pattern in Redis.
        
        Args:
            pattern: Pattern to cache
            
        Returns:
            bool: True if successful
        """
        try:
            cache_key = self._make_cache_key(pattern.pattern_id)
            pattern_data = pattern.model_dump(mode="json")
            
            await self.redis_client.set(
                key=cache_key,
                value=pattern_data,
                ttl=self.cache_ttl,
            )
            
            logger.debug("Pattern cached", pattern_id=pattern.pattern_id)
            return True
            
        except Exception as e:
            logger.warning(
                "Failed to cache pattern",
                pattern_id=pattern.pattern_id,
                error=str(e),
            )
            return False
    
    def _make_cache_key(self, pattern_id: str) -> str:
        """Generate Redis cache key for a pattern."""
        return f"{self.cache_key_prefix}{pattern_id}"


# Singleton instance
_cache_instance: Optional[PatternCache] = None


async def get_pattern_cache(
    redis_client: RedisClient,
    es_client: ElasticsearchClient,
) -> PatternCache:
    """
    Get or create the pattern cache singleton.
    
    Args:
        redis_client: Redis client
        es_client: Elasticsearch client
        
    Returns:
        PatternCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = PatternCache(redis_client, es_client)
    
    return _cache_instance
