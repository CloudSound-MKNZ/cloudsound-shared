"""
Tenant-aware database sessions for multitenancy.

This module provides three approaches:
1. Row-level filtering (TenantAwareSession) - Automatic WHERE tenant_id = X
2. Schema-level routing (SchemaRouter) - SET search_path TO tenant_schema
3. Database-level routing (DatabaseRouter) - Connect to tenant-specific database
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy import event, text
from sqlalchemy.orm import Session, Query
from typing import AsyncGenerator, Optional, Dict, Any
from contextlib import asynccontextmanager
import structlog

from cloudsound_shared.config.settings import app_settings
from cloudsound_shared.multitenancy.context import (
    get_current_tenant,
    get_current_tenant_id,
    TenantContext,
)
from cloudsound_shared.db.pool import db_settings

logger = structlog.get_logger(__name__)


# =============================================================================
# Scheme 1: Row-Level Multitenancy (Discriminator Column)
# =============================================================================

class TenantAwareSession(AsyncSession):
    """
    Session that automatically filters queries by tenant_id.
    
    This is the simplest multitenancy approach - all tenants share the same
    tables, but queries are automatically filtered by tenant_id.
    
    Pros:
    - Simple implementation
    - Easy migrations
    - Shared resources efficient
    
    Cons:
    - No hard isolation between tenants
    - Complex queries with many JOINs
    - Risk of data leakage if filter is bypassed
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tenant_id: Optional[str] = None
    
    @property
    def tenant_id(self) -> Optional[str]:
        """Get tenant ID from context or explicit setting."""
        if self._tenant_id:
            return self._tenant_id
        return get_current_tenant_id()
    
    @tenant_id.setter
    def tenant_id(self, value: str):
        """Explicitly set tenant ID for this session."""
        self._tenant_id = value


# Listener to automatically add tenant_id filter to queries
@event.listens_for(Query, "before_compile", retval=True)
def add_tenant_filter(query):
    """
    Automatically add tenant_id filter to queries on tenant-aware models.
    
    This is a safety net - the middleware should set tenant context,
    and this filter ensures queries don't leak across tenants.
    """
    from cloudsound_shared.multitenancy.models import TenantMixin
    
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        return query
    
    # Check if query involves tenant-aware models
    for entity in query.column_descriptions:
        entity_class = entity.get("entity")
        if entity_class and issubclass(entity_class, TenantMixin):
            # Add tenant filter if not already present
            query = query.filter(entity_class.tenant_id == tenant_id)
    
    return query


