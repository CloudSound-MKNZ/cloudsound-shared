"""
Multitenancy module for CloudSound.

This module provides three multitenancy schemes:
1. Row-level (Discriminator Column) - All tenants share tables, filtered by tenant_id
2. Schema-level - Each tenant has its own PostgreSQL schema
3. Database-level - Each tenant has its own database

Choose based on your needs:
- Row-level: Simple, good for small number of tenants, shared resources
- Schema-level: Better isolation, easier backups per tenant, moderate complexity
- Database-level: Maximum isolation, complex management, best for enterprise

Quick Start:
    1. Add TenantMixin to your models
    2. Add TenantMiddleware to your FastAPI app
    3. Use get_tenant_db() as your session dependency

Example:
    from cloudsound_shared.multitenancy import TenantMixin, TenantMiddleware, get_tenant_db
    
    # 1. Update your model
    class RadioStation(Base, UUIDMixin, TimestampMixin, TenantMixin):
        __tablename__ = "radio_stations"
        name = Column(String(255), nullable=False)
    
    # 2. Add middleware to app
    app.add_middleware(TenantMiddleware)
    
    # 3. Use tenant-aware session
    @app.get("/stations")
    async def list_stations(db: AsyncSession = Depends(get_tenant_db)):
        result = await db.execute(select(RadioStation))
        return result.scalars().all()
"""

from cloudsound_shared.multitenancy.context import (
    TenantContext,
    get_current_tenant,
    get_current_tenant_id,
    set_current_tenant,
    clear_tenant_context,
    tenant_context,
    require_tenant,
)
from cloudsound_shared.multitenancy.middleware import (
    TenantMiddleware,
    TenantIdentificationStrategy,
)
from cloudsound_shared.multitenancy.models import (
    TenantMixin,
    TenantIsolatedMixin,
    Tenant,
)
from cloudsound_shared.multitenancy.session import (
    get_tenant_db,
    get_schema_tenant_db,
    get_database_tenant_db,
    TenantAwareSession,
    SchemaRouter,
    DatabaseRouter,
    get_database_router,
)
from cloudsound_shared.multitenancy.config import (
    MultitenancyScheme,
    TenantIdentificationMethod,
    MultitenancySettings,
    multitenancy_settings,
    is_multitenancy_enabled,
    get_multitenancy_scheme,
)

__all__ = [
    # Context
    "TenantContext",
    "get_current_tenant",
    "get_current_tenant_id",
    "set_current_tenant",
    "clear_tenant_context",
    "tenant_context",
    "require_tenant",
    # Middleware
    "TenantMiddleware",
    "TenantIdentificationStrategy",
    # Models
    "TenantMixin",
    "TenantIsolatedMixin",
    "Tenant",
    # Session (Row-level)
    "get_tenant_db",
    "TenantAwareSession",
    # Session (Schema-level)
    "get_schema_tenant_db",
    "SchemaRouter",
    # Session (Database-level)
    "get_database_tenant_db",
    "DatabaseRouter",
    "get_database_router",
    # Config
    "MultitenancyScheme",
    "TenantIdentificationMethod",
    "MultitenancySettings",
    "multitenancy_settings",
    "is_multitenancy_enabled",
    "get_multitenancy_scheme",
]

