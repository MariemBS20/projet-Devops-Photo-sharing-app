#!/usr/bin/env python3
"""Tests for gallery endpoints (upload, list photos)."""

import pytest
from unittest.mock import patch
from exceptions import PhotographerNotFoundError, PhotographerServiceUnavailableError


class TestUploadPhoto:
    """Tests for POST /gallery/{display_name}."""
    
    @pytest.mark.asyncio
    async def test_upload_photo_success(self, async_client, sample_image_bytes):
        """Test uploading a photo successfully."""
        display_name = "testphotographer"
        
        files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
        response = await async_client.post(
            f"/gallery/{display_name}",
            files=files
        )
        
        assert response.status_code == 201
        
        # Check Location header
        assert "Location" in response.headers
        assert response.headers["Location"].startswith(f"/photo/{display_name}/")
        
        # Check response body
        data = response.json()
        assert data["message"] == "Photo uploaded successfully"
        assert "photo_id" in data
        assert data["photo_id"] == 0  # First photo
    
    @pytest.mark.asyncio
    async def test_upload_multiple_photos_sequential_ids(self, async_client, sample_image_bytes):
        """Test that multiple uploads get sequential IDs."""
        display_name = "testphotographer"
        
        photo_ids = []
        for i in range(3):
            files = {"file": (f"test{i}.jpg", sample_image_bytes, "image/jpeg")}
            response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            assert response.status_code == 201
            photo_ids.append(response.json()["photo_id"])
        
        # Check sequential IDs
        assert photo_ids == [0, 1, 2]
    
    @pytest.mark.asyncio
    async def test_upload_photo_photographer_not_found(self, async_client, sample_image_bytes):
        """Test uploading when photographer doesn't exist."""
        display_name = "nonexistent"
        
        # Mock photographer client to raise not found
        with patch("clients.PhotographerClient.check_photographer_exists") as mock:
            mock.side_effect = PhotographerNotFoundError(display_name)
            
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_photo_photographer_service_unavailable(self, async_client, sample_image_bytes):
        """Test uploading when photographer service is down."""
        display_name = "testphotographer"
        
        # Mock photographer client to raise service unavailable
        with patch("clients.PhotographerClient.check_photographer_exists") as mock:
            mock.side_effect = PhotographerServiceUnavailableError()
            
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            assert response.status_code == 503
            assert "unavailable" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_photo_invalid_image_type(self, async_client):
        """Test uploading a non-image file."""
        display_name = "testphotographer"
        
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        response = await async_client.post(
            f"/gallery/{display_name}",
            files=files
        )
        
        assert response.status_code == 400
        assert "Invalid image" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_photo_corrupted_image(self, async_client, invalid_image_bytes):
        """Test uploading corrupted image data."""
        display_name = "testphotographer"
        
        files = {"file": ("test.jpg", invalid_image_bytes, "image/jpeg")}
        response = await async_client.post(
            f"/gallery/{display_name}",
            files=files
        )
        
        assert response.status_code == 400
        assert "Invalid image" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_upload_photo_with_tags(self, async_client, sample_image_bytes):
        """Test that tags are generated for uploaded photo."""
        display_name = "testphotographer"
        
        # Mock tags service to return specific tags
        with patch("clients.tags_client.get_tags") as mock_tags:
            mock_tags.return_value = ["sunset", "beach", "ocean"]
            
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            assert response.status_code == 201
            photo_id = response.json()["photo_id"]
            
            # Verify tags were stored
            attrs_response = await async_client.get(
                f"/photo/{display_name}/{photo_id}/attributes"
            )
            assert attrs_response.status_code == 200
            assert attrs_response.json()["tags"] == ["sunset", "beach", "ocean"]
    
    @pytest.mark.asyncio
    async def test_upload_photo_tags_service_failure(self, async_client, sample_image_bytes):
        """Test that upload succeeds even if tags service fails."""
        display_name = "testphotographer"
        
        # Mock tags service to fail
        with patch("clients.tags_client.get_tags") as mock_tags:
            mock_tags.return_value = []  # Service returns empty on failure
            
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            response = await async_client.post(
                f"/gallery/{display_name}",
                files=files
            )
            
            # Should succeed with empty tags
            assert response.status_code == 201
            photo_id = response.json()["photo_id"]
            
            # Verify empty tags
            attrs_response = await async_client.get(
                f"/photo/{display_name}/{photo_id}/attributes"
            )
            assert attrs_response.status_code == 200
            assert attrs_response.json()["tags"] == []


