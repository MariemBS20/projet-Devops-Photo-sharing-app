#!/usr/bin/env python3
"""Tests for individual photo endpoints."""

import pytest


class TestGetPhotoImage:
    """Tests for GET /photo/{display_name}/{photo_id}."""
    
    @pytest.mark.asyncio
    async def test_get_photo_image_success(self, async_client, uploaded_photo):
        """Test retrieving a photo image."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        response = await async_client.get(f"/photo/{display_name}/{photo_id}")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        
        # Check that we got the image data
        assert len(response.content) > 0
        assert response.content == uploaded_photo["image_data"]
    
    @pytest.mark.asyncio
    async def test_get_photo_image_not_found(self, async_client):
        """Test retrieving a non-existent photo."""
        response = await async_client.get("/photo/testphotographer/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestGetPhotoAttributes:
    """Tests for GET /photo/{display_name}/{photo_id}/attributes."""
    
    @pytest.mark.asyncio
    async def test_get_photo_attributes_success(self, async_client, uploaded_photo):
        """Test retrieving photo metadata."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["photo_id"] == photo_id
        assert data["display_name"] == display_name
        assert data["title"] == "untitled"  # Default value
        assert data["comment"] == ""
        assert data["location"] == ""
        assert data["author"] == ""
        assert isinstance(data["tags"], list)
        assert "created_at" in data
        assert "updated_at" in data
    
    @pytest.mark.asyncio
    async def test_get_photo_attributes_not_found(self, async_client):
        """Test retrieving attributes for non-existent photo."""
        response = await async_client.get(
            "/photo/testphotographer/999/attributes"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_get_photo_attributes_includes_tags(self, async_client, sample_image_bytes):
        """Test that attributes include auto-generated tags."""
        from unittest.mock import patch
        
        display_name = "testphotographer"
        expected_tags = ["mountain", "snow", "winter"]
        
        # Upload with specific tags
        with patch("clients.tags_client.get_tags") as mock_tags:
            mock_tags.return_value = expected_tags
            
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            upload_response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            photo_id = upload_response.json()["photo_id"]
        
        # Get attributes
        response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        
        assert response.status_code == 200
        assert response.json()["tags"] == expected_tags


class TestUpdatePhotoAttributes:
    """Tests for PUT /photo/{display_name}/{photo_id}/attributes."""
    
    @pytest.mark.asyncio
    async def test_update_photo_attributes_success(self, async_client, uploaded_photo):
        """Test updating photo metadata."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        update_data = {
            "title": "Beautiful Sunset",
            "comment": "Taken at the beach",
            "location": "Malibu, CA",
            "author": "John Doe"
        }
        
        response = await async_client.put(
            f"/photo/{display_name}/{photo_id}/attributes",
            json=update_data
        )
        
        assert response.status_code == 200
        assert response.json()["message"] == "Photo attributes updated successfully"
        
        # Verify the update
        get_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        data = get_response.json()
        assert data["title"] == "Beautiful Sunset"
        assert data["comment"] == "Taken at the beach"
        assert data["location"] == "Malibu, CA"
        assert data["author"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_update_photo_attributes_partial(self, async_client, uploaded_photo):
        """Test updating only some attributes."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        # Update only title
        update_data = {"title": "New Title"}
        
        response = await async_client.put(
            f"/photo/{display_name}/{photo_id}/attributes",
            json=update_data
        )
        
        assert response.status_code == 200
        
        # Verify only title changed
        get_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        data = get_response.json()
        assert data["title"] == "New Title"
        assert data["comment"] == ""  # Unchanged
        assert data["location"] == ""  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_photo_attributes_not_found(self, async_client):
        """Test updating non-existent photo."""
        update_data = {"title": "Test"}
        
        response = await async_client.put(
            "/photo/testphotographer/999/attributes",
            json=update_data
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_photo_attributes_cannot_change_tags(self, async_client, uploaded_photo):
        """Test that tags cannot be updated manually."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        # Get original tags
        get_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        original_tags = get_response.json()["tags"]
        
        # Try to update with tags in the payload (should be ignored)
        update_data = {
            "title": "New Title",
            "tags": ["newtag1", "newtag2"]  # This should be ignored
        }
        
        response = await async_client.put(
            f"/photo/{display_name}/{photo_id}/attributes",
            json=update_data
        )
        
        assert response.status_code == 200
        
        # Verify tags didn't change
        get_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        assert get_response.json()["tags"] == original_tags
    
    @pytest.mark.asyncio
    async def test_update_photo_attributes_empty_data(self, async_client, uploaded_photo):
        """Test updating with no data."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        response = await async_client.put(
            f"/photo/{display_name}/{photo_id}/attributes",
            json={}
        )
        
        # Should succeed but do nothing
        assert response.status_code == 200


class TestDeletePhoto:
    """Tests for DELETE /photo/{display_name}/{photo_id}."""
    
    @pytest.mark.asyncio
    async def test_delete_photo_success(self, async_client, uploaded_photo):
        """Test deleting a photo."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        response = await async_client.delete(f"/photo/{display_name}/{photo_id}")
        
        assert response.status_code == 204
        assert response.content == b""  # No body
        
        # Verify deletion
        get_response = await async_client.get(f"/photo/{display_name}/{photo_id}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_photo_not_found(self, async_client):
        """Test deleting a non-existent photo."""
        response = await async_client.delete("/photo/testphotographer/999")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_delete_photo_idempotency(self, async_client, uploaded_photo):
        """Test that deleting twice returns appropriate status codes."""
        display_name = uploaded_photo["display_name"]
        photo_id = uploaded_photo["photo_id"]
        
        # First delete - should succeed
        response1 = await async_client.delete(f"/photo/{display_name}/{photo_id}")
        assert response1.status_code == 204
        
        # Second delete - should return 404
        response2 = await async_client.delete(f"/photo/{display_name}/{photo_id}")
        assert response2.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_photo_removes_from_gallery(self, async_client, multiple_photos):
        """Test that deleted photo is removed from gallery listing."""
        display_name = multiple_photos[0]["display_name"]
        photo_id = multiple_photos[0]["photo_id"]
        
        # Verify photo is in gallery
        list_response = await async_client.get(f"/gallery/{display_name}")
        assert len(list_response.json()["items"]) == 3
        
        # Delete photo
        delete_response = await async_client.delete(f"/photo/{display_name}/{photo_id}")
        assert delete_response.status_code == 204
        
        # Verify photo is no longer in gallery
        list_response = await async_client.get(f"/gallery/{display_name}")
        data = list_response.json()
        assert len(data["items"]) == 2
        photo_ids = [item["photo_id"] for item in data["items"]]
        assert photo_id not in photo_ids


class TestPhotoWorkflow:
    """Integration tests for complete workflows."""
    
    @pytest.mark.asyncio
    async def test_full_photo_workflow(self, async_client, sample_image_bytes):
        """Test complete workflow: Upload -> Get -> Update -> Delete."""
        display_name = "testphotographer"
        
        # 1. Upload
        files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
        upload_response = await async_client.post(
            f"/gallery/{display_name}",
            files=files
        )
        assert upload_response.status_code == 201
        photo_id = upload_response.json()["photo_id"]
        
        # 2. Get image
        image_response = await async_client.get(f"/photo/{display_name}/{photo_id}")
        assert image_response.status_code == 200
        assert image_response.content == sample_image_bytes
        
        # 3. Get attributes
        attrs_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        assert attrs_response.status_code == 200
        assert attrs_response.json()["title"] == "untitled"
        
        # 4. Update attributes
        update_data = {"title": "My Photo", "location": "Paris"}
        update_response = await async_client.put(
            f"/photo/{display_name}/{photo_id}/attributes",
            json=update_data
        )
        assert update_response.status_code == 200
        
        # Verify update
        attrs_response = await async_client.get(
            f"/photo/{display_name}/{photo_id}/attributes"
        )
        data = attrs_response.json()
        assert data["title"] == "My Photo"
        assert data["location"] == "Paris"
        
        # 5. Delete
        delete_response = await async_client.delete(f"/photo/{display_name}/{photo_id}")
        assert delete_response.status_code == 204
        
        # Verify deletion
        image_response = await async_client.get(f"/photo/{display_name}/{photo_id}")
        assert image_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_upload_and_list_workflow(self, async_client, sample_image_bytes):
        """Test uploading multiple photos and listing them."""
        display_name = "testphotographer"
        
        # Gallery should be empty initially
        list_response = await async_client.get(f"/gallery/{display_name}")
        assert len(list_response.json()["items"]) == 0
        
        # Upload 3 photos
        for i in range(3):
            files = {"file": (f"test{i}.jpg", sample_image_bytes, "image/jpeg")}
            upload_response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            assert upload_response.status_code == 201
        
        # List should have 3 photos
        list_response = await async_client.get(f"/gallery/{display_name}")
        data = list_response.json()
        assert len(data["items"]) == 3
        assert data["total_count"] == 3
        
        # Photos should have sequential IDs
        photo_ids = [item["photo_id"] for item in data["items"]]
        assert photo_ids == [0, 1, 2]
