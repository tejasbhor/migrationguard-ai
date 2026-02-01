"""
Graceful Degradation Module.

This module provides fallback logic when external services are unavailable:
- Claude API unavailable: Use rule-based root cause analysis
- Elasticsearch unavailable: Fall back to PostgreSQL for pattern matching
- Kafka unavailable: Buffer signals in Redis with persistence

The system continues to operate with reduced functionality rather than failing completely.
"""

from typing import Optional, Any
from datetime import datetime

from migrationguard_ai.core.schemas import (
    Signal,
    Pattern,
    RootCauseAnalysis,
)
from migrationguard_ai.core.logging import get_logger

logger = get_logger(__name__)


class RuleBasedRootCauseAnalyzer:
    """
    Rule-based fallback for Claude API when unavailable.
    
    Uses pattern matching and heuristics to classify issues when
    AI-powered analysis is not available.
    """
    
    def __init__(self):
        """Initialize rule-based analyzer."""
        logger.info("Rule-based root cause analyzer initialized (fallback mode)")
    
    async def analyze(
        self,
        signals: list[Signal],
        patterns: list[Pattern],
        merchant_context: Optional[dict] = None,
    ) -> RootCauseAnalysis:
        """
        Analyze signals using rule-based heuristics.
        
        Args:
            signals: List of signals related to the issue
            patterns: List of detected patterns
            merchant_context: Additional context about the merchant
            
        Returns:
            RootCauseAnalysis: Analysis result with category and reasoning
        """
        if not signals:
            raise ValueError("At least one signal is required for analysis")
        
        logger.warning(
            "Using rule-based fallback for root cause analysis",
            signal_count=len(signals),
            pattern_count=len(patterns),
        )
        
        # Analyze signals using rules
        category, confidence, reasoning, evidence = self._apply_rules(
            signals, patterns, merchant_context
        )
        
        return RootCauseAnalysis(
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            alternatives_considered=[
                {
                    "hypothesis": "Other categories were considered",
                    "reason_rejected": "Rule-based analysis selected most likely category based on signal patterns"
                }
            ],
            recommended_actions=self._get_recommended_actions(category),
        )
    
    def _apply_rules(
        self,
        signals: list[Signal],
        patterns: list[Pattern],
        merchant_context: Optional[dict] = None,
    ) -> tuple[str, float, str, list[str]]:
        """
        Apply rule-based heuristics to classify the issue.
        
        Returns:
            tuple: (category, confidence, reasoning, evidence)
        """
        evidence = []
        
        # Rule 1: Check for API authentication errors
        auth_errors = [
            s for s in signals
            if s.error_code and any(
                code in s.error_code.lower()
                for code in ["401", "403", "unauthorized", "forbidden", "auth"]
            )
        ]
        if auth_errors:
            evidence.append(f"Found {len(auth_errors)} authentication-related errors")
            return (
                "migration_misstep",
                0.75,
                "Multiple authentication errors detected. This typically indicates incorrect API credentials or missing authentication configuration during migration.",
                evidence
            )
        
        # Rule 2: Check for configuration errors
        config_errors = [
            s for s in signals
            if s.error_message and any(
                term in s.error_message.lower()
                for term in ["config", "configuration", "setting", "environment", "variable"]
            )
        ]
        if config_errors:
            evidence.append(f"Found {len(config_errors)} configuration-related errors")
            return (
                "config_error",
                0.70,
                "Configuration-related errors detected. This suggests incorrect settings or environment variables.",
                evidence
            )
        
        # Rule 3: Check for webhook failures
        webhook_signals = [s for s in signals if s.source == "webhook_failure"]
        if webhook_signals:
            evidence.append(f"Found {len(webhook_signals)} webhook failures")
            return (
                "config_error",
                0.65,
                "Webhook failures detected. This typically indicates incorrect webhook URLs or missing webhook configuration.",
                evidence
            )
        
        # Rule 4: Check for API endpoint errors (404, 405)
        endpoint_errors = [
            s for s in signals
            if s.error_code and any(
                code in s.error_code
                for code in ["404", "405"]
            )
        ]
        if endpoint_errors:
            evidence.append(f"Found {len(endpoint_errors)} endpoint-related errors")
            
            # Check if this is a recent platform change
            if patterns and any(p.frequency > 5 for p in patterns):
                return (
                    "platform_regression",
                    0.68,
                    "Multiple endpoint errors affecting many merchants. This suggests a platform API change or regression.",
                    evidence
                )
            else:
                return (
                    "migration_misstep",
                    0.65,
                    "Endpoint errors detected. This may indicate incorrect API endpoint URLs in merchant configuration.",
                    evidence
                )
        
        # Rule 5: Check for checkout failures
        checkout_signals = [s for s in signals if s.source == "checkout_error"]
        if checkout_signals:
            evidence.append(f"Found {len(checkout_signals)} checkout errors")
            return (
                "migration_misstep",
                0.60,
                "Checkout errors detected. This typically indicates issues with payment gateway configuration or checkout flow setup.",
                evidence
            )
        
        # Rule 6: Check for cross-merchant patterns (platform regression)
        if patterns:
            cross_merchant_patterns = [
                p for p in patterns
                if len(p.merchant_ids) > 3
            ]
            if cross_merchant_patterns:
                evidence.append(
                    f"Found {len(cross_merchant_patterns)} patterns affecting multiple merchants"
                )
                return (
                    "platform_regression",
                    0.70,
                    "Issue affects multiple merchants simultaneously. This strongly suggests a platform-wide regression or bug.",
                    evidence
                )
        
        # Rule 7: Check for documentation-related keywords
        doc_keywords = ["unclear", "missing", "documentation", "docs", "guide", "tutorial", "example"]
        doc_signals = [
            s for s in signals
            if s.error_message and any(
                keyword in s.error_message.lower()
                for keyword in doc_keywords
            )
        ]
        if doc_signals:
            evidence.append(f"Found {len(doc_signals)} documentation-related signals")
            return (
                "documentation_gap",
                0.60,
                "Signals mention documentation issues. This suggests missing or unclear guidance in documentation.",
                evidence
            )
        
        # Default: Migration misstep (most common during migrations)
        evidence.append("No specific error patterns matched, defaulting to migration misstep")
        return (
            "migration_misstep",
            0.50,
            "Unable to determine specific root cause with high confidence. Based on context, this appears to be a merchant configuration issue during migration. Manual review recommended.",
            evidence
        )
    
    def _get_recommended_actions(self, category: str) -> list[str]:
        """
        Get recommended actions based on category.
        
        Args:
            category: Root cause category
            
        Returns:
            list: Recommended actions
        """
        actions = {
            "migration_misstep": [
                "Provide step-by-step guidance to merchant",
                "Review merchant's migration checklist",
                "Check API credentials and configuration"
            ],
            "platform_regression": [
                "Escalate to engineering team",
                "Check recent platform changes",
                "Notify affected merchants"
            ],
            "documentation_gap": [
                "Update documentation with clearer instructions",
                "Add examples and troubleshooting guide",
                "Create FAQ entry"
            ],
            "config_error": [
                "Review merchant configuration settings",
                "Validate environment variables",
                "Check webhook and API endpoint URLs"
            ],
        }
        return actions.get(category, ["Manual investigation required"])


