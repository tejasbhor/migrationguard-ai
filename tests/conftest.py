"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from migrationguard_ai.core.config import Settings, get_settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Get test settings."""
    settings = get_settings()
    # Override with test-specific settings
    settings.environment = "testing"
    settings.postgres_db = "migrationguard_test"
    settings.redis_db = 1
    return settings


@pytest_asyncio.fixture
async def db_engine(test_settings: Settings):
    """Create test database engine."""
    engine = create_async_engine(
        test_settings.database_url,
        echo=test_settings.debug,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    producer = MagicMock()
    producer.send = AsyncMock()
    producer.start = AsyncMock()
    producer.stop = AsyncMock()
    return producer


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=False)
    return client


@pytest.fixture
def mock_elasticsearch_client():
    """Mock Elasticsearch client for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.index = AsyncMock()
    client.search = AsyncMock(return_value={"hits": {"hits": []}})
    client.get = AsyncMock()
    return client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    from unittest.mock import AsyncMock, MagicMock
    
    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock()
    return client
