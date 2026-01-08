"""
Configuration for multitenancy.

Add these settings to your environment or .env file to configure multitenancy.
"""

from enum import Enum
from typing import Optional, List
from pydantic_settings import BaseSettings


class MultitenancyScheme(str, Enum):
    """Available multitenancy schemes."""
    
    # Row-level: All tenants share tables, filtered by tenant_id column
    ROW_LEVEL = "row_level"
    
    # Schema-level: Each tenant has own PostgreSQL schema
    SCHEMA_LEVEL = "schema_level"
    
    # Database-level: Each tenant has own database
    DATABASE_LEVEL = "database_level"
    
    # Disabled: No multitenancy (single tenant mode)
    DISABLED = "disabled"


class TenantIdentificationMethod(str, Enum):
    """Methods for identifying tenant from requests."""
    JWT_TOKEN = "jwt_token"      # From JWT payload (tenant_id claim)
    HEADER = "header"            # From X-Tenant-ID header
    SUBDOMAIN = "subdomain"      # From subdomain (tenant.example.com)
    DOMAIN = "domain"            # From custom domain
    PATH = "path"                # From URL path (/tenants/{id}/...)


class MultitenancySettings(BaseSettings):
    """
    Multitenancy configuration settings.
    
    Environment variables:
        MULTITENANCY_ENABLED: Enable/disable multitenancy
        MULTITENANCY_SCHEME: row_level, schema_level, database_level, or disabled
        MULTITENANCY_IDENTIFICATION_METHODS: Comma-separated list of methods
        MULTITENANCY_REQUIRE_TENANT: If true, reject requests without tenant
        MULTITENANCY_DEFAULT_TENANT_ID: Default tenant for unauthenticated requests
    """
    
    # Enable/disable multitenancy
    multitenancy_enabled: bool = True
    
    # Which multitenancy scheme to use
    multitenancy_scheme: MultitenancyScheme = MultitenancyScheme.ROW_LEVEL
    
    # How to identify tenant from requests (comma-separated in env)
    multitenancy_identification_methods: str = "jwt_token,header"
    
    # Whether to require tenant on all requests
    multitenancy_require_tenant: bool = False
    
    # Default tenant for unauthenticated requests (optional)
    multitenancy_default_tenant_id: Optional[str] = None
    
    # Header name for header-based identification
    multitenancy_tenant_header: str = "X-Tenant-ID"
    
    # Paths excluded from tenant requirement
    multitenancy_exclude_paths: str = "/health,/metrics,/docs,/openapi.json"
    
    # Schema prefix for schema-level multitenancy
    multitenancy_schema_prefix: str = "tenant_"
    
    # Database name prefix for database-level multitenancy
    multitenancy_database_prefix: str = "tenant_"
    
    @property
    def identification_methods(self) -> List[TenantIdentificationMethod]:
        """Parse identification methods from comma-separated string."""
        methods = []
        for method in self.multitenancy_identification_methods.split(","):
            method = method.strip().lower()
            try:
                methods.append(TenantIdentificationMethod(method))
            except ValueError:
                pass
        return methods or [TenantIdentificationMethod.JWT_TOKEN]
    
    @property
    def exclude_paths_list(self) -> List[str]:
        """Parse exclude paths from comma-separated string."""
        return [p.strip() for p in self.multitenancy_exclude_paths.split(",") if p.strip()]
    
    class Config:
        env_prefix = ""  # No prefix, use exact variable names


# Global settings instance
multitenancy_settings = MultitenancySettings()


# Convenience functions
def is_multitenancy_enabled() -> bool:
    """Check if multitenancy is enabled."""
    return (
        multitenancy_settings.multitenancy_enabled
        and multitenancy_settings.multitenancy_scheme != MultitenancyScheme.DISABLED
    )


def get_multitenancy_scheme() -> MultitenancyScheme:
    """Get the current multitenancy scheme."""
    return multitenancy_settings.multitenancy_scheme

