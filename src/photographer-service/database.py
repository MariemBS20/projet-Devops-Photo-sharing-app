#!/usr/bin/env python3
"""Database initialization and management."""

from contextlib import asynccontextmanager
from typing import AsyncIterator
import logging

from fastapi import FastAPI
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from config import settings
from models import Photographer

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    client: AsyncIOMotorClient | None = None
    
    @classmethod
    async def connect(cls) -> None:
        """Initialize database connection and Beanie ODM."""
        try:
            logger.info(f"Connecting to MongoDB at {settings.mongo_host}:{settings.mongo_port}")
            cls.client = AsyncIOMotorClient(settings.mongodb_url)
            
            # Initialize Beanie with document models
            await init_beanie(
                database=cls.client[settings.database_name],
                document_models=[Photographer]
            )
            
            logger.info("Successfully connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    @classmethod
    async def disconnect(cls) -> None:
        """Close database connection."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan (startup and shutdown)."""
    # Startup
    await Database.connect()
    yield
    # Shutdown
    await Database.disconnect()
