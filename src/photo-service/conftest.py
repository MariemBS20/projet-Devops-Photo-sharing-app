#!/usr/bin/env python3
"""Test configuration and fixtures for photo service."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from unittest.mock import AsyncMock, patch
from io import BytesIO
from PIL import Image

from main import app
from models import Photo, PhotoIdCounter
from config import Settings


# Test database settings
TEST_SETTINGS = Settings(
    mongo_host="mongo",
    mongo_port=27017,
    database_name="photos_test",
    auth_database_name="photos_test",
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
        document_models=[Photo, PhotoIdCounter]
    )
    yield
    # Clean up after tests
    await Photo.find().delete()
    await PhotoIdCounter.find().delete()


@pytest_asyncio.fixture
async def mock_photographer_client():
    """Mock the photographer service client."""
    with patch("clients.PhotographerClient.check_photographer_exists") as mock:
        mock.return_value = True
        yield mock


@pytest_asyncio.fixture
async def mock_tags_client():
    """Mock the tags service client."""
    with patch("clients.tags_client.get_tags") as mock:
        mock.return_value = ["landscape", "nature", "sunset"]
        yield mock


@pytest_asyncio.fixture
async def async_client(init_test_db, mock_photographer_client, mock_tags_client):
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
def sample_image_bytes():
    """Generate a valid JPEG image as bytes."""
    img = Image.new('RGB', (100, 100), color='red')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    return buf.getvalue()


@pytest_asyncio.fixture
def large_image_bytes():
    """Generate a large JPEG image (>10MB) for testing size limits."""
    # Create a large image that will exceed 10MB when encoded
    img = Image.new('RGB', (5000, 5000), color='blue')
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=100)
    buf.seek(0)
    return buf.getvalue()


@pytest_asyncio.fixture
def invalid_image_bytes():
    """Generate invalid image data."""
    return b"this is not a valid image"


@pytest_asyncio.fixture
async def uploaded_photo(async_client, sample_image_bytes):
    """Upload a photo and return its data."""
    display_name = "testphotographer"
    
    files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
    response = await async_client.post(
        f"/gallery/{display_name}",
        files=files
    )
    
    assert response.status_code == 201
    photo_id = response.json()["photo_id"]
    
    return {
        "display_name": display_name,
        "photo_id": photo_id,
        "image_data": sample_image_bytes
    }


@pytest_asyncio.fixture
async def multiple_photos(async_client, sample_image_bytes):
    """Upload multiple photos for testing."""
    display_name = "testphotographer"
    photos = []
    
    for i in range(3):
        files = {"file": (f"test{i}.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            f"/gallery/{display_name}",
            files=files
        )
        
        assert response.status_code == 201
        photo_id = response.json()["photo_id"]
        
        photos.append({
            "display_name": display_name,
            "photo_id": photo_id
        })
    
    return photos
