#!/usr/bin/env python3
"""Main FastAPI application for reaction service."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pymongo

# Import our modules
from config import settings
from database import Database
from routers import reactions
from exceptions import database_exception_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan including external services."""
    # Startup: runs ONCE when app starts
    logger.info("🚀 Starting Reaction Service...")
    await Database.connect()      # Connect to MongoDB

    yield  # App is now running and handling requests

    # Shutdown: runs ONCE when app stops
    logger.info("👋 Shutting down Reaction Service...")
    await Database.disconnect()
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## Reaction Service API

A RESTful API for managing photo reactions (emoji responses).

### Features
* Add reactions to photos (❤️, 👍, 😍, etc.)
* View all reactions for a photo
* Update existing reactions
* Delete reactions
* View all reactions by a photographer
    """,
    lifespan=app_lifespan,
)
    # Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Which origins can call this API
    allow_credentials=True,   # Allow cookies
    allow_methods=["*"],      # Allow all HTTP methods
    allow_headers=["*"],      # Allow all headers
)
# Include routers
app.include_router(reactions.router)
@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Reaction Service API",
        "version": settings.api_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    try:
        from models import Reaction
        await Reaction.find().limit(1).to_list()

        return {
            "status": "healthy",
            "database": "connected",
            "photographer_service": settings.photographer_service_url,
            "photo_service": settings.photo_service_url
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected"}