"""
Tenant context management using contextvars.

This module provides thread-safe tenant context storage that works with:
- Async FastAPI routes
- Background tasks
- Kafka/RabbitMQ consumers
"""

from contextvars import ContextVar
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional
import structlog

logger = structlog.get_logger(__name__)

# Context variable for storing current tenant
_current_tenant: ContextVar[Optional["TenantContext"]] = ContextVar(
    "current_tenant", default=None
)


@dataclass
class TenantContext:
    """Holds information about the current tenant context."""
    
    tenant_id: str
    tenant_slug: Optional[str] = None
    tenant_name: Optional[str] = None
    schema_name: Optional[str] = None  # For schema-based multitenancy
    database_url: Optional[str] = None  # For database-based multitenancy
    
    @property
    def identifier(self) -> str:
        """Return the primary identifier for this tenant."""
        return self.tenant_slug or self.tenant_id


def get_current_tenant() -> Optional[TenantContext]:
    """
    Get the current tenant context.
    
    Returns:
        TenantContext if set, None otherwise.
    
    Usage:
        tenant = get_current_tenant()
        if tenant:
            logger.info("Processing for tenant", tenant_id=tenant.tenant_id)
    """
    return _current_tenant.get()


def get_current_tenant_id() -> Optional[str]:
    """
    Get the current tenant ID.
    
    Returns:
        str if tenant context is set, None otherwise.
    """
    tenant = _current_tenant.get()
    return tenant.tenant_id if tenant else None


def set_current_tenant(tenant: Optional[TenantContext]) -> None:
    """
    Set the current tenant context.
    
    Args:
        tenant: TenantContext to set, or None to clear.
    """
    _current_tenant.set(tenant)
    if tenant:
        # Bind tenant to structured logging context
        structlog.contextvars.bind_contextvars(tenant_id=tenant.tenant_id)
        logger.debug("tenant_context_set", tenant_id=tenant.tenant_id)
    else:
        structlog.contextvars.unbind_contextvars("tenant_id")


def clear_tenant_context() -> None:
    """Clear the current tenant context."""
    set_current_tenant(None)


@contextmanager
def tenant_context(tenant: TenantContext):
    """
    Context manager for temporarily setting tenant context.
    
    Usage:
        with tenant_context(TenantContext(tenant_id="tenant-123")):
            # All operations here will use this tenant
            await process_data()
    """
    previous_tenant = get_current_tenant()
    set_current_tenant(tenant)
    try:
        yield tenant
    finally:
        set_current_tenant(previous_tenant)


def require_tenant() -> TenantContext:
    """
    Get the current tenant context, raising an error if not set.
    
    Returns:
        TenantContext for the current request.
        
    Raises:
        RuntimeError: If no tenant context is set.
    
    Usage:
        tenant = require_tenant()
        # Guaranteed to have a valid tenant here
    """
    tenant = get_current_tenant()
    if not tenant:
        raise RuntimeError("No tenant context set. Ensure TenantMiddleware is configured.")
    return tenant

