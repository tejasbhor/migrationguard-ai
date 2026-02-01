"""Kafka consumer wrapper for consuming messages."""

import asyncio
import json
from typing import Any, Callable, Optional

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.circuit_breaker import kafka_circuit_breaker
from migrationguard_ai.core.graceful_degradation import get_degradation_manager

logger = get_logger(__name__)


class KafkaConsumerWrapper:
    """Async Kafka consumer with error handling and offset management."""

    def __init__(
        self,
        topics: list[str],
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest",
    ) -> None:
        """
        Initialize Kafka consumer wrapper.

        Args:
            topics: List of topics to subscribe to
            group_id: Consumer group ID (defaults to config value)
            auto_offset_reset: Where to start consuming (earliest or latest)
        """
        self.settings = get_settings()
        self.topics = topics
        self.group_id = group_id or self.settings.kafka_consumer_group
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._started = False
        self._consuming = False
        self.degradation_manager = get_degradation_manager()

    async def start(self) -> None:
        """Start the Kafka consumer."""
        if self._started:
            logger.warning("Kafka consumer already started")
            return

        try:
            self.consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=False,  # Manual commit for better control
                value_deserializer=self._deserialize_message,
                max_poll_records=self.settings.signal_processing_batch_size,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            await self.consumer.start()
            self._started = True
            logger.info(
                "Kafka consumer started",
                topics=self.topics,
                group_id=self.group_id,
                bootstrap_servers=self.settings.kafka_bootstrap_servers,
            )
        except Exception as e:
            logger.error("Failed to start Kafka consumer", error=str(e))
            raise

    async def stop(self) -> None:
        """Stop the Kafka consumer."""
        if not self._started or self.consumer is None:
            logger.warning("Kafka consumer not started")
            return

        try:
            self._consuming = False
            await self.consumer.stop()
            self._started = False
            logger.info("Kafka consumer stopped")
        except Exception as e:
            logger.error("Error stopping Kafka consumer", error=str(e))
            raise

    async def consume(
        self,
        handler: Callable[[dict[str, Any]], Any],
        batch_size: int = 1,
    ) -> None:
        """
        Consume messages and process them with the provided handler.

        Args:
            handler: Async function to process each message
            batch_size: Number of messages to process in a batch

        Raises:
            RuntimeError: If consumer is not started
        """
        if not self._started or self.consumer is None:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        self._consuming = True
        logger.info("Starting message consumption", batch_size=batch_size)

        try:
            while self._consuming:
                # Fetch messages
                messages = await self.consumer.getmany(
                    timeout_ms=1000,
                    max_records=batch_size,
                )

                if not messages:
                    await asyncio.sleep(0.1)
                    continue

                # Process messages by partition
                for topic_partition, records in messages.items():
                    logger.debug(
                        "Processing messages",
                        topic=topic_partition.topic,
                        partition=topic_partition.partition,
                        count=len(records),
                    )

                    for record in records:
                        try:
                            # Process message
                            await handler(record.value)

                            logger.debug(
                                "Message processed",
                                topic=record.topic,
                                partition=record.partition,
                                offset=record.offset,
                            )

                        except Exception as e:
                            logger.error(
                                "Error processing message",
                                topic=record.topic,
                                partition=record.partition,
                                offset=record.offset,
                                error=str(e),
                            )
                            # Continue processing other messages
                            continue

                    # Commit offsets after processing batch
                    try:
                        await self.consumer.commit()
                        logger.debug(
                            "Offsets committed",
                            topic=topic_partition.topic,
                            partition=topic_partition.partition,
                        )
                    except Exception as e:
                        logger.error(
                            "Error committing offsets",
                            topic=topic_partition.topic,
                            partition=topic_partition.partition,
                            error=str(e),
                        )

        except asyncio.CancelledError:
            logger.info("Message consumption cancelled")
            raise
        except Exception as e:
            logger.error("Error in message consumption loop", error=str(e))
            raise

    @kafka_circuit_breaker
    async def consume_one(self) -> Optional[dict[str, Any]]:
        """
        Consume a single message.

        Returns:
            Message data or None if no message available

        Raises:
            RuntimeError: If consumer is not started
        """
        if not self._started or self.consumer is None:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        try:
            # Fetch one message with timeout
            message = await self.consumer.getone()

            if message:
                logger.debug(
                    "Message consumed",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                )
                
                # Mark Kafka as healthy
                self.degradation_manager.set_degraded("kafka", False)
                
                return message.value

            return None

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error("Error consuming message", error=str(e))
            
            # Mark Kafka as degraded
            self.degradation_manager.set_degraded("kafka", True)
            raise

    async def commit(self) -> None:
        """Manually commit current offsets."""
        if not self._started or self.consumer is None:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        try:
            await self.consumer.commit()
            logger.debug("Offsets committed manually")
        except Exception as e:
            logger.error("Error committing offsets", error=str(e))
            raise

    async def seek_to_beginning(self) -> None:
        """Seek to the beginning of all assigned partitions."""
        if not self._started or self.consumer is None:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        try:
            await self.consumer.seek_to_beginning()
            logger.info("Seeked to beginning of all partitions")
        except Exception as e:
            logger.error("Error seeking to beginning", error=str(e))
            raise

    async def seek_to_end(self) -> None:
        """Seek to the end of all assigned partitions."""
        if not self._started or self.consumer is None:
            raise RuntimeError("Kafka consumer not started. Call start() first.")

        try:
            await self.consumer.seek_to_end()
            logger.info("Seeked to end of all partitions")
        except Exception as e:
            logger.error("Error seeking to end", error=str(e))
            raise

    @staticmethod
    def _deserialize_message(message_bytes: bytes) -> dict[str, Any]:
        """
        Deserialize message from JSON bytes.

        Args:
            message_bytes: JSON-encoded bytes

        Returns:
            Deserialized message data
        """
        try:
            return json.loads(message_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Failed to deserialize message", error=str(e))
            raise

    async def __aenter__(self) -> "KafkaConsumerWrapper":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()


def create_consumer(
    topics: list[str],
    group_id: Optional[str] = None,
    auto_offset_reset: str = "earliest",
) -> KafkaConsumerWrapper:
    """
    Create a new Kafka consumer.

    Args:
        topics: List of topics to subscribe to
        group_id: Consumer group ID
        auto_offset_reset: Where to start consuming

    Returns:
        KafkaConsumerWrapper instance
    """
    return KafkaConsumerWrapper(
        topics=topics,
        group_id=group_id,
        auto_offset_reset=auto_offset_reset,
    )
