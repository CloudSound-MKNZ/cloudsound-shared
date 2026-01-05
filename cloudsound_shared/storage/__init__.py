"""MinIO/S3 client utilities."""
from minio import Minio
from minio.error import S3Error
import structlog
from typing import Optional, BinaryIO
from cloudsound_shared.config.settings import app_settings

logger = structlog.get_logger(__name__)

class StorageClient:
    """MinIO/S3 storage client wrapper."""
    
    def __init__(
        self,
        endpoint: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        secure: Optional[bool] = None,
        bucket: Optional[str] = None,
    ):
        self.endpoint = endpoint or app_settings.minio_endpoint
        self.access_key = access_key or app_settings.minio_access_key
        self.secret_key = secret_key or app_settings.minio_secret_key
        self.secure = secure if secure is not None else app_settings.minio_secure
        self.bucket = bucket or app_settings.minio_bucket
        self.client: Optional[Minio] = None
    
    def connect(self) -> None:
        """Initialize MinIO client."""
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
            # Ensure bucket exists
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("storage_bucket_created", bucket=self.bucket)
            logger.info("storage_client_connected", endpoint=self.endpoint, bucket=self.bucket)
        except S3Error as e:
            logger.error("storage_client_connection_failed", error=str(e))
            raise
    
    def upload_file(
        self,
        object_name: str,
        file_data: BinaryIO,
        content_type: str = "application/octet-stream",
        length: Optional[int] = None,
    ) -> str:
        """Upload file to storage."""
        if not self.client:
            self.connect()
        
        try:
            if length is None:
                # Read file to get length
                file_data.seek(0, 2)  # Seek to end
                length = file_data.tell()
                file_data.seek(0)  # Reset to beginning
            
            self.client.put_object(
                self.bucket,
                object_name,
                file_data,
                length=length,
                content_type=content_type,
            )
            logger.info("storage_file_uploaded", object_name=object_name, bucket=self.bucket)
            return object_name
        except S3Error as e:
            logger.error("storage_upload_failed", object_name=object_name, error=str(e))
            raise
    
    def get_file(self, object_name: str) -> bytes:
        """Download file from storage."""
        if not self.client:
            self.connect()
        
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            logger.debug("storage_file_downloaded", object_name=object_name)
            return data
        except S3Error as e:
            logger.error("storage_download_failed", object_name=object_name, error=str(e))
            raise
    
    def delete_file(self, object_name: str) -> None:
        """Delete file from storage."""
        if not self.client:
            self.connect()
        
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info("storage_file_deleted", object_name=object_name)
        except S3Error as e:
            logger.error("storage_delete_failed", object_name=object_name, error=str(e))
            raise
    
    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Generate presigned URL for file access."""
        if not self.client:
            self.connect()
        
        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires_seconds,
            )
            logger.debug("storage_presigned_url_generated", object_name=object_name)
            return url
        except S3Error as e:
            logger.error("storage_presigned_url_failed", object_name=object_name, error=str(e))
            raise
    
    async def file_exists(self, object_name: str) -> bool:
        """Check if file exists in storage."""
        if not self.client:
            self.connect()
        
        try:
            # Try to stat the object
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error("storage_stat_failed", object_name=object_name, error=str(e))
            raise
    
    async def get_file_range(self, object_name: str, start: int, end: int) -> bytes:
        """Download a range of bytes from a file."""
        if not self.client:
            self.connect()
        
        try:
            response = self.client.get_object(
                self.bucket,
                object_name,
                offset=start,
                length=end - start + 1,
            )
            data = response.read()
            response.close()
            response.release_conn()
            logger.debug("storage_file_range_downloaded", object_name=object_name, start=start, end=end)
            return data
        except S3Error as e:
            logger.error("storage_range_download_failed", object_name=object_name, error=str(e))
            raise

