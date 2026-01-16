#!/usr/bin/env python3
"""External service clients."""
import grpc
from grpc import aio
import logging
import httpx
from config import settings
from exceptions import (
    PhotographerNotFoundError,
    PhotographerServiceUnavailableError,
    PhotoNotFoundError,
    # PhotoServiceUnavailableError n'était pas défini dans tes exceptions, on peut le créer ici si besoin
)
from grpc.aio import insecure_channel
import photo_of_day_pb2
import photo_of_day_pb2_grpc


logger = logging.getLogger(__name__)


class PhotographerClient:
    """HTTP client for photographer service."""

    @staticmethod
    async def check_photographer_exists(display_name: str) -> bool:
        """Check if a photographer exists."""
        url = f"{settings.photographer_service_url}/photographers/{display_name}"

        try:
            async with httpx.AsyncClient(timeout=settings.photographer_timeout) as client:
                response = await client.get(url)

            if response.status_code == 200:
                logger.debug(f"Photographer '{display_name}' exists")
                return True
            elif response.status_code == 404:
                logger.warning(f"Photographer '{display_name}' not found")
                raise PhotographerNotFoundError(display_name)
            else:
                logger.error(f"Photographer service returned {response.status_code}")
                raise PhotographerServiceUnavailableError()

        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"Error calling photographer service: {e}")
            raise PhotographerServiceUnavailableError()


class PhotoServiceUnavailableError(PhotographerServiceUnavailableError):
    """Raised when photo service is unavailable."""
    def __init__(self):
        super().__init__()
        self.detail = "Photo service is unavailable"


class PhotoClient:
    """HTTP client for photo service."""

    @staticmethod
    async def check_photo_exists(display_name: str, photo_id: int) -> bool:
        """Check if a photo exists."""
        url = f"{settings.photo_service_url}/photo/{display_name}/{photo_id}"

        try:
            async with httpx.AsyncClient(timeout=settings.photo_timeout) as client:
                response = await client.get(url)

            if response.status_code == 200:
                logger.debug(f"Photo {photo_id} for '{display_name}' exists")
                return True
            elif response.status_code == 404:
                logger.warning(f"Photo {photo_id} for '{display_name}' not found")
                raise PhotoNotFoundError(display_name, photo_id)
            else:
                logger.error(f"Photo service returned {response.status_code}")
                raise PhotoServiceUnavailableError()

        except (httpx.TimeoutException, httpx.RequestError) as e:
            logger.error(f"Error calling photo service: {e}")
            raise PhotoServiceUnavailableError()


 
        """
        Notify Photo of Day service that a reaction was added.
        
        ⚠️ Important: This runs in BACKGROUND and does NOT block reaction creation.
        If it fails, we just log the error.
        """
        try:
            request = photo_of_day_pb2.IncrementReactionRequest(
                display_name=display_name,
                photo_id=photo_id,
                reaction_type=reaction_type
            )

            response = await self.stub.IncrementReaction(request, timeout=5.0)

            if response.success:
                logger.info(
                    f"✅ Photo of Day updated: {display_name}/{photo_id} "
                    f"now has {response.total_reactions} reactions"
                )
                return True
            else:
                logger.warning(f"⚠️ Photo of Day returned error: {response.message}")
                return False

        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return False


# Create singleton instance
class PhotoOfDayClient:
    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self):
        address = f"{settings.PHOTO_OF_DAY_HOST}:{settings.PHOTO_OF_DAY_PORT}"
        logger.info(f"Connecting to Photo of Day service at {address}")
        self.channel = insecure_channel(address)
        self.stub = photo_of_day_pb2_grpc.PhotoOfDayServiceStub(self.channel)
        logger.info("✅ Connected to Photo of Day service")

    async def increment_reaction(self, display_name: str, photo_id: int, reaction_type: str):
        if self.stub is None:
            await self.connect()
        request = photo_of_day_pb2.IncrementReactionRequest(
            display_name=display_name,
            photo_id=photo_id,
            reaction_type=reaction_type
        )
        try:
            logger.info(f"📤 Sending IncrementReaction request for {display_name}/{photo_id} -> {reaction_type}")
            response = await self.stub.IncrementReaction(request, timeout=5.0)
            logger.info(f"✅ Reaction incremented: {response.success}")
        except grpc.RpcError as e:
            logger.error(f"❌ gRPC error: {e.code()} - {e.details()}")

photo_of_day_client = PhotoOfDayClient()