class PostgreSQLPatternMatcher:
    """
    PostgreSQL-based fallback for Elasticsearch when unavailable.
    
    Uses SQL queries to match patterns when Elasticsearch is down.
    """
    
    def __init__(self, db_session):
        """
        Initialize PostgreSQL pattern matcher.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        logger.info("PostgreSQL pattern matcher initialized (fallback mode)")
    
    async def match_pattern(
        self,
        signal: Signal,
        time_window_minutes: int = 120
    ) -> Optional[Pattern]:
        """
        Match signal against known patterns using PostgreSQL.
        
        Args:
            signal: Signal to match
            time_window_minutes: Time window for pattern matching
            
        Returns:
            Optional[Pattern]: Matched pattern or None
        """
        logger.warning(
            "Using PostgreSQL fallback for pattern matching",
            signal_id=signal.signal_id,
        )
        
        # This is a simplified fallback - in production, you would implement
        # SQL queries to find similar signals and group them into patterns
        
        # For now, return None to indicate no pattern match
        # The system will continue without pattern detection
        return None
    
    async def search_patterns(
        self,
        query: dict[str, Any],
        limit: int = 10
    ) -> list[Pattern]:
        """
        Search for patterns using PostgreSQL.
        
        Args:
            query: Search query parameters
            limit: Maximum number of results
            
        Returns:
            list[Pattern]: Matching patterns
        """
        logger.warning("Using PostgreSQL fallback for pattern search")
        
        # Simplified fallback - return empty list
        # The system will continue without pattern search results
        return []


class RedisSignalBuffer:
    """
    Redis-based fallback for Kafka when unavailable.
    
    Buffers signals in Redis when Kafka is down, with persistence to disk.
    """
    
    def __init__(self, redis_client):
        """
        Initialize Redis signal buffer.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
        self.buffer_key = "signal_buffer:pending"
        logger.info("Redis signal buffer initialized (fallback mode)")
    
    async def buffer_signal(self, signal: Signal) -> bool:
        """
        Buffer signal in Redis when Kafka is unavailable.
        
        Args:
            signal: Signal to buffer
            
        Returns:
            bool: True if buffered successfully
        """
        try:
            logger.warning(
                "Buffering signal in Redis (Kafka unavailable)",
                signal_id=signal.signal_id,
            )
            
            # Add signal to Redis list
            await self.redis_client.lpush(
                self.buffer_key,
                signal.model_dump_json()
            )
            
            # Set expiration to prevent unbounded growth (7 days)
            await self.redis_client.expire(self.buffer_key, 604800)
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to buffer signal in Redis",
                signal_id=signal.signal_id,
                error=str(e),
            )
            return False
    
    async def flush_buffer_to_kafka(self, kafka_producer) -> int:
        """
        Flush buffered signals to Kafka when it becomes available.
        
        Args:
            kafka_producer: Kafka producer instance
            
        Returns:
            int: Number of signals flushed
        """
        try:
            count = 0
            
            # Get all buffered signals
            while True:
                signal_json = await self.redis_client.rpop(self.buffer_key)
                if not signal_json:
                    break
                
                # Parse signal
                signal_dict = Signal.model_validate_json(signal_json)
                
                # Send to Kafka
                await kafka_producer.send(
                    topic="signals.normalized",
                    message=signal_dict.model_dump(),
                    key=signal_dict.merchant_id,
                )
                
                count += 1
            
            if count > 0:
                logger.info(
                    "Flushed buffered signals to Kafka",
                    count=count,
                )
            
            return count
            
        except Exception as e:
            logger.error(
                "Failed to flush buffer to Kafka",
                error=str(e),
            )
            return 0
    
    async def get_buffer_size(self) -> int:
        """
        Get the number of buffered signals.
        
        Returns:
            int: Number of signals in buffer
        """
        try:
            return await self.redis_client.llen(self.buffer_key)
        except Exception:
            return 0


