"""Custom exceptions for CloudSound platform.

This module provides a comprehensive set of custom exceptions with error codes
for better error tracking and debugging across all services.
"""
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for CloudSound platform."""
    
    # General errors (1xxx)
    INTERNAL_ERROR = "CS1000"
    VALIDATION_ERROR = "CS1001"
    NOT_FOUND = "CS1002"
    CONFLICT = "CS1003"
    BAD_REQUEST = "CS1004"
    METHOD_NOT_ALLOWED = "CS1005"
    SERVICE_UNAVAILABLE = "CS1006"
    TIMEOUT = "CS1007"
    
    # Authentication errors (2xxx)
    UNAUTHORIZED = "CS2000"
    FORBIDDEN = "CS2001"
    TOKEN_EXPIRED = "CS2002"
    TOKEN_INVALID = "CS2003"
    CREDENTIALS_INVALID = "CS2004"
    SESSION_EXPIRED = "CS2005"
    RATE_LIMITED = "CS2006"
    
    # Database errors (3xxx)
    DATABASE_ERROR = "CS3000"
    DATABASE_CONNECTION_ERROR = "CS3001"
    DATABASE_QUERY_ERROR = "CS3002"
    DATABASE_INTEGRITY_ERROR = "CS3003"
    OPTIMISTIC_LOCK_ERROR = "CS3004"
    RECORD_NOT_FOUND = "CS3005"
    DUPLICATE_RECORD = "CS3006"
    
    # External service errors (4xxx)
    EXTERNAL_SERVICE_ERROR = "CS4000"
    EXTERNAL_SERVICE_TIMEOUT = "CS4001"
    EXTERNAL_SERVICE_UNAVAILABLE = "CS4002"
    CIRCUIT_BREAKER_OPEN = "CS4003"
    YOUTUBE_API_ERROR = "CS4010"
    BANDCAMP_API_ERROR = "CS4020"
    FACEBOOK_API_ERROR = "CS4030"
    
    # Storage errors (5xxx)
    STORAGE_ERROR = "CS5000"
    STORAGE_QUOTA_EXCEEDED = "CS5001"
    FILE_NOT_FOUND = "CS5002"
    FILE_UPLOAD_FAILED = "CS5003"
    FILE_DOWNLOAD_FAILED = "CS5004"
    
    # Messaging errors (6xxx)
    MESSAGING_ERROR = "CS6000"
    KAFKA_ERROR = "CS6001"
    RABBITMQ_ERROR = "CS6002"
    MESSAGE_PUBLISH_FAILED = "CS6003"
    MESSAGE_CONSUME_FAILED = "CS6004"
    
    # Business logic errors (7xxx)
    BUSINESS_RULE_VIOLATION = "CS7000"
    INVALID_STATE_TRANSITION = "CS7001"
    CONCERT_CONFLICT = "CS7002"
    TRACK_NOT_AVAILABLE = "CS7003"
    STATION_FULL = "CS7004"


class CloudSoundException(Exception):
    """Base exception for all CloudSound errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Standardized error code from ErrorCode enum
        details: Optional dictionary with additional error details
        status_code: HTTP status code for API responses
    """
    
    status_code: int = 500
    error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    
    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        if error_code:
            self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        result = {
            "error": self.message,
            "error_code": self.error_code.value,
            "status_code": self.status_code,
        }
        if self.details:
            result["details"] = self.details
        return result


# Validation Errors
class ValidationError(CloudSoundException):
    """Validation error for invalid input data."""
    status_code = 422
    error_code = ErrorCode.VALIDATION_ERROR


class BadRequestError(CloudSoundException):
    """Bad request error for malformed requests."""
    status_code = 400
    error_code = ErrorCode.BAD_REQUEST


# Authentication/Authorization Errors
class AuthenticationError(CloudSoundException):
    """Authentication error for unauthenticated requests."""
    status_code = 401
    error_code = ErrorCode.UNAUTHORIZED


class AuthorizationError(CloudSoundException):
    """Authorization error for forbidden actions."""
    status_code = 403
    error_code = ErrorCode.FORBIDDEN


class TokenExpiredError(AuthenticationError):
    """Error when JWT token has expired."""
    error_code = ErrorCode.TOKEN_EXPIRED


class TokenInvalidError(AuthenticationError):
    """Error when JWT token is invalid."""
    error_code = ErrorCode.TOKEN_INVALID


class CredentialsInvalidError(AuthenticationError):
    """Error when provided credentials are invalid."""
    error_code = ErrorCode.CREDENTIALS_INVALID


class RateLimitedError(CloudSoundException):
    """Error when rate limit is exceeded."""
    status_code = 429
    error_code = ErrorCode.RATE_LIMITED


# Resource Errors
class NotFoundError(CloudSoundException):
    """Resource not found error."""
    status_code = 404
    error_code = ErrorCode.NOT_FOUND


class ConflictError(CloudSoundException):
    """Conflict error for conflicting operations."""
    status_code = 409
    error_code = ErrorCode.CONFLICT


class OptimisticLockError(ConflictError):
    """Error when optimistic locking fails due to concurrent modification."""
    error_code = ErrorCode.OPTIMISTIC_LOCK_ERROR


# Database Errors
class DatabaseError(CloudSoundException):
    """Database operation error."""
    status_code = 500
    error_code = ErrorCode.DATABASE_ERROR


class DatabaseConnectionError(DatabaseError):
    """Database connection error."""
    error_code = ErrorCode.DATABASE_CONNECTION_ERROR


class DatabaseQueryError(DatabaseError):
    """Database query execution error."""
    error_code = ErrorCode.DATABASE_QUERY_ERROR


class DatabaseIntegrityError(DatabaseError):
    """Database integrity constraint violation."""
    status_code = 409
    error_code = ErrorCode.DATABASE_INTEGRITY_ERROR


class RecordNotFoundError(NotFoundError):
    """Database record not found error."""
    error_code = ErrorCode.RECORD_NOT_FOUND


class DuplicateRecordError(ConflictError):
    """Duplicate database record error."""
    error_code = ErrorCode.DUPLICATE_RECORD


# External Service Errors
class ExternalServiceError(CloudSoundException):
    """External service error."""
    status_code = 502
    error_code = ErrorCode.EXTERNAL_SERVICE_ERROR


class ExternalServiceTimeoutError(ExternalServiceError):
    """External service timeout error."""
    status_code = 504
    error_code = ErrorCode.EXTERNAL_SERVICE_TIMEOUT


class ExternalServiceUnavailableError(ExternalServiceError):
    """External service unavailable error."""
    status_code = 503
    error_code = ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE


class CircuitBreakerOpenError(ExternalServiceUnavailableError):
    """Circuit breaker is open, service temporarily unavailable."""
    error_code = ErrorCode.CIRCUIT_BREAKER_OPEN


class YouTubeAPIError(ExternalServiceError):
    """YouTube API error."""
    error_code = ErrorCode.YOUTUBE_API_ERROR


class BandcampAPIError(ExternalServiceError):
    """Bandcamp API error."""
    error_code = ErrorCode.BANDCAMP_API_ERROR


class FacebookAPIError(ExternalServiceError):
    """Facebook API error."""
    error_code = ErrorCode.FACEBOOK_API_ERROR


# Storage Errors
class StorageError(CloudSoundException):
    """Storage operation error."""
    status_code = 500
    error_code = ErrorCode.STORAGE_ERROR


class StorageQuotaExceededError(StorageError):
    """Storage quota exceeded error."""
    status_code = 507
    error_code = ErrorCode.STORAGE_QUOTA_EXCEEDED


class FileNotFoundError(NotFoundError):
    """File not found in storage."""
    error_code = ErrorCode.FILE_NOT_FOUND


class FileUploadError(StorageError):
    """File upload failed."""
    error_code = ErrorCode.FILE_UPLOAD_FAILED


class FileDownloadError(StorageError):
    """File download failed."""
    error_code = ErrorCode.FILE_DOWNLOAD_FAILED


# Messaging Errors
class MessagingError(CloudSoundException):
    """Messaging system error."""
    status_code = 500
    error_code = ErrorCode.MESSAGING_ERROR


class KafkaError(MessagingError):
    """Kafka error."""
    error_code = ErrorCode.KAFKA_ERROR


class RabbitMQError(MessagingError):
    """RabbitMQ error."""
    error_code = ErrorCode.RABBITMQ_ERROR


class MessagePublishError(MessagingError):
    """Message publish failed."""
    error_code = ErrorCode.MESSAGE_PUBLISH_FAILED


class MessageConsumeError(MessagingError):
    """Message consume failed."""
    error_code = ErrorCode.MESSAGE_CONSUME_FAILED


# Business Logic Errors
class BusinessRuleError(CloudSoundException):
    """Business rule violation error."""
    status_code = 422
    error_code = ErrorCode.BUSINESS_RULE_VIOLATION


class InvalidStateTransitionError(BusinessRuleError):
    """Invalid state transition error."""
    error_code = ErrorCode.INVALID_STATE_TRANSITION


class ConcertConflictError(ConflictError):
    """Concert scheduling conflict error."""
    error_code = ErrorCode.CONCERT_CONFLICT


class TrackNotAvailableError(NotFoundError):
    """Track not available for streaming."""
    error_code = ErrorCode.TRACK_NOT_AVAILABLE


class StationFullError(BusinessRuleError):
    """Station has reached maximum track capacity."""
    error_code = ErrorCode.STATION_FULL


# Service Availability
class ServiceUnavailableError(CloudSoundException):
    """Service temporarily unavailable."""
    status_code = 503
    error_code = ErrorCode.SERVICE_UNAVAILABLE


class TimeoutError(CloudSoundException):
    """Operation timeout error."""
    status_code = 504
    error_code = ErrorCode.TIMEOUT

