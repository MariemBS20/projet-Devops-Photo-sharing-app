#!/usr/bin/env python3
"""Database connection management."""

import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from config import settings
from models import Reaction

logger = logging.getLogger(__name__)

class Database:
    """Database connection manager."""

    client: AsyncIOMotorClient | None = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize database connection and Beanie ODM."""
        logger.info(f"Connecting to MongoDB at {settings.mongo_host}:{settings.mongo_port}")

        # Create async MongoDB client
        cls.client = AsyncIOMotorClient(settings.mongodb_url)

        # Initialize Beanie with our models
        await init_beanie(
            database=cls.client[settings.database_name],
            document_models=[Reaction]
        )

        logger.info("Successfully connected to MongoDB")

    @classmethod
    async def disconnect(cls) -> None:
        """Close database connection."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")