class TestListPhotos:
    """Tests for GET /gallery/{display_name}."""
    
    @pytest.mark.asyncio
    async def test_list_photos_empty(self, async_client):
        """Test listing photos when gallery is empty."""
        display_name = "testphotographer"
        
        response = await async_client.get(f"/gallery/{display_name}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["total_count"] == 0
    
    @pytest.mark.asyncio
    async def test_list_photos_single(self, async_client, uploaded_photo):
        """Test listing photos with one photo."""
        display_name = uploaded_photo["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is False
        assert data["total_count"] == 1
        
        # Check item structure
        item = data["items"][0]
        assert item["photo_id"] == uploaded_photo["photo_id"]
        assert item["link"] == f"/photo/{display_name}/{uploaded_photo['photo_id']}"
    
    @pytest.mark.asyncio
    async def test_list_photos_multiple(self, async_client, multiple_photos):
        """Test listing multiple photos."""
        display_name = multiple_photos[0]["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 3
        assert data["has_more"] is False
        assert data["total_count"] == 3
        
        # Check all photos are present
        photo_ids = {item["photo_id"] for item in data["items"]}
        expected_ids = {p["photo_id"] for p in multiple_photos}
        assert photo_ids == expected_ids
    
    @pytest.mark.asyncio
    async def test_list_photos_pagination_has_more_false(self, async_client, multiple_photos):
        """Test pagination when all items fit in one page."""
        display_name = multiple_photos[0]["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}?offset=0&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 3
        assert data["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_photos_pagination_has_more_true(self, async_client, multiple_photos):
        """Test pagination when there are more items available."""
        display_name = multiple_photos[0]["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}?offset=0&limit=1")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is True
        assert data["total_count"] == 3
    
    @pytest.mark.asyncio
    async def test_list_photos_pagination_offset(self, async_client, multiple_photos):
        """Test pagination with offset."""
        display_name = multiple_photos[0]["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}?offset=1&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is False
    
    @pytest.mark.asyncio
    async def test_list_photos_pagination_out_of_range(self, async_client, uploaded_photo):
        """Test pagination with offset beyond available items."""
        display_name = uploaded_photo["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}?offset=100&limit=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["total_count"] == 1
    
    @pytest.mark.asyncio
    async def test_list_photos_invalid_pagination_params(self, async_client):
        """Test with invalid pagination parameters."""
        display_name = "testphotographer"
        
        # Negative offset
        response = await async_client.get(f"/gallery/{display_name}?offset=-1&limit=10")
        assert response.status_code == 422
        
        # Zero limit
        response = await async_client.get(f"/gallery/{display_name}?offset=0&limit=0")
        assert response.status_code == 422
        
        # Limit too high
        response = await async_client.get(f"/gallery/{display_name}?offset=0&limit=101")
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_photos_photographer_not_found(self, async_client):
        """Test listing photos for non-existent photographer."""
        display_name = "nonexistent"
        
        # Mock photographer client to raise not found
        with patch("clients.PhotographerClient.check_photographer_exists") as mock:
            mock.side_effect = PhotographerNotFoundError(display_name)
            
            response = await async_client.get(f"/gallery/{display_name}")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_list_photos_sorted_by_id(self, async_client, multiple_photos):
        """Test that photos are sorted by photo_id."""
        display_name = multiple_photos[0]["display_name"]
        
        response = await async_client.get(f"/gallery/{display_name}")
        
        assert response.status_code == 200
        
        data = response.json()
        photo_ids = [item["photo_id"] for item in data["items"]]
        
        # Should be sorted in ascending order
        assert photo_ids == sorted(photo_ids)
