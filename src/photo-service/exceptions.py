#!/usr/bin/env python3
"""Custom exceptions and error handlers."""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

import pymongo
import logging

logger = logging.getLogger(__name__)

class PhotoNotFoundError(HTTPException):
    """Raised when a photo is not found."""
    
    def __init__(self, display_name: str, photo_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo {photo_id} for photographer '{display_name}' not found"
        )


class PhotographerNotFoundError(HTTPException):
    """Raised when a photographer is not found."""
    
    def __init__(self, display_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photographer '{display_name}' not found"
        )


class PhotographerServiceUnavailableError(HTTPException):
    """Raised when photographer service is unavailable."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Photographer service is unavailable"
        )


class TagsServiceUnavailableError(HTTPException):
    """Raised when tags service is unavailable."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tags service is unavailable"
        )


class DatabaseUnavailableError(HTTPException):
    """Raised when database is unavailable."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is unavailable"
        )


class InvalidImageError(HTTPException):
    """Raised when uploaded image is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image: {reason}"
        )


class ImageTooLargeError(HTTPException):
    """Raised when uploaded image is too large."""
    
    def __init__(self, max_size_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image too large. Maximum size: {max_size_mb}MB"
        )

async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle MongoDB-specific exceptions."""
    if isinstance(exc, pymongo.errors.ServerSelectionTimeoutError):
        logger.error(f"MongoDB timeout error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database service is unavailable"}
        )
    
    raise exc