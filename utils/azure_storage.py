"""Azure Blob Storage utilities for downloading images."""

import os
import tempfile
from typing import Tuple, Optional
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError

from config.settings import settings


class AzureStorageManager:
    """Manager for Azure Blob Storage operations."""
    
    def __init__(self):
        self.blob_service_client: Optional[BlobServiceClient] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client."""
        try:
            if settings.azure_storage_connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    settings.azure_storage_connection_string
                )
                print("✅ Azure Blob Storage client initialized")
            else:
                print("⚠️ Azure Storage connection string not provided")
        except Exception as e:
            print(f"❌ Failed to initialize Azure Blob Storage client: {e}")
            raise

    async def download_image(self, image_url: str, image_type: str = "image") -> str:
        """Download a single image from Azure Blob Storage."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        print(f"📥 Downloading {image_type} from: {image_url}")
        
        try:
            # Extract blob name from URL
            blob_name = self._extract_blob_name(image_url)
            
            # Download blob
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container,
                blob=blob_name
            )
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Download blob to temporary file
            with open(temp_file_path, 'wb') as f:
                download_stream = blob_client.download_blob()
                f.write(download_stream.readall())
            
            print(f"✅ Downloaded {image_type} to: {temp_file_path}")
            return temp_file_path
            
        except AzureError as e:
            print(f"❌ Azure error downloading {image_type}: {e}")
            raise
        except Exception as e:
            print(f"❌ Failed to download {image_type}: {e}")
            raise

    async def download_both_images(
        self, 
        question_image_url: str, 
        working_note_url: str
    ) -> Tuple[str, str]:
        """Download both question and working note images from Azure Blob Storage."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        print(f"📥 Downloading both images:")
        print(f"  - Question: {question_image_url}")
        print(f"  - Working Note: {working_note_url}")
        
        question_image_path = None
        working_note_path = None
        
        try:
            # Validate both URLs first
            print("🔍 Validating image URLs...")
            question_valid = await self.validate_image_url(question_image_url)
            working_note_valid = await self.validate_image_url(working_note_url)
            
            if not question_valid:
                raise ValueError(f"Question image URL is not accessible: {question_image_url}")
            if not working_note_valid:
                raise ValueError(f"Working note image URL is not accessible: {working_note_url}")
            
            print("✅ Both image URLs are valid")
            
            # Download question image
            question_image_path = await self.download_image(question_image_url, "question image")
            
            # Download working note image
            working_note_path = await self.download_image(working_note_url, "working note image")
            
            print("✅ Both images downloaded successfully")
            return question_image_path, working_note_path
            
        except Exception as e:
            print(f"❌ Failed to download both images: {e}")
            # Clean up any partially downloaded files
            self._cleanup_temp_files(question_image_path, working_note_path)
            raise

    def _extract_blob_name(self, image_url: str) -> str:
        """Extract blob name from Azure Blob Storage URL."""
        try:
            # Handle different URL formats
            if 'blob.core.windows.net' in image_url:
                # Full Azure Blob URL: https://account.blob.core.windows.net/container/blobname
                parts = image_url.split('/')
                container_index = parts.index(settings.azure_storage_container)
                if container_index + 1 < len(parts):
                    return '/'.join(parts[container_index + 1:])
            
            # If it's just the blob name
            if '/' not in image_url:
                return image_url
            
            # Extract from path-like URL
            return image_url.split('/')[-1]
            
        except Exception as e:
            print(f"⚠️ Could not extract blob name from URL: {image_url}, using as-is")
            return image_url.split('/')[-1]

    def _cleanup_temp_files(self, *file_paths: Optional[str]):
        """Clean up temporary files."""
        for file_path in file_paths:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(f"🧹 Cleaned up: {file_path}")
                except Exception as e:
                    print(f"⚠️ Failed to clean up {file_path}: {e}")

    async def validate_image_url(self, image_url: str) -> bool:
        """Validate if the image URL is accessible."""
        if not self.blob_service_client:
            return False
        
        try:
            blob_name = self._extract_blob_name(image_url)
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container,
                blob=blob_name
            )
            
            # Check if blob exists
            exists = await blob_client.exists()
            return exists
            
        except Exception as e:
            print(f"❌ Failed to validate image URL {image_url}: {e}")
            return False

    async def get_image_metadata(self, image_url: str) -> dict:
        """Get metadata for an image blob."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        try:
            blob_name = self._extract_blob_name(image_url)
            blob_client = self.blob_service_client.get_blob_client(
                container=settings.azure_storage_container,
                blob=blob_name
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
            print(f"❌ Failed to get image metadata for {image_url}: {e}")
            raise

    async def get_both_images_metadata(self, question_image_url: str, working_note_url: str) -> dict:
        """Get metadata for both images."""
        try:
            question_metadata = await self.get_image_metadata(question_image_url)
            working_note_metadata = await self.get_image_metadata(working_note_url)
            
            return {
                "question_image": question_metadata,
                "working_note_image": working_note_metadata,
                "total_size": question_metadata["size"] + working_note_metadata["size"]
            }
            
        except Exception as e:
            print(f"❌ Failed to get both images metadata: {e}")
            raise

    async def list_images_in_container(self, prefix: str = "") -> list:
        """List all images in the container with optional prefix."""
        if not self.blob_service_client:
            raise RuntimeError("Azure Blob Storage client not initialized")
        
        try:
            container_client = self.blob_service_client.get_container_client(
                settings.azure_storage_container
            )
            
            blobs = []
            async for blob in container_client.list_blobs(name_starts_with=prefix):
                blobs.append({
                    "name": blob.name,
                    "size": blob.size,
                    "last_modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None
                })
            
            return blobs
            
        except Exception as e:
            print(f"❌ Failed to list images in container: {e}")
            raise


# Global Azure Storage manager instance
azure_storage = AzureStorageManager()
