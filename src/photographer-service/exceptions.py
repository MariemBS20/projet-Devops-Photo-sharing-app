#!/usr/bin/env python3
"""Custom exceptions and error handlers."""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import pymongo
import logging

logger = logging.getLogger(_name_)


class PhotographerNotFoundError(HTTPException):
    """Raised when a photographer is not found."""
    
    def __init__(self, display_name: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photographer '{display_name}' does not exist"
        )


class PhotographerAlreadyExistsError(HTTPException):
    """Raised when attempting to create a photographer that already exists."""
    
    def __init__(self, display_name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Photographer '{display_name}' already exists"
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