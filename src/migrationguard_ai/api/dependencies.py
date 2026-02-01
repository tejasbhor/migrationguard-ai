"""
Dependency injection for FastAPI.

This module provides dependency injection functions for services
used across API endpoints.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from migrationguard_ai.services.kafka_producer import KafkaProducerWrapper, get_kafka_producer
from migrationguard_ai.services.signal_normalizer import SignalNormalizer, get_signal_normalizer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database session.
    
    This is a placeholder that should be replaced with actual database session management.
    For now, it yields None to allow the API to be imported without database setup.
    
    Yields:
        AsyncSession: Database session
    """
    # TODO: Implement actual database session management
    # from migrationguard_ai.db import get_session
    # async with get_session() as session:
    #     yield session
    yield None  # type: ignore


async def get_kafka_producer_dependency() -> AsyncGenerator[KafkaProducerWrapper, None]:
    """
    Dependency injection for Kafka producer.
    
    Yields:
        KafkaProducerWrapper: Kafka producer instance
    """
    producer = await get_kafka_producer()
    try:
        yield producer
    finally:
        # Cleanup if needed
        pass


def get_signal_normalizer_dependency() -> SignalNormalizer:
    """
    Dependency injection for signal normalizer.
    
    Returns:
        SignalNormalizer: Signal normalizer instance
    """
    return get_signal_normalizer()
