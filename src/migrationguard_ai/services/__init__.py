"""Business logic services."""

from migrationguard_ai.services.kafka_producer import KafkaProducerWrapper, get_kafka_producer
from migrationguard_ai.services.kafka_consumer import KafkaConsumerWrapper
from migrationguard_ai.services.signal_normalizer import SignalNormalizer, get_signal_normalizer
from migrationguard_ai.services.elasticsearch_client import ElasticsearchClient, get_elasticsearch_client
from migrationguard_ai.services.redis_client import RedisClient, get_redis_client
from migrationguard_ai.services.pattern_detector import PatternDetector, get_pattern_detector
from migrationguard_ai.services.pattern_cache import PatternCache, get_pattern_cache
from migrationguard_ai.services.alert_manager import AlertManager, AlertSeverity, AlertChannel

__all__ = [
    "KafkaProducerWrapper",
    "get_kafka_producer",
    "KafkaConsumerWrapper",
    "SignalNormalizer",
    "get_signal_normalizer",
    "ElasticsearchClient",
    "get_elasticsearch_client",
    "RedisClient",
    "get_redis_client",
    "PatternDetector",
    "get_pattern_detector",
    "PatternCache",
    "get_pattern_cache",
    "AlertManager",
    "AlertSeverity",
    "AlertChannel",
]
