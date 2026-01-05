"""JWT token generation and validation."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from pydantic import BaseModel
from cloudsound_shared.config.settings import app_settings
import structlog

logger = structlog.get_logger(__name__)

class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str
    role: str
    tenant_id: Optional[str] = None

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=app_settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(
        to_encode,
        app_settings.secret_key,
        algorithm=app_settings.jwt_algorithm,
    )
    
    logger.debug("access_token_created", user_id=data.get("user_id"))
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=app_settings.jwt_refresh_token_expire_days)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    
    encoded_jwt = jwt.encode(
        to_encode,
        app_settings.secret_key,
        algorithm=app_settings.jwt_algorithm,
    )
    
    logger.debug("refresh_token_created", user_id=data.get("user_id"))
    return encoded_jwt

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(
            token,
            app_settings.secret_key,
            algorithms=[app_settings.jwt_algorithm],
        )
        
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        tenant_id: Optional[str] = payload.get("tenant_id")
        
        if user_id is None or email is None or role is None:
            logger.warning("token_missing_required_fields")
            return None
        
        token_data = TokenData(
            user_id=user_id,
            email=email,
            role=role,
            tenant_id=tenant_id,
        )
        
        logger.debug("token_verified", user_id=user_id)
        return token_data
        
    except JWTError as e:
        logger.warning("token_verification_failed", error=str(e))
        return None

