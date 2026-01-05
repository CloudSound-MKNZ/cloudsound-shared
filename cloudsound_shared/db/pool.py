"""Database connection pool configuration."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
import os
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_user: str = os.getenv("POSTGRES_USER", "cloudsound")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "cloudsound_dev")
    postgres_db: str = os.getenv("POSTGRES_DB", "cloudsound")
    postgres_pool_size: int = int(os.getenv("POSTGRES_POOL_SIZE", "10"))
    postgres_max_overflow: int = int(os.getenv("POSTGRES_MAX_OVERFLOW", "20"))
    
    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

# Global settings instance
db_settings = DatabaseSettings()

# Create async engine
engine = create_async_engine(
    db_settings.database_url,
    pool_size=db_settings.postgres_pool_size,
    max_overflow=db_settings.postgres_max_overflow,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

