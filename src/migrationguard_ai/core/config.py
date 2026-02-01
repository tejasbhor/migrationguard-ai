"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "MigrationGuard AI"
    app_version: str = "0.1.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    
    # Expose as uppercase for compatibility
    @property
    def CORS_ORIGINS(self) -> list[str]:
        """Get CORS origins (uppercase alias)."""
        return self.cors_origins
    
    @property
    def ENVIRONMENT(self) -> str:
        """Get environment (uppercase alias)."""
        return self.environment

    # Database - PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "migrationguard"
    postgres_password: str = "changeme"
    postgres_db: str = "migrationguard"
    postgres_pool_size: int = 20
    postgres_max_overflow: int = 10

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Kafka
    kafka_bootstrap_servers: list[str] = Field(default_factory=lambda: ["localhost:9092"])
    kafka_consumer_group: str = "migrationguard-consumers"
    kafka_auto_offset_reset: str = "earliest"

    # Elasticsearch
    elasticsearch_hosts: list[str] = Field(default_factory=lambda: ["http://localhost:9200"])
    elasticsearch_index_prefix: str = "migrationguard"

    @property
    def elasticsearch_url(self) -> str:
        """Get the first Elasticsearch host URL."""
        return self.elasticsearch_hosts[0] if self.elasticsearch_hosts else "http://localhost:9200"

    # Anthropic API
    anthropic_api_key: str = Field(default="", description="Anthropic API key for Claude")
    anthropic_model: str = "claude-sonnet-4.5-20250514"
    anthropic_max_tokens: int = 4096
    anthropic_temperature: float = 0.3

    # Google Gemini API
    gemini_api_key: str = Field(default="", description="Google AI Studio API key for Gemini")
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_tokens: int = 4096
    gemini_temperature: float = 0.3

    # Agent Configuration
    agent_confidence_threshold: float = 0.7
    agent_high_risk_approval_required: bool = True
    agent_max_retries: int = 3
    agent_retry_backoff_multiplier: float = 1.0
    agent_retry_backoff_min: float = 2.0
    agent_retry_backoff_max: float = 10.0

    # Performance
    signal_processing_batch_size: int = 100
    pattern_detection_window_seconds: int = 120
    max_signals_per_minute: int = 10000

    # Security
    jwt_secret_key: str = Field(default="changeme-in-production", description="JWT secret key")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    # Monitoring
    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    # Alerting - Email
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "alerts@migrationguard.ai"
    alert_email_recipients: str = "ops@example.com"

    # Alerting - Slack
    slack_webhook_url: str | None = None

    # Alerting - PagerDuty
    pagerduty_integration_key: str | None = None

    # Expose uppercase aliases for compatibility
    @property
    def APP_NAME(self) -> str:
        """Get app name (uppercase alias)."""
        return self.app_name
    
    @property
    def APP_VERSION(self) -> str:
        """Get app version (uppercase alias)."""
        return self.app_version
    
    @property
    def LOG_LEVEL(self) -> str:
        """Get log level (uppercase alias)."""
        return self.log_level
    
    @property
    def SMTP_HOST(self) -> str | None:
        """Get SMTP host (uppercase alias)."""
        return self.smtp_host
    
    @property
    def SMTP_PORT(self) -> int:
        """Get SMTP port (uppercase alias)."""
        return self.smtp_port
    
    @property
    def SMTP_USE_TLS(self) -> bool:
        """Get SMTP TLS setting (uppercase alias)."""
        return self.smtp_use_tls
    
    @property
    def SMTP_USERNAME(self) -> str | None:
        """Get SMTP username (uppercase alias)."""
        return self.smtp_username
    
    @property
    def SMTP_PASSWORD(self) -> str | None:
        """Get SMTP password (uppercase alias)."""
        return self.smtp_password
    
    @property
    def SMTP_FROM_EMAIL(self) -> str:
        """Get SMTP from email (uppercase alias)."""
        return self.smtp_from_email
    
    @property
    def ALERT_EMAIL_RECIPIENTS(self) -> str:
        """Get alert email recipients (uppercase alias)."""
        return self.alert_email_recipients
    
    @property
    def SLACK_WEBHOOK_URL(self) -> str | None:
        """Get Slack webhook URL (uppercase alias)."""
        return self.slack_webhook_url
    
    @property
    def PAGERDUTY_INTEGRATION_KEY(self) -> str | None:
        """Get PagerDuty integration key (uppercase alias)."""
        return self.pagerduty_integration_key


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
