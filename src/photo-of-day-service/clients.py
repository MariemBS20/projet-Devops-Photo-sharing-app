#!/usr/bin/env python3
"""External service clients."""

import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)


class PhotoClient:
    """HTTP client for photo service."""

    @staticmethod
    async def get_photo_url(display_name: str, photo_id: int) -> str | None:
        """Get the URL for a photo."""
        url = f"{settings.photo_service_url}/photo/{display_name}/{photo_id}"

        try:
            async with httpx.AsyncClient(timeout=settings.photo_timeout) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    logger.debug(f"Photo {photo_id} for '{display_name}' exists")
                    return url
                elif response.status_code == 404:
                    logger.warning(f"Photo {photo_id} for '{display_name}' not found")
                    return None
                else:
                    logger.error(f"Photo service returned {response.status_code}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"Timeout calling photo service")
            return None
        except httpx.RequestError as e:
            logger.error(f"Error calling photo service: {e}")
            return None

    @staticmethod
    async def check_photo_exists(display_name: str, photo_id: int) -> bool:
        """Check if a photo exists."""
        url = await PhotoClient.get_photo_url(display_name, photo_id)
        return url is not None