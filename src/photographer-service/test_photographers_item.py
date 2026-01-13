#!/usr/bin/env python3
"""Tests for individual photographer endpoints."""

import pytest


class TestGetPhotographer:
    """Tests for GET /photographers/{display_name}."""
    
    @pytest.mark.asyncio
    async def test_get_photographer_success(self, async_client, created_photographer):
        """Test retrieving an existing photographer."""
        display_name = created_photographer["display_name"]
        response = await async_client.get(f"/photographers/{display_name}")
        
        assert response.status_code == 200
        
        # Check response data
        data = response.json()
        assert data["display_name"] == created_photographer["display_name"]
        assert data["first_name"] == created_photographer["first_name"]
        assert data["last_name"] == created_photographer["last_name"]
        assert data["interests"] == created_photographer["interests"]
    
    @pytest.mark.asyncio
    async def test_get_photographer_not_found(self, async_client, init_test_db):
        """Test retrieving a non-existent photographer."""
        response = await async_client.get("/photographers/nonexistent")
        
        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_photographer_special_characters(self, async_client, init_test_db):
        """Test with special characters in display_name."""
        # Create photographer with allowed special chars
        data = {
            "display_name": "test_user",
            "first_name": "Test",
            "last_name": "User",
            "interests": ["test"]
        }
        
        create_response = await async_client.post("/photographers", json=data)
        assert create_response.status_code == 201
        
        # Retrieve it
        response = await async_client.get("/photographers/test_user")
        assert response.status_code == 200
        assert response.json()["display_name"] == "test_user"


class TestUpdatePhotographer:
    """Tests for PUT /photographers/{display_name}."""
    
    @pytest.mark.asyncio
    async def test_update_photographer_success(self, async_client, created_photographer):
        """Test updating an existing photographer."""
        display_name = created_photographer["display_name"]
        
        updated_data = {
            "display_name": display_name,  # Must match path param
            "first_name": "Updated",
            "last_name": "Name",
            "interests": ["portrait", "landscape", "street"]
        }
        
        response = await async_client.put(
            f"/photographers/{display_name}",
            json=updated_data
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Photographer updated successfully"
        
        # Verify the update by retrieving the photographer
        get_response = await async_client.get(f"/photographers/{display_name}")
        data = get_response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["interests"] == ["portrait", "landscape", "street"]
    
    @pytest.mark.asyncio
    async def test_update_photographer_not_found(self, async_client, init_test_db, sample_photographer_data):
        """Test updating a non-existent photographer."""
        response = await async_client.put(
            "/photographers/nonexistent",
            json={
                "display_name": "nonexistent",
                "first_name": "Test",
                "last_name": "User",
                "interests": ["test"]
            }
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_photographer_display_name_mismatch(self, async_client, created_photographer):
        """Test updating with mismatched display_name."""
        display_name = created_photographer["display_name"]
        
        mismatched_data = {
            "display_name": "different_name",  # Doesn't match path param
            "first_name": "Test",
            "last_name": "User",
            "interests": ["test"]
        }
        
        response = await async_client.put(
            f"/photographers/{display_name}",
            json=mismatched_data
        )
        
        assert response.status_code == 422
        assert "must be identical" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_update_photographer_invalid_data(self, async_client, created_photographer):
        """Test updating with invalid data."""
        display_name = created_photographer["display_name"]
        
        invalid_data = {
            "display_name": display_name,
            "first_name": "",  # Empty string
            "last_name": "User",
            "interests": ["test"]
        }
        
        response = await async_client.put(
            f"/photographers/{display_name}",
            json=invalid_data
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_photographer_partial_data(self, async_client, created_photographer):
        """Test that PUT requires all fields (PUT semantics)."""
        display_name = created_photographer["display_name"]
        
        partial_data = {
            "display_name": display_name,
            "first_name": "Updated"
            # Missing last_name and interests
        }
        
        response = await async_client.put(
            f"/photographers/{display_name}",
            json=partial_data
        )
        
        assert response.status_code == 422  # Missing required fields


class TestDeletePhotographer:
    """Tests for DELETE /photographers/{display_name}."""
    
    @pytest.mark.asyncio
    async def test_delete_photographer_success(self, async_client, created_photographer):
        """Test deleting an existing photographer."""
        display_name = created_photographer["display_name"]
        
        response = await async_client.delete(f"/photographers/{display_name}")
        
        assert response.status_code == 204
        assert response.content == b""  # DELETE 204 has no body
        
        # Verify deletion by trying to retrieve
        get_response = await async_client.get(f"/photographers/{display_name}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_photographer_not_found(self, async_client, init_test_db):
        """Test deleting a non-existent photographer."""
        response = await async_client.delete("/photographers/nonexistent")
        
        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_delete_photographer_idempotency(self, async_client, created_photographer):
        """Test that deleting twice returns appropriate status codes."""
        display_name = created_photographer["display_name"]
        
        # First delete - should succeed
        response1 = await async_client.delete(f"/photographers/{display_name}")
        assert response1.status_code == 204
        
        # Second delete - should return 404
        response2 = await async_client.delete(f"/photographers/{display_name}")
        assert response2.status_code == 404


class TestPhotographerWorkflow:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_crud_workflow(self, async_client, init_test_db, sample_photographer_data):
        """Test complete CRUD workflow: Create -> Read -> Update -> Delete."""
        display_name = sample_photographer_data["display_name"]
        
        # 1. Create
        create_response = await async_client.post(
            "/photographers",
            json=sample_photographer_data
        )
        assert create_response.status_code == 201
        
        # 2. Read
        read_response = await async_client.get(f"/photographers/{display_name}")
        assert read_response.status_code == 200
        assert read_response.json()["first_name"] == sample_photographer_data["first_name"]
        
        # 3. Update
        updated_data = {
            **sample_photographer_data,
            "first_name": "Updated"
        }
        update_response = await async_client.put(
            f"/photographers/{display_name}",
            json=updated_data
        )
        assert update_response.status_code == 200
        
        # Verify update
        read_after_update = await async_client.get(f"/photographers/{display_name}")
        assert read_after_update.json()["first_name"] == "Updated"
        
        # 4. Delete
        delete_response = await async_client.delete(f"/photographers/{display_name}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        read_after_delete = await async_client.get(f"/photographers/{display_name}")
        assert read_after_delete.status_code == 404
    
    @pytest.mark.asyncio
    async def test_create_list_workflow(self, async_client, init_test_db, sample_photographer_data, another_photographer_data):
        """Test creating multiple photographers and listing them."""
        # Create first photographer
        await async_client.post("/photographers", json=sample_photographer_data)
        
        # List should have 1
        list_response1 = await async_client.get("/photographers")
        assert len(list_response1.json()["items"]) == 1
        
        # Create second photographer
        await async_client.post("/photographers", json=another_photographer_data)
        
        # List should have 2
        list_response2 = await async_client.get("/photographers")
        data = list_response2.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 2


