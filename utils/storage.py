"""Storage utilities for downloading images from Azure Blob Storage and local filesystem."""

import os
import tempfile
import shutil
from abc import ABC, abstractmethod
from typing import Optional
from azure.storage.blob import BlobServiceClient
from azure.identity import ClientSecretCredential
from azure.core.exceptions import AzureError

from config.settings import settings


class StorageManager(ABC):
    """Abstract base class for storage managers."""
    
    @abstractmethod
    async def download_image(self, container_name: str, image_name: str) -> str:
        """Download/copy a single image to a temporary file."""
        pass
    
    @abstractmethod
    async def get_image_metadata(self, container_name: str, image_name: str) -> dict:
        """Get metadata for an image."""
        pass


class AzureStorageManager(StorageManager):
    """Simplified manager for Azure Blob Storage operations using service principal authentication."""
    
    def __init__(self):
        self.blob_service_client: Optional[BlobServiceClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client using service principal authentication."""
        try:
            if all([settings.azure_client_id, settings.azure_tenant_id, settings.azure_client_secret, settings.azure_storage_account_name]):
                # Use service principal authentication
                credential = ClientSecretCredential(
                    tenant_id=settings.azure_tenant_id,
                    client_id=settings.azure_client_id,
                    client_secret=settings.azure_client_secret
                )
                
                account_url = f"https://{settings.azure_storage_account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(
                    account_url=account_url,
                    credential=credential
                )
                print("✅ Azure Blob Storage client initialized with service principal")
        except Exception as e:
            print(f"❌ Failed to initialize Azure Blob Storage client: {e}")
            raise

    async def download_image(self, container_name: str, image_name: str) -> str:
        """Download a single image from Azure Blob Storage."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        print(f"📥 Downloading {container_name}/{image_name}")
        
        try:
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=image_name
            )
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Download blob to temporary file
            with open(temp_file_path, 'wb') as f:
                download_stream = blob_client.download_blob()
                f.write(download_stream.readall())
            
            print(f"✅ Downloaded {temp_file_path}")
            return temp_file_path
            
        except AzureError as e:
            print(f"Azure error downloading {container_name}/{image_name}: {e}")
            raise
        except Exception as e:
            print(f"Failed to download {container_name}/{image_name}: {e}")
            raise

    async def get_image_metadata(self, container_name: str, image_name: str) -> dict:
        """Get metadata for an image blob."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=image_name
            )
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "content_type": properties.content_settings.content_type,
                "last_modified": properties.last_modified,
                "etag": properties.etag,
                "metadata": properties.metadata
            }
            
        except Exception as e:
            print(f"❌ Failed to get image metadata for {container_name}/{image_name}: {e}")
            raise


class LocalStorageManager(StorageManager):
    """Manager for local filesystem operations using container_name as folder name."""
    
    def __init__(self, base_path: str = "."):
        self.base_path = os.path.abspath(base_path)
        print(f"✅ Local Storage manager initialized with base path: {self.base_path}")

    async def download_image(self, container_name: str, image_name: str) -> str:
        """Copy a single image from local filesystem to temporary file."""
        print(f"📥 Copying {container_name}/{image_name}")
        
        try:
            # Resolve the full path using container_name as folder
            full_path = os.path.join(self.base_path, container_name, image_name)
            
            # Check if file exists
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Image file not found: {full_path}")
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Copy file to temporary location
            shutil.copy2(full_path, temp_file_path)
            
            print(f"✅ Copied {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            print(f"Failed to copy {container_name}/{image_name}: {e}")
            raise

    async def get_image_metadata(self, container_name: str, image_name: str) -> dict:
        """Get metadata for a local image file."""
        try:
            # Resolve the full path using container_name as folder
            full_path = os.path.join(self.base_path, container_name, image_name)
            
            # Check if file exists
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Image file not found: {full_path}")
            
            # Get file stats
            stat = os.stat(full_path)
            
            # Determine content type based on file extension
            _, ext = os.path.splitext(full_path.lower())
            content_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }
            content_type = content_type_map.get(ext, 'application/octet-stream')
            
            return {
                "size": stat.st_size,
                "content_type": content_type,
                "last_modified": stat.st_mtime,
                "etag": None,  # Not applicable for local files
                "metadata": {}  # Not applicable for local files
            }
            
        except Exception as e:
            print(f"❌ Failed to get image metadata for {container_name}/{image_name}: {e}")
            raise


# Global storage manager instances
azure_storage = AzureStorageManager()
local_storage = LocalStorageManager()