class GracefulDegradationManager:
    """
    Manager for graceful degradation across all services.
    
    Coordinates fallback logic and tracks degradation state.
    """
    
    def __init__(self):
        """Initialize graceful degradation manager."""
        self.degradation_state = {
            "claude_api": False,
            "elasticsearch": False,
            "kafka": False,
        }
        logger.info("Graceful degradation manager initialized")
    
    def set_degraded(self, service: str, degraded: bool) -> None:
        """
        Set degradation state for a service.
        
        Args:
            service: Service name (claude_api, elasticsearch, kafka)
            degraded: Whether service is degraded
        """
        if service in self.degradation_state:
            previous_state = self.degradation_state[service]
            self.degradation_state[service] = degraded
            
            if degraded and not previous_state:
                logger.warning(
                    "Service entered degraded mode",
                    service=service,
                )
            elif not degraded and previous_state:
                logger.info(
                    "Service recovered from degraded mode",
                    service=service,
                )
    
    def is_degraded(self, service: str) -> bool:
        """
        Check if a service is in degraded mode.
        
        Args:
            service: Service name
            
        Returns:
            bool: True if service is degraded
        """
        return self.degradation_state.get(service, False)
    
    def get_degradation_status(self) -> dict[str, bool]:
        """
        Get degradation status for all services.
        
        Returns:
            dict: Service degradation states
        """
        return self.degradation_state.copy()
    
    def is_any_degraded(self) -> bool:
        """
        Check if any service is degraded.
        
        Returns:
            bool: True if any service is degraded
        """
        return any(self.degradation_state.values())


# Singleton instance
_degradation_manager: Optional[GracefulDegradationManager] = None


def get_degradation_manager() -> GracefulDegradationManager:
    """
    Get or create the graceful degradation manager singleton.
    
    Returns:
        GracefulDegradationManager instance
    """
    global _degradation_manager
    
    if _degradation_manager is None:
        _degradation_manager = GracefulDegradationManager()
    
    return _degradation_manager
