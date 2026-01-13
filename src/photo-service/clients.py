#!/usr/bin/env python3
"""Clients for external services (photographer, tags)."""

import logging
from typing import Any

import httpx
import grpc
from grpc import aio

from config import settings
from exceptions import (
    PhotographerNotFoundError,
    PhotographerServiceUnavailableError,
    TagsServiceUnavailableError,
)

logger = logging.getLogger(__name__)
# Import generated protobuf code
# You'll need to generate this from proto/tags.proto
# For now, we'll define a simple stub
try:
    import tags_pb2
    import tags_pb2_grpc
    logger.info("Successfully imported protobuf stubs")
except ImportError as e:
    # Fallback if proto not generated yet
    logger.error(f"❌ Failed to import protobuf modules: {e}")
    tags_pb2 = None
    tags_pb2_grpc = None




class PhotographerClient:
    """HTTP client for photographer service."""
    
    @staticmethod
    async def check_photographer_exists(display_name: str) -> bool:
        """
        Check if a photographer exists.
        
        Raises:
            PhotographerNotFoundError: If photographer doesn't exist
            PhotographerServiceUnavailableError: If service is down
        """
        url = f"{settings.photographer_service_url}/photographers/{display_name}"
        
        try:
            async with httpx.AsyncClient(timeout=settings.photographer_timeout) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    raise PhotographerNotFoundError(display_name)
                else:
                    logger.error(f"Photographer service returned {response.status_code}")
                    raise PhotographerServiceUnavailableError()
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout calling photographer service at {url}")
            raise PhotographerServiceUnavailableError()
        except httpx.RequestError as e:
            logger.error(f"Error calling photographer service: {e}")
            raise PhotographerServiceUnavailableError()


class TagsClient:
    """gRPC client for tags service."""
    
    def __init__(self):
        self.channel: aio.Channel | None = None
        self.stub: Any | None = None
    
    async def connect(self):
        """Establish gRPC connection to tags service."""
        try:
            self.channel = aio.insecure_channel(settings.tags_service_address)
            
            if tags_pb2_grpc:
                self.stub = tags_pb2_grpc.TagsStub(self.channel)
            
            logger.info(f"Connected to tags service at {settings.tags_service_address}")
        except Exception as e:
            logger.error(f"Failed to connect to tags service: {e}")
            raise TagsServiceUnavailableError()
    
    async def disconnect(self):
        """Close gRPC connection."""
        if self.channel:
            await self.channel.close()
            logger.info("Disconnected from tags service")
    
    async def get_tags(self, image_data: bytes) -> list[str]:
        """
        Get tags for an image.
        
        Args:
            image_data: JPEG image bytes
            
        Returns:
            List of tags
            
        Raises:
            TagsServiceUnavailableError: If service is unavailable
        """
        if not self.stub or not tags_pb2:
            logger.warning("Tags service not available, returning empty tags")
            return []
        
        try:
            request = tags_pb2.ImageRequest(file=image_data)
            response = await self.stub.GetTags(request, timeout=5.0)
            
            logger.info(f"Received {len(response.tags)} tags from service")
            return list(response.tags)
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error calling tags service: {e}")
            # Don't fail the upload if tags service is down
            return []
        except Exception as e:
            logger.error(f"Unexpected error calling tags service: {e}")
            return []


# Singleton instance
tags_client = TagsClient()
