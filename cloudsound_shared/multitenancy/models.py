"""
Tenant models and mixins for multitenancy.

This module provides:
1. Tenant model - For managing tenants
2. TenantMixin - Add to models that need tenant isolation
"""

from sqlalchemy import Column, String, Boolean, DateTime, Index, event, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr, relationship
from sqlalchemy.ext.hybrid import hybrid_property
import uuid
from typing import Optional

from cloudsound_shared.models.base import Base, UUIDMixin, TimestampMixin
from cloudsound_shared.multitenancy.context import get_current_tenant_id


class Tenant(Base, UUIDMixin, TimestampMixin):
    """
    Tenant model for managing organizations/clients.
    
    Each tenant represents a separate organization using the platform.
    """
    
    __tablename__ = "tenants"
    
    # Unique slug for URL-friendly tenant identification
    slug = Column(String(100), unique=True, nullable=False, index=True)
    
    # Display name
    name = Column(String(255), nullable=False)
    
    # Optional custom domain for tenant
    domain = Column(String(255), unique=True, nullable=True, index=True)
    
    # Schema name for schema-based multitenancy (e.g., "tenant_acme")
    schema_name = Column(String(100), unique=True, nullable=True)
    
    # Database URL for database-based multitenancy
    database_url = Column(String(500), nullable=True)
    
    # Tenant status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Subscription/plan information
    plan = Column(String(50), default="free", nullable=False)
    
    # Metadata
    settings = Column(String(5000), nullable=True)  # JSON string for tenant settings
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug='{self.slug}', name='{self.name}')>"
    
    @classmethod
    def generate_schema_name(cls, slug: str) -> str:
        """Generate PostgreSQL schema name from tenant slug."""
        # Sanitize slug for PostgreSQL schema naming
        safe_slug = slug.lower().replace("-", "_").replace(" ", "_")
        return f"tenant_{safe_slug}"


class TenantMixin:
    """
    Mixin for models that require tenant isolation (Row-level multitenancy).
    
    Usage:
        class RadioStation(Base, UUIDMixin, TimestampMixin, TenantMixin):
            __tablename__ = "radio_stations"
            name = Column(String(255), nullable=False)
            # ... other fields
    
    This adds:
    - tenant_id column with foreign key to tenants table
    - Automatic tenant_id filter on queries (when using TenantAwareSession)
    - Automatic tenant_id population on insert
    """
    
    @declared_attr
    def tenant_id(cls):
        """Tenant ID foreign key column."""
        return Column(
            UUID(as_uuid=True),
            nullable=False,
            index=True,
        )
    
    @declared_attr
    def __table_args__(cls):
        """Add composite index for tenant_id + common query patterns."""
        # Get existing table args if any
        existing_args = getattr(cls, "__table_args__", ())
        if isinstance(existing_args, dict):
            existing_args = (existing_args,)
        elif not isinstance(existing_args, tuple):
            existing_args = ()
        
        # Add tenant index
        new_args = (
            Index(f"ix_{cls.__tablename__}_tenant_id", "tenant_id"),
            *[arg for arg in existing_args if isinstance(arg, Index)],
        )
        
        # Preserve any dict args (like schema)
        dict_args = next((arg for arg in existing_args if isinstance(arg, dict)), {})
        
        return (*new_args, dict_args) if dict_args else new_args


# Event listeners for automatic tenant_id population
@event.listens_for(TenantMixin, "before_insert", propagate=True)
def set_tenant_id_on_insert(mapper, connection, target):
    """
    Automatically set tenant_id on insert if not already set.
    
    This uses the current tenant context to populate tenant_id.
    """
    if hasattr(target, "tenant_id") and target.tenant_id is None:
        current_tenant_id = get_current_tenant_id()
        if current_tenant_id:
            target.tenant_id = uuid.UUID(current_tenant_id) if isinstance(current_tenant_id, str) else current_tenant_id


class TenantIsolatedMixin(TenantMixin):
    """
    Extended tenant mixin with additional isolation features.
    
    Use this for models that need stricter isolation and audit trails.
    """
    
    @declared_attr
    def created_by_tenant_user_id(cls):
        """Track which user created this record within the tenant."""
        return Column(UUID(as_uuid=True), nullable=True)
    
    @declared_attr
    def last_modified_by_tenant_user_id(cls):
        """Track which user last modified this record within the tenant."""
        return Column(UUID(as_uuid=True), nullable=True)

