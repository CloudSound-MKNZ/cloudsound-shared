"""
Tenant middleware for FastAPI.

This middleware extracts tenant information from requests and sets the tenant context.
Supports multiple tenant identification strategies:
1. JWT token (tenant_id in payload)
2. HTTP header (X-Tenant-ID)
3. Subdomain (tenant.cloudsound.com)
4. Custom domain (tenant's own domain)
5. URL path (/api/v1/tenants/{tenant_id}/...)
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional, List, Callable
from enum import Enum
import structlog
from jose import jwt, JWTError

from cloudsound_shared.config.settings import app_settings
from cloudsound_shared.multitenancy.context import (
    TenantContext,
    set_current_tenant,
    clear_tenant_context,
)

logger = structlog.get_logger(__name__)


class TenantIdentificationStrategy(str, Enum):
    """Strategies for identifying tenant from request."""
    JWT_TOKEN = "jwt_token"
    HEADER = "header"
    SUBDOMAIN = "subdomain"
    DOMAIN = "domain"
    PATH = "path"


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set tenant context from incoming requests.
    
    Usage:
        app = FastAPI()
        app.add_middleware(
            TenantMiddleware,
            strategies=[
                TenantIdentificationStrategy.JWT_TOKEN,
                TenantIdentificationStrategy.HEADER,
            ],
            exclude_paths=["/health", "/metrics", "/docs"],
        )
    """
    
    def __init__(
        self,
        app,
        strategies: Optional[List[TenantIdentificationStrategy]] = None,
        exclude_paths: Optional[List[str]] = None,
        tenant_header: str = "X-Tenant-ID",
        require_tenant: bool = False,
        tenant_resolver: Optional[Callable[[str], Optional[TenantContext]]] = None,
    ):
        """
        Initialize tenant middleware.
        
        Args:
            app: FastAPI application
            strategies: List of strategies to try (in order)
            exclude_paths: Paths to skip tenant resolution
            tenant_header: Header name for header-based identification
            require_tenant: If True, reject requests without tenant
            tenant_resolver: Optional async function to resolve tenant_id to TenantContext
        """
        super().__init__(app)
        self.strategies = strategies or [
            TenantIdentificationStrategy.JWT_TOKEN,
            TenantIdentificationStrategy.HEADER,
        ]
        self.exclude_paths = exclude_paths or [
            "/health",
            "/health/ready",
            "/metrics",
            "/docs",
            "/openapi.json",
        ]
        self.tenant_header = tenant_header
        self.require_tenant = require_tenant
        self.tenant_resolver = tenant_resolver
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and set tenant context."""
        # Skip excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        try:
            # Try to identify tenant
            tenant_context = await self._identify_tenant(request)
            
            if tenant_context:
                set_current_tenant(tenant_context)
                logger.debug(
                    "tenant_identified",
                    tenant_id=tenant_context.tenant_id,
                    strategy=self._get_successful_strategy(request),
                )
            elif self.require_tenant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant identification required",
                )
            
            # Process request
            response = await call_next(request)
            
            # Add tenant ID to response headers (useful for debugging)
            if tenant_context:
                response.headers["X-Tenant-ID"] = tenant_context.tenant_id
            
            return response
            
        finally:
            # Always clear tenant context after request
            clear_tenant_context()
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path should skip tenant resolution."""
        return any(path.startswith(excluded) for excluded in self.exclude_paths)
    
    async def _identify_tenant(self, request: Request) -> Optional[TenantContext]:
        """Try each strategy to identify tenant."""
        for strategy in self.strategies:
            tenant_id = await self._extract_tenant_id(request, strategy)
            if tenant_id:
                # Resolve to full context if resolver provided
                if self.tenant_resolver:
                    context = await self.tenant_resolver(tenant_id)
                    if context:
                        return context
                else:
                    return TenantContext(tenant_id=tenant_id)
        return None
    
    async def _extract_tenant_id(
        self, request: Request, strategy: TenantIdentificationStrategy
    ) -> Optional[str]:
        """Extract tenant ID using specified strategy."""
        if strategy == TenantIdentificationStrategy.JWT_TOKEN:
            return self._from_jwt_token(request)
        elif strategy == TenantIdentificationStrategy.HEADER:
            return self._from_header(request)
        elif strategy == TenantIdentificationStrategy.SUBDOMAIN:
            return self._from_subdomain(request)
        elif strategy == TenantIdentificationStrategy.DOMAIN:
            return await self._from_domain(request)
        elif strategy == TenantIdentificationStrategy.PATH:
            return self._from_path(request)
        return None
    
    def _from_jwt_token(self, request: Request) -> Optional[str]:
        """Extract tenant_id from JWT token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(
                token,
                app_settings.secret_key,
                algorithms=[app_settings.jwt_algorithm],
            )
            return payload.get("tenant_id")
        except JWTError:
            return None
    
    def _from_header(self, request: Request) -> Optional[str]:
        """Extract tenant_id from HTTP header."""
        return request.headers.get(self.tenant_header)
    
    def _from_subdomain(self, request: Request) -> Optional[str]:
        """Extract tenant from subdomain (e.g., acme.cloudsound.com -> acme)."""
        host = request.headers.get("host", "")
        parts = host.split(".")
        
        # Expect format: tenant.domain.tld
        if len(parts) >= 3:
            subdomain = parts[0]
            # Exclude common subdomains
            if subdomain not in ["www", "api", "app", "admin"]:
                return subdomain
        return None
    
    async def _from_domain(self, request: Request) -> Optional[str]:
        """
        Extract tenant from custom domain.
        
        This requires a database lookup to map domain -> tenant_id.
        Only works if tenant_resolver is provided.
        """
        # Domain resolution happens in tenant_resolver
        # Return the full host as identifier for lookup
        host = request.headers.get("host", "").split(":")[0]  # Remove port
        if host and not host.endswith(("localhost", "cloudsound.com")):
            return f"domain:{host}"
        return None
    
    def _from_path(self, request: Request) -> Optional[str]:
        """Extract tenant from URL path (e.g., /api/v1/tenants/{tenant_id}/...)."""
        path_parts = request.url.path.strip("/").split("/")
        
        # Look for pattern: /api/v1/tenants/{tenant_id}/...
        try:
            tenants_index = path_parts.index("tenants")
            if len(path_parts) > tenants_index + 1:
                return path_parts[tenants_index + 1]
        except ValueError:
            pass
        return None
    
    def _get_successful_strategy(self, request: Request) -> str:
        """Determine which strategy succeeded (for logging)."""
        for strategy in self.strategies:
            if strategy == TenantIdentificationStrategy.JWT_TOKEN:
                if self._from_jwt_token(request):
                    return "jwt_token"
            elif strategy == TenantIdentificationStrategy.HEADER:
                if self._from_header(request):
                    return "header"
        return "unknown"

