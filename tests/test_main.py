"""
Basic tests for the flashcards application
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_home_page():
    """Test home page loads"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Chinese-English Flashcards" in response.text


def test_api_docs():
    """Test API documentation is accessible"""
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_spec():
    """Test OpenAPI specification"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "openapi" in spec
    assert "info" in spec
    assert spec["info"]["title"] == "Chinese-English Flashcards"


# Note: These tests would require proper test database setup
# For full integration tests, you would need:
# 1. Test Supabase project or mock database
# 2. Test user authentication
# 3. Test CRUD operations
# 4. Test learning algorithm

class TestAuthEndpoints:
    """Test authentication endpoints (without actual database calls)"""
    
    def test_register_endpoint_exists(self):
        """Test register endpoint exists (will fail without proper setup)"""
        response = client.post("/api/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        })
        # This will fail without proper Supabase setup, but tests endpoint exists
        assert response.status_code in [200, 400, 422, 500]
    
    def test_login_endpoint_exists(self):
        """Test login endpoint exists"""
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "testpassword"
        })
        # This will fail without proper setup, but tests endpoint exists
        assert response.status_code in [200, 401, 422, 500]


class TestUserEndpoints:
    """Test user management endpoints"""
    
    def test_users_endpoint_exists(self):
        """Test users list endpoint exists"""
        response = client.get("/api/users/")
        # Will fail without auth/database, but tests endpoint exists
        assert response.status_code in [200, 401, 500]


class TestDeckEndpoints:
    """Test deck management endpoints"""
    
    def test_decks_endpoint_requires_auth(self):
        """Test decks endpoint requires authentication"""
        response = client.get("/api/decks/")
        assert response.status_code == 401  # Should require authentication


if __name__ == "__main__":
    pytest.main([__file__])