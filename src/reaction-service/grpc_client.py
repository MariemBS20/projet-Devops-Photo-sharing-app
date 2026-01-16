#!/usr/bin/env python3
"""gRPC client for Photo of Day service."""

import logging
import grpc
from config import settings
import photo_of_day_pb2
import photo_of_day_pb2_grpc

logger = logging.getLogger(__name__)


class PhotoOfDayClient:
    """gRPC client for Photo of Day service."""

    def __init__(self):
        """Initialize gRPC client."""
        self.address = settings.photo_of_day_grpc_address
        logger.info(f"Initializing PhotoOfDayClient with address: {self.address}")

    async def notify_photo_like(
        self, 
        photographer_display_name: str, 
        photo_id: int, 
        reaction_type: str
    ) -> dict:
        """
        Notify Photo of Day service about a new like.
        
        Args:
            photographer_display_name: Name of the photographer
            photo_id: ID of the photo
            reaction_type: Type of reaction (coeur, pouce, etc.)
            
        Returns:
            dict with success status and current like count
        """
        try:
            async with grpc.aio.insecure_channel(self.address) as channel:
                stub = photo_of_day_pb2_grpc.PhotoOfDayServiceStub(channel)
                
                request = photo_of_day_pb2.PhotoLikeRequest(
                    photographer_display_name=photographer_display_name,
                    photo_id=photo_id,
                    reaction_type=reaction_type
                )
                
                response = await stub.NotifyPhotoLike(request)
                
                logger.info(
                    f"Notified Photo of Day service: {photographer_display_name}/{photo_id} "
                    f"- {response.message}"
                )
                
                return {
                    "success": response.success,
                    "current_like_count": response.current_like_count,
                    "message": response.message
                }
                
        except grpc.RpcError as e:
            logger.error(f"gRPC error notifying Photo of Day service: {e.code()} - {e.details()}")
            return {
                "success": False,
                "current_like_count": 0,
                "message": f"Failed to notify: {e.details()}"
            }
        except Exception as e:
            logger.error(f"Unexpected error notifying Photo of Day service: {str(e)}")
            return {
                "success": False,
                "current_like_count": 0,
                "message": f"Unexpected error: {str(e)}"
            }


# Singleton instance
photo_of_day_client = PhotoOfDayClient()