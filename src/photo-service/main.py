#!/usr/bin/env python3
"""Main FastAPI application for photo service."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymongo
from exceptions import database_exception_handler 

from config import settings
from database import lifespan
from routers import gallery, photo,photo_of_day
from clients import tags_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Custom lifespan to include tags client
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan including external services."""
    # Startup
    from database import Database
    await Database.connect()
    await tags_client.connect()
    
    yield
    
    # Shutdown
    await tags_client.disconnect()
    await Database.disconnect()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## Photo Service API

A RESTful API for managing photos and galleries.

### Features
* Upload photos to photographer galleries
* Automatic tagging using AI (tags service)
* Retrieve photos and metadata
* Update photo attributes
* Delete photos

### Dependencies
* **Photographer Service**: Validates photographer existence
* **Tags Service**: Auto-generates tags for uploaded images
* **MongoDB**: Stores photos and metadata
    """,
    lifespan=app_lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(
    pymongo.errors.ServerSelectionTimeoutError,
    database_exception_handler
)

# Include routers
app.include_router(gallery.router)
app.include_router(photo.router)
app.include_router(photo_of_day.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Photo Service API",
        "version": settings.api_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    try:
        # Try to count documents to verify DB connection
        from models import Photo
        await Photo.find().limit(1).to_list()
        
        return {
            "status": "healthy",
            "database": "connected",
            "photographer_service": settings.photographer_service_url,
            "tags_service": settings.tags_service_address
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
