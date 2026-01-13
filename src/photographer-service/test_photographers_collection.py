#!/usr/bin/env python3
"""Tests for photographers collection endpoints."""

import pytest


class TestCreatePhotographer:
    """Tests for POST /photographers."""
    
    @pytest.mark.asyncio
    async def test_create_photographer_success(self, async_client, init_test_db, sample_photographer_data):
        """Test creating a photographer successfully."""
        response = await async_client.post(
            "/photographers",
            json=sample_photographer_data
        )
        
        # Check status code
        assert response.status_code == 201
        
        # Check Location header
        assert "Location" in response.headers
        assert response.headers["Location"] == f"/photographers/{sample_photographer_data['display_name']}"
        
        # Check response body
        data = response.json()
        assert data["message"] == "Photographer created successfully"
    
    @pytest.mark.asyncio
    async def test_create_photographer_duplicate(self, async_client, created_photographer):
        """Test creating a duplicate photographer returns 409."""
        response = await async_client.post(
            "/photographers",
            json=created_photographer
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_photographer_invalid_data(self, async_client, init_test_db):
        """Test creating a photographer with invalid data."""
        invalid_data = {
            "display_name": "",  # Empty display_name
            "first_name": "Test",
            "last_name": "User",
            "interests": []
        }
        
        response = await async_client.post(
            "/photographers",
            json=invalid_data
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_create_photographer_missing_fields(self, async_client, init_test_db):
        """Test creating a photographer with missing required fields."""
        incomplete_data = {
            "display_name": "test"
            # Missing other required fields
        }
        
        response = await async_client.post(
            "/photographers",
            json=incomplete_data
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_photographer_too_long_display_name(self, async_client, init_test_db):
        """Test creating a photographer with display_name exceeding max length."""
        invalid_data = {
            "display_name": "a" * 17,  # Max is 16
            "first_name": "Test",
            "last_name": "User",
            "interests": ["test"]
        }
        
        response = await async_client.post(
            "/photographers",
            json=invalid_data
        )
        
        assert response.status_code == 422


class TestListPhotographers:
    """Tests for GET /photographers."""
    
    @pytest.mark.asyncio
    async def test_list_photographers_empty(self, async_client, init_test_db):
        """Test listing photographers when database is empty."""
        response = await async_client.get("/photographers")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["total_count"] == 0
        
        # Check X-Total-Count header
        assert response.headers["X-Total-Count"] == "0"
    
    @pytest.mark.asyncio
    async def test_list_photographers_single(self, async_client, created_photographer):
        """Test listing photographers with one photographer."""
        response = await async_client.get("/photographers")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is False
        assert data["total_count"] == 1
        
        # Check item structure
        item = data["items"][0]
        assert item["display_name"] == created_photographer["display_name"]
        assert item["link"] == f"/photographers/{created_photographer['display_name']}"
        
        # Check X-Total-Count header
        assert response.headers["X-Total-Count"] == "1"
    
    @pytest.mark.asyncio
    async def test_list_photographers_multiple(self, async_client, multiple_photographers):
        """Test listing photographers with multiple photographers."""
        response = await async_client.get("/photographers")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is False
        assert data["total_count"] == 2
        
        # Check that all photographers are present
        display_names = {item["display_name"] for item in data["items"]}
        expected_names = {p["display_name"] for p in multiple_photographers}
        assert display_names == expected_names
    
    @pytest.mark.asyncio
    async def test_list_photographers_pagination_has_more_false(self, async_client, multiple_photographers):
        """Test pagination when all items fit in one page."""
        response = await async_client.get("/photographers?offset=0&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_photographers_pagination_has_more_true(self, async_client, multiple_photographers):
        """Test pagination when there are more items available."""
        response = await async_client.get("/photographers?offset=0&limit=1")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is True
        assert data["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_list_photographers_pagination_offset(self, async_client, multiple_photographers):
        """Test pagination with offset."""
        response = await async_client.get("/photographers?offset=1&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_photographers_pagination_out_of_range(self, async_client, created_photographer):
        """Test pagination with offset beyond available items."""
        response = await async_client.get("/photographers?offset=100&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["total_count"] == 1
    
    @pytest.mark.asyncio
    async def test_list_photographers_invalid_pagination_params(self, async_client, init_test_db):
        """Test with invalid pagination parameters."""
        # Negative offset
        response = await async_client.get("/photographers?offset=-1&limit=10")
        assert response.status_code == 422
        
        # Zero limit
        response = await async_client.get("/photographers?offset=0&limit=0")
        assert response.status_code == 422
        
        # Limit too high
        response = await async_client.get("/photographers?offset=0&limit=101")
        assert response.status_code == 422


class TestHeadPhotographers:
    """Tests for HEAD /photographers."""
    
    @pytest.mark.asyncio
    async def test_head_photographers_empty(self, async_client, init_test_db):
        """Test HEAD request when database is empty."""
        response = await async_client.head("/photographers")
        
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "0"
        assert response.content == b""  # HEAD has no body
    
    @pytest.mark.asyncio
    async def test_head_photographers_with_data(self, async_client, multiple_photographers):
        """Test HEAD request with photographers in database."""
        response = await async_client.head("/photographers")
        
        assert response.status_code == 200
        assert response.headers["X-Total-Count"] == "2"
        assert response.content == b""



