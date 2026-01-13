#!/usr/bin/env python3
"""Tests for utility endpoints (root, health)."""

import pytest


class TestRootEndpoint:
    """Tests for GET /."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client):
        """Test the root endpoint."""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "redoc" in data
        assert data["message"] == "Photo Service API"


class TestHealthCheck:
    """Tests for GET /health."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, async_client):
        """Test health check when database is connected."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
        assert "photographer_service" in data
        assert "tags_service" in data
