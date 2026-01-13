#!/usr/bin/env python3
"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from main import app
from models import Photographer
from config import Settings


# Test database settings
TEST_SETTINGS = Settings(
    mongo_host="mongo",
    mongo_port=27017,
    database_name="photographers_test",
    auth_database_name="photographers_test",
)


@pytest_asyncio.fixture(scope="function")
async def test_db_client():
    """Create a MongoDB client for the test database."""
    client = AsyncIOMotorClient(TEST_SETTINGS.mongodb_url)
    yield client
    client.close()


@pytest_asyncio.fixture(scope="function")
async def init_test_db(test_db_client):
    """Initialize Beanie with test database."""
    await init_beanie(
        database=test_db_client[TEST_SETTINGS.database_name],
        document_models=[Photographer]
    )
    yield
    # Clean up after all tests in this function
    await Photographer.find().delete()


@pytest_asyncio.fixture
async def async_client():
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def sample_photographer_data():
    """Sample photographer data for testing."""
    return {
        "display_name": "rdoisneau",
        "first_name": "Robert",
        "last_name": "Doisneau",
        "interests": ["street", "portrait"],
    }


@pytest_asyncio.fixture
async def another_photographer_data():
    """Another sample photographer data for testing."""
    return {
        "display_name": "hsentucq",
        "first_name": "Hervé",
        "last_name": "Sentucq",
        "interests": ["landscape", "nature"],
    }


@pytest_asyncio.fixture
async def created_photographer(async_client, init_test_db, sample_photographer_data):
    """Create a photographer and return its data."""
    response = await async_client.post(
        "/photographers",
        json=sample_photographer_data
    )
    assert response.status_code == 201
    return sample_photographer_data


@pytest_asyncio.fixture
async def multiple_photographers(async_client, init_test_db, sample_photographer_data, another_photographer_data):
    """Create multiple photographers for testing."""
    # Create first photographer
    response1 = await async_client.post(
        "/photographers",
        json=sample_photographer_data
    )
    assert response1.status_code == 201
    
    # Create second photographer
    response2 = await async_client.post(
        "/photographers",
        json=another_photographer_data
    )
    assert response2.status_code == 201
    
    return [sample_photographer_data, another_photographer_data]