async def get_tenant_db() -> AsyncGenerator[TenantAwareSession, None]:
    """
    FastAPI dependency for getting a tenant-aware database session.
    
    Usage:
        @app.get("/items")
        async def list_items(db: TenantAwareSession = Depends(get_tenant_db)):
            # Queries automatically filtered by current tenant
            items = await db.execute(select(Item))
            return items.scalars().all()
    """
    from cloudsound_shared.db.pool import engine
    
    session_factory = async_sessionmaker(
        engine,
        class_=TenantAwareSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# =============================================================================
# Scheme 2: Schema-Level Multitenancy
# =============================================================================

class SchemaRouter:
    """
    Routes database operations to tenant-specific PostgreSQL schemas.
    
    Each tenant has their own schema (e.g., tenant_acme, tenant_beta).
    All schemas share the same database but have isolated tables.
    
    Pros:
    - Good isolation between tenants
    - Easy per-tenant backups
    - Native PostgreSQL feature
    - Can have tenant-specific table modifications
    
    Cons:
    - More complex migrations
    - Schema proliferation
    - Connection overhead for schema switching
    """
    
    DEFAULT_SCHEMA = "public"
    TENANT_SCHEMA_PREFIX = "tenant_"
    
    def __init__(self, engine: AsyncEngine):
        self.engine = engine
        self._schema_cache: Dict[str, bool] = {}
    
    def get_schema_name(self, tenant_id: str) -> str:
        """Generate schema name for tenant."""
        return f"{self.TENANT_SCHEMA_PREFIX}{tenant_id.replace('-', '_')}"
    
    async def ensure_schema_exists(self, tenant_id: str) -> str:
        """
        Create tenant schema if it doesn't exist.
        
        Returns the schema name.
        """
        schema_name = self.get_schema_name(tenant_id)
        
        if schema_name in self._schema_cache:
            return schema_name
        
        async with self.engine.begin() as conn:
            # Create schema if not exists
            await conn.execute(
                text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            )
            logger.info("tenant_schema_created", schema=schema_name, tenant_id=tenant_id)
        
        self._schema_cache[schema_name] = True
        return schema_name
    
    async def create_tenant_tables(self, tenant_id: str, base_metadata) -> None:
        """
        Create all tables in tenant schema.
        
        Args:
            tenant_id: Tenant identifier
            base_metadata: SQLAlchemy metadata containing table definitions
        """
        schema_name = await self.ensure_schema_exists(tenant_id)
        
        async with self.engine.begin() as conn:
            # Set search path to tenant schema
            await conn.execute(text(f'SET search_path TO "{schema_name}"'))
            
            # Create tables
            await conn.run_sync(base_metadata.create_all)
            
            # Reset search path
            await conn.execute(text(f'SET search_path TO "{self.DEFAULT_SCHEMA}"'))
        
        logger.info("tenant_tables_created", schema=schema_name, tenant_id=tenant_id)
    
    async def drop_tenant_schema(self, tenant_id: str) -> None:
        """
        Drop tenant schema and all its data (use with caution!).
        """
        schema_name = self.get_schema_name(tenant_id)
        
        async with self.engine.begin() as conn:
            await conn.execute(
                text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            )
        
        self._schema_cache.pop(schema_name, None)
        logger.warning("tenant_schema_dropped", schema=schema_name, tenant_id=tenant_id)
    
    @asynccontextmanager
    async def session_for_tenant(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session for a specific tenant schema.
        
        Usage:
            async with schema_router.session_for_tenant("acme") as session:
                # All queries run against tenant_acme schema
                result = await session.execute(select(RadioStation))
        """
        schema_name = await self.ensure_schema_exists(tenant_id)
        
        session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        async with session_factory() as session:
            # Set search path to tenant schema
            await session.execute(text(f'SET search_path TO "{schema_name}", public'))
            
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                # Reset search path
                await session.execute(text(f'SET search_path TO "{self.DEFAULT_SCHEMA}"'))


async def get_schema_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for schema-based multitenancy.
    
    Usage:
        @app.get("/items")
        async def list_items(db: AsyncSession = Depends(get_schema_tenant_db)):
            # Queries run against tenant's schema
            items = await db.execute(select(Item))
            return items.scalars().all()
    """
    from cloudsound_shared.db.pool import engine
    
    tenant = get_current_tenant()
    if not tenant:
        raise RuntimeError("No tenant context set")
    
    router = SchemaRouter(engine)
    async with router.session_for_tenant(tenant.tenant_id) as session:
        yield session


# =============================================================================
# Scheme 3: Database-Level Multitenancy
# =============================================================================

class DatabaseRouter:
    """
    Routes database operations to tenant-specific databases.
    
    Each tenant has their own database. This provides maximum isolation
    but requires more infrastructure management.
    
    Pros:
    - Maximum isolation
    - Easy per-tenant backups and restores
    - Can have different database versions/configs per tenant
    - No risk of cross-tenant data leakage
    
    Cons:
    - Complex infrastructure
    - Connection pool per tenant
    - Expensive migrations
    - Resource intensive
    """
    
    def __init__(self, default_url: Optional[str] = None):
        self._engines: Dict[str, AsyncEngine] = {}
        self.default_url = default_url or db_settings.database_url
    
    def get_database_url(self, tenant: TenantContext) -> str:
        """
        Get database URL for tenant.
        
        Override this method to implement custom URL resolution logic.
        """
        if tenant.database_url:
            return tenant.database_url
        
        # Default: same host, different database name
        base_url = self.default_url.rsplit("/", 1)[0]
        return f"{base_url}/tenant_{tenant.tenant_id.replace('-', '_')}"
    
    async def get_engine(self, tenant: TenantContext) -> AsyncEngine:
        """Get or create engine for tenant."""
        if tenant.tenant_id not in self._engines:
            url = self.get_database_url(tenant)
            self._engines[tenant.tenant_id] = create_async_engine(
                url,
                pool_size=5,  # Smaller pool per tenant
                max_overflow=10,
                pool_pre_ping=True,
            )
            logger.info(
                "tenant_engine_created",
                tenant_id=tenant.tenant_id,
            )
        return self._engines[tenant.tenant_id]
    
    async def create_tenant_database(self, tenant: TenantContext, base_metadata) -> None:
        """
        Create a new database for tenant.
        
        Note: This requires superuser privileges on PostgreSQL.
        """
        db_name = f"tenant_{tenant.tenant_id.replace('-', '_')}"
        
        # Connect to default database to create new one
        from cloudsound_shared.db.pool import engine
        
        async with engine.connect() as conn:
            # PostgreSQL requires autocommit for CREATE DATABASE
            await conn.execute(text("COMMIT"))
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        
        # Create tables in new database
        tenant_engine = await self.get_engine(tenant)
        async with tenant_engine.begin() as conn:
            await conn.run_sync(base_metadata.create_all)
        
        logger.info("tenant_database_created", database=db_name, tenant_id=tenant.tenant_id)
    
    @asynccontextmanager
    async def session_for_tenant(self, tenant: TenantContext) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session for a specific tenant's database.
        """
        engine = await self.get_engine(tenant)
        
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def close_all(self) -> None:
        """Close all tenant database connections."""
        for tenant_id, engine in self._engines.items():
            await engine.dispose()
            logger.info("tenant_engine_disposed", tenant_id=tenant_id)
        self._engines.clear()


# Global database router instance (for database-level multitenancy)
_database_router: Optional[DatabaseRouter] = None


def get_database_router() -> DatabaseRouter:
    """Get the global database router instance."""
    global _database_router
    if _database_router is None:
        _database_router = DatabaseRouter()
    return _database_router


async def get_database_tenant_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database-based multitenancy.
    
    Usage:
        @app.get("/items")
        async def list_items(db: AsyncSession = Depends(get_database_tenant_db)):
            # Queries run against tenant's database
            items = await db.execute(select(Item))
            return items.scalars().all()
    """
    tenant = get_current_tenant()
    if not tenant:
        raise RuntimeError("No tenant context set")
    
    router = get_database_router()
    async with router.session_for_tenant(tenant) as session:
        yield session

