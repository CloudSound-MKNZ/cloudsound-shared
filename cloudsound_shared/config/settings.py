"""Environment configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os

# Determine environment from ENVIRONMENT variable or default to development
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()


class AppSettings(BaseSettings):
    """Application-wide settings."""

    model_config = SettingsConfigDict(
        env_file=f".env.{ENVIRONMENT}"
        if os.path.exists(f".env.{ENVIRONMENT}")
        else ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CloudSound"
    app_version: str = "1.0.0"
    debug: bool = ENVIRONMENT == "development"
    environment: str = ENVIRONMENT

    # Feature flags
    use_mock_apis: bool = ENVIRONMENT in ["development", "test"]
    seed_mock_data: bool = ENVIRONMENT in ["development", "test"]

    # API
    api_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Database (can be overridden by service-specific settings)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "cloudsound"
    postgres_password: str = "cloudsound_dev"
    postgres_db: str = "cloudsound"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_client_id: str = "cloudsound"

    # RabbitMQ
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "cloudsound"
    rabbitmq_password: str = "cloudsound_dev"
    rabbitmq_vhost: str = "/"

    # MinIO/S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "cloudsound-music"
    minio_secure: bool = False

    # Logging
    log_level: str = "DEBUG" if ENVIRONMENT == "development" else "INFO"
    log_format: str = "text" if ENVIRONMENT == "development" else "json"  # json or text

    # Service URLs (for inter-service communication)
    api_gateway_url: str = "http://localhost:8000"
    concert_management_url: str = "http://localhost:8001"
    event_manager_url: str = "http://localhost:8002"
    music_discovery_url: str = "http://localhost:8003"
    radio_streaming_url: str = "http://localhost:8004"
    admin_management_url: str = "http://localhost:8005"
    authentication_url: str = "http://localhost:8006"
    analytics_url: str = "http://localhost:8007"

    # Facebook API
    facebook_access_token: Optional[str] = None
    facebook_page_ids: str = ""  # Comma-separated page IDs
    facebook_api_version: str = "v24.0"
    facebook_poll_interval_minutes: int = 30
    facebook_fetch_days_back: int = (
        30  # Fetch events from past N days (default 30 days = 1 month)
    )


# Global settings instance
app_settings = AppSettings()
