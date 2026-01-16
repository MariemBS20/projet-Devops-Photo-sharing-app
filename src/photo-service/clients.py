#!/usr/bin/env python3
"""Clients for external services (photographer, tags)."""
from typing import Optional

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
import photo_of_day_pb2
import photo_of_day_pb2_grpc
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

class PhotoOfDayClient:
    """Client pour le service gRPC Photo of Day."""
    
    def __init__(self, grpc_host: str = "localhost", grpc_port: int = 50051):
        """
        Initialiser le client gRPC.
        
        Args:
            grpc_host: Hôte du service gRPC
            grpc_port: Port du service gRPC
        """
        self.grpc_address = f"{grpc_host}:{grpc_port}"
        logger.info(f"\uD83D\uDCE1 PhotoOfDayClient initialized for {self.grpc_address}")
    
    async def get_photo_of_day(
        self, 
        start_timestamp: int, 
        end_timestamp: int
    ) -> Optional[photo_of_day_pb2.GetPhotoOfDayResponse]:
        """
        Obtenir la photo du jour (la plus réactée dans la période).
        
        Args:
            start_timestamp: Timestamp de début (Unix timestamp)
            end_timestamp: Timestamp de fin (Unix timestamp)
            
        Returns:
            GetPhotoOfDayResponse ou None si erreur
        """
        try:
            async with grpc.aio.insecure_channel(self.grpc_address) as channel:
                stub = photo_of_day_pb2_grpc.PhotoOfDayServiceStub(channel)
                
                request = photo_of_day_pb2.GetPhotoOfDayRequest(
                    start_timestamp=start_timestamp,
                    end_timestamp=end_timestamp
                )
                
                logger.info(f"\uD83D\uDCDE Calling gRPC GetPhotoOfDay: {start_timestamp} -> {end_timestamp}")
                response = await stub.GetPhotoOfDay(request)
                
                if response.found:
                    logger.info(
                        f"✅ Photo of day found: {response.display_name}/"
                        f"{response.photo_id} ({response.total_reactions} reactions)"
                    )
                    return response
                else:
                    logger.info("ℹ️  No photo found in the specified period")
                    return None
                    
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            logger.error(f"❌ Error calling PhotoOfDay service: {e}", exc_info=True)
            return None
    
    async def get_photo_stats(
        self,
        display_name: str,
        photo_id: int
    ) -> Optional[photo_of_day_pb2.GetPhotoStatsResponse]:
        """
        Obtenir les statistiques d'une photo spécifique.
        
        Args:
            display_name: Nom d'affichage du photographe
            photo_id: ID de la photo
            
        Returns:
            GetPhotoStatsResponse ou None si erreur
        """
        try:
            async with grpc.aio.insecure_channel(self.grpc_address) as channel:
                stub = photo_of_day_pb2_grpc.PhotoOfDayServiceStub(channel)
                
                request = photo_of_day_pb2.GetPhotoStatsRequest(
                    display_name=display_name,
                    photo_id=photo_id
                )
                
                logger.info(f"\uD83D\uDCDE Calling gRPC GetPhotoStats: {display_name}/{photo_id}")
                response = await stub.GetPhotoStats(request)
                
                if response.found:
                    logger.info(f"✅ Stats found: {response.total_reactions} reactions")
                    return response
                else:
                    logger.info(f"ℹ️  No stats found for {display_name}/{photo_id}")
                    return None
                    
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting photo stats: {e}", exc_info=True)
            return None
# Singleton instance
tags_client = TagsClient()
