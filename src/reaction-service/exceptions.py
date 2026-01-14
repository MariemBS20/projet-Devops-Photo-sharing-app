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



class ReactionNotFoundError(HTTPException):
    """Raised when a reaction is not found."""

    def __init__(self, display_name: str, photo_id: int, reactor_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reaction by '{reactor_name}' on photo {photo_id} of '{display_name}' not found"
        )


class ReactionAlreadyExistsError(HTTPException):
    """Raised when trying to create a duplicate reaction."""

    def __init__(self, display_name: str, photo_id: int, reactor_name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Reaction by '{reactor_name}' on photo {photo_id} of '{display_name}' already exists. Use PUT to update."
        )


class InvalidReactionError(HTTPException):
    """Raised when reaction emoji is not allowed."""

    def __init__(self, reaction: str, allowed: list[str]):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reaction '{reaction}'. Allowed reactions: {', '.join(allowed)}"
        )
class DatabaseUnavailableError(HTTPException):
    """Raised when database is unavailable."""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is unavailable"
        )


async def database_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle MongoDB-specific exceptions."""
    if isinstance(exc, pymongo.errors.ServerSelectionTimeoutError):
        logger.error(f"MongoDB timeout error: {exc}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Database service is unavailable"}
        )
    
    # Re-raise if not a MongoDB error
    raise exc

