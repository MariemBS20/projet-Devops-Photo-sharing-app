#!/usr/bin/env python3
"""Tests for reaction service."""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from main import app
from models import Reaction


# Configuration de la base de données de test
TEST_MONGODB_URL = "mongodb://localhost:27017"
TEST_DB_NAME = "reaction_service_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def setup_database():
    """Initialize test database before each test and clean up after."""
    # Initialize database
    client = AsyncIOMotorClient(TEST_MONGODB_URL)
    database = client[TEST_DB_NAME]
    
    await init_beanie(
        database=database,
        document_models=[Reaction]
    )
    
    yield
    
    # Cleanup: delete all reactions after each test
    await Reaction.delete_all()
    client.close()


@pytest.mark.asyncio
async def test_add_reaction():
    """Test adding a reaction to a photo."""
    transport = ASGITransport(app=app)
    
    # Mock les appels externes aux autres services
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None  # Photo existe
        mock_photog.return_value = None  # Photographer existe
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add reaction
            response = await client.post(
                "/reactions/john/5",
                json={
                    "reaction": "coeur",
                    "reactor_name": "hcartier"
                }
            )

            # Assert
            assert response.status_code == 201
            data = response.json()
            assert data["display_name"] == "john"
            assert data["photo_id"] == 5
            assert data["reactor_name"] == "hcartier"
            assert data["reaction"] == "coeur"


@pytest.mark.asyncio
async def test_duplicate_reaction_fails():
    """Test that adding a duplicate reaction fails."""
    transport = ASGITransport(app=app)
    
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None
        mock_photog.return_value = None
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add first reaction
            await client.post(
                "/reactions/john/5",
                json={
                    "reaction": "coeur",
                    "reactor_name": "hcartier"
                }
            )
            
            # Try to add duplicate reaction
            response = await client.post(
                "/reactions/john/5",
                json={
                    "reaction": "sourire",
                    "reactor_name": "hcartier"
                }
            )
            
            # Should return 409 Conflict
            assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_photo_reactions():
    """Test getting all reactions for a photo."""
    transport = ASGITransport(app=app)
    
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None
        mock_photog.return_value = None
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add some reactions
            await client.post(
                "/reactions/john/5",
                json={"reaction": "coeur", "reactor_name": "hcartier"}
            )
            await client.post(
                "/reactions/john/5",
                json={"reaction": "sourire", "reactor_name": "alice"}
            )
            
            # Get all reactions
            response = await client.get("/reactions/john/5")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_reactions"] == 2
            assert len(data["reactions"]) == 2


@pytest.mark.asyncio
async def test_update_reaction():
    """Test updating an existing reaction."""
    transport = ASGITransport(app=app)
    
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None
        mock_photog.return_value = None
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add reaction
            await client.post(
                "/reactions/john/5",
                json={"reaction": "coeur", "reactor_name": "hcartier"}
            )
            
            # Update reaction
            response = await client.put(
                "/reactions/john/5/hcartier",
                json={"reaction": "sourire"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["reaction"] == "sourire"


@pytest.mark.asyncio
async def test_delete_reaction():
    """Test deleting a reaction."""
    transport = ASGITransport(app=app)
    
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None
        mock_photog.return_value = None
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Add reaction
            await client.post(
                "/reactions/john/5",
                json={"reaction": "coeur", "reactor_name": "hcartier"}
            )
            
            # Delete reaction
            response = await client.delete("/reactions/john/5/hcartier")
            
            assert response.status_code == 204
            
            # Verify it's deleted - should get empty list
            response = await client.get("/reactions/john/5")
            data = response.json()
            assert data["total_reactions"] == 0


@pytest.mark.asyncio
async def test_invalid_reaction():
    """Test that invalid reaction emoji is rejected."""
    transport = ASGITransport(app=app)
    
    with patch('clients.PhotoClient.check_photo_exists', new_callable=AsyncMock) as mock_photo, \
         patch('clients.PhotographerClient.check_photographer_exists', new_callable=AsyncMock) as mock_photog:
        
        mock_photo.return_value = None
        mock_photog.return_value = None
        
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/reactions/john/5",
                json={"reaction": "invalid_emoji", "reactor_name": "hcartier"}
            )
            
            assert response.status_code == 400