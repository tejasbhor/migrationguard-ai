"""Test configuration management."""

import pytest

from migrationguard_ai.core.config import Settings, get_settings


def test_settings_creation():
    """Test that settings can be created with defaults."""
    settings = Settings()
    
    assert settings.app_name == "MigrationGuard AI"
    assert settings.app_version == "0.1.0"
    assert settings.environment in ["development", "staging", "production"]
    assert settings.api_port == 8000


def test_database_url_construction():
    """Test that database URL is constructed correctly."""
    settings = Settings(
        postgres_user="testuser",
        postgres_password="testpass",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="testdb",
    )
    
    expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
    assert settings.database_url == expected_url


def test_redis_url_construction():
    """Test that Redis URL is constructed correctly."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password=None,
    )
    
    expected_url = "redis://localhost:6379/0"
    assert settings.redis_url == expected_url


def test_redis_url_with_password():
    """Test that Redis URL includes password when provided."""
    settings = Settings(
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_password="secret",
    )
    
    expected_url = "redis://:secret@localhost:6379/0"
    assert settings.redis_url == expected_url


def test_get_settings_cached():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2


def test_agent_configuration():
    """Test agent-specific configuration."""
    settings = Settings()
    
    assert settings.agent_confidence_threshold == 0.7
    assert settings.agent_high_risk_approval_required is True
    assert settings.agent_max_retries == 3
    assert settings.agent_retry_backoff_multiplier == 1.0


def test_anthropic_configuration():
    """Test Anthropic API configuration."""
    settings = Settings()
    
    assert settings.anthropic_model == "claude-sonnet-4.5-20250514"
    assert settings.anthropic_max_tokens == 4096
    assert settings.anthropic_temperature == 0.3
