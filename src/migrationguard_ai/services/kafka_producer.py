"""Kafka producer wrapper for publishing messages."""

import json
from typing import Any, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.circuit_breaker import kafka_circuit_breaker
from migrationguard_ai.core.graceful_degradation import (
    RedisSignalBuffer,
    get_degradation_manager,
)
from migrationguard_ai.core.schemas import Signal

logger = get_logger(__name__)


class KafkaProducerWrapper:
    """Async Kafka producer with error handling and retry logic."""

    def __init__(self, redis_client=None) -> None:
        """
        Initialize Kafka producer wrapper.
        
        Args:
            redis_client: Optional Redis client for fallback buffering
        """
        self.settings = get_settings()
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False
        self.degradation_manager = get_degradation_manager()
        
        # Initialize Redis fallback if redis_client provided
        self.redis_buffer = None
        if redis_client:
            self.redis_buffer = RedisSignalBuffer(redis_client)

    async def start(self) -> None:
        """Start the Kafka producer."""
        if self._started:
            logger.warning("Kafka producer already started")
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                value_serializer=self._serialize_message,
                compression_type="gzip",
                acks="all",  # Wait for all replicas to acknowledge
                max_in_flight_requests_per_connection=5,
                enable_idempotence=True,  # Ensure exactly-once semantics
            )
            await self.producer.start()
            self._started = True
            logger.info(
                "Kafka producer started",
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
            )
        except Exception as e:
            logger.error("Failed to start Kafka producer", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if not self._started or self.producer is None:
            logger.warning("Kafka producer not started")
            return

        try:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")
        except Exception as e:
            logger.error("Error stopping Kafka producer", error=str(e))
            raise

    @kafka_circuit_breaker
    async def send(
        self,
        topic: str,
        message: dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
    ) -> None:
        """
        Send a message to a Kafka topic.

        Args:
            topic: Kafka topic name
            message: Message data (will be JSON serialized)
            key: Optional message key for partitioning
            partition: Optional specific partition to send to

        Raises:
            RuntimeError: If producer is not started
            KafkaError: If message send fails
        """
        if not self._started or self.producer is None:
            raise RuntimeError("Kafka producer not started. Call start() first.")

        try:
            # Encode key if provided
            key_bytes = key.encode("utf-8") if key else None

            # Send message
            future = await self.producer.send(
                topic=topic,
                value=message,
                key=key_bytes,
                partition=partition,
            )

            # Wait for acknowledgment
            record_metadata = await future

            logger.debug(
                "Message sent to Kafka",
                topic=topic,
                partition=record_metadata.partition,
                offset=record_metadata.offset,
                key=key,
            )
            
            # Mark Kafka as healthy
            self.degradation_manager.set_degraded("kafka", False)

        except KafkaError as e:
            logger.error(
                "Failed to send message to Kafka",
                topic=topic,
                error=str(e),
                key=key,
            )
            
            # Mark Kafka as degraded
            self.degradation_manager.set_degraded("kafka", True)
            
            # Try Redis buffer fallback for signal messages
            if self.redis_buffer and topic == "signals.normalized":
                logger.warning(
                    "Attempting Redis buffer fallback for signal",
                    topic=topic,
                    key=key,
                )
                try:
                    # Convert message to Signal and buffer it
                    signal = Signal(**message)
                    buffered = await self.redis_buffer.buffer_signal(signal)
                    if buffered:
                        logger.info(
                            "Signal buffered in Redis",
                            signal_id=signal.signal_id,
                        )
                        return  # Successfully buffered, don't raise
                except Exception as buffer_error:
                    logger.error(
                        "Redis buffer fallback also failed",
                        error=str(buffer_error),
                    )
            
            raise
        except Exception as e:
            logger.error(
                "Unexpected error sending message to Kafka",
                topic=topic,
                error=str(e),
                key=key,
            )
            
            # Mark Kafka as degraded
            self.degradation_manager.set_degraded("kafka", True)
            raise

    @kafka_circuit_breaker
    async def send_batch(
        self,
        topic: str,
        messages: list[dict[str, Any]],
        keys: Optional[list[str]] = None,
    ) -> None:
        """
        Send multiple messages to a Kafka topic.

        Args:
            topic: Kafka topic name
            messages: List of message data
            keys: Optional list of message keys (must match messages length)

        Raises:
            ValueError: If keys length doesn't match messages length
            RuntimeError: If producer is not started
            KafkaError: If any message send fails
        """
        if keys and len(keys) != len(messages):
            raise ValueError("Keys length must match messages length")

        if not self._started or self.producer is None:
            raise RuntimeError("Kafka producer not started. Call start() first.")

        try:
            # Send all messages
            futures = []
            for i, message in enumerate(messages):
                key = keys[i] if keys else None
                key_bytes = key.encode("utf-8") if key else None

                future = await self.producer.send(
                    topic=topic,
                    value=message,
                    key=key_bytes,
                )
                futures.append(future)

            # Wait for all acknowledgments
            for future in futures:
                await future

            logger.info(
                "Batch messages sent to Kafka",
                topic=topic,
                count=len(messages),
            )

        except KafkaError as e:
            logger.error(
                "Failed to send batch messages to Kafka",
                topic=topic,
                count=len(messages),
                error=str(e),
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error sending batch messages to Kafka",
                topic=topic,
                count=len(messages),
                error=str(e),
            )
            raise

    async def flush(self) -> None:
        """Flush any pending messages."""
        if not self._started or self.producer is None:
            raise RuntimeError("Kafka producer not started. Call start() first.")

        try:
            await self.producer.flush()
            logger.debug("Kafka producer flushed")
            
            # If Kafka is healthy and we have a Redis buffer, flush it
            if self.redis_buffer and not self.degradation_manager.is_degraded("kafka"):
                buffer_size = await self.redis_buffer.get_buffer_size()
                if buffer_size > 0:
                    logger.info(
                        "Flushing Redis buffer to Kafka",
                        buffer_size=buffer_size,
                    )
                    flushed_count = await self.redis_buffer.flush_buffer_to_kafka(self)
                    logger.info(
                        "Redis buffer flushed to Kafka",
                        flushed_count=flushed_count,
                    )
        except Exception as e:
            logger.error("Error flushing Kafka producer", error=str(e))
            raise

    @staticmethod
    def _serialize_message(message: dict[str, Any]) -> bytes:
        """
        Serialize message to JSON bytes.

        Args:
            message: Message data

        Returns:
            JSON-encoded bytes
        """
        return json.dumps(message, default=str).encode("utf-8")

    async def __aenter__(self) -> "KafkaProducerWrapper":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


# Singleton instance
_producer_instance: Optional[KafkaProducerWrapper] = None


async def get_kafka_producer() -> KafkaProducerWrapper:
    """
    Get or create the Kafka producer singleton.

    Returns:
        KafkaProducerWrapper instance
    """
    global _producer_instance

    if _producer_instance is None:
        _producer_instance = KafkaProducerWrapper()
        await _producer_instance.start()

    return _producer_instance


async def close_kafka_producer() -> None:
    """Close the Kafka producer singleton."""
    global _producer_instance

    if _producer_instance is not None:
        await _producer_instance.stop()
        _producer_instance = None
