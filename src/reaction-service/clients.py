#!/usr/bin/env python3
"""External service clients."""

import logging
import httpx
from config import settings
from exceptions import (
    PhotographerNotFoundError,
    PhotographerServiceUnavailableError,
    PhotoNotFoundError,
    # PhotoServiceUnavailableError n'était pas défini dans tes exceptions, on peut le créer ici si besoin
)

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
