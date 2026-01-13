#!/usr/bin/env python3
"""Tests for utility endpoints (root, health)."""

import pytest


class TestRootEndpoint:
    """Tests for GET /."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, async_client, init_test_db):
        """Test the root endpoint."""
        response = await async_client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "redoc" in data


class TestHealthCheck:
    """Tests for GET /health."""
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, async_client, init_test_db):
        """Test health check when database is connected."""
        response = await async_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

