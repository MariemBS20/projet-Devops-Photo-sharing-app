#!/usr/bin/env python3
"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymongo

from config import settings
from database import lifespan
from routers.photographers_item import router as photographers_item_router
from routers.photographers_collection import router as photographers_collection_router
from exceptions import database_exception_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## Photographer Service API

A RESTful API for managing photographers and their information.

### Features
* Create, read, update, and delete photographers
* Paginated listing of photographers
* MongoDB backend with Beanie ODM

### Authentication
Currently, this API does not require authentication.
    """,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "photographers",
            "description": "Operations on the photographers (collection and individual resources)"
        }
    ]
)

# Add CORS middleware (configure as needed)
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
app.include_router(photographers_collection_router)
app.include_router(photographers_item_router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Photographer Service API",
        "version": settings.api_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    try:
        # Try to count documents to verify DB connection
        from models import Photographer
        await Photographer.count()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
