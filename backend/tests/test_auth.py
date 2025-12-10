from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
import pytest
from unittest.mock import MagicMock, patch
from app.core.auth import verify_authorized_user

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Insider-Alpha"}

def test_protected_route_unauthorized():
    # Ensure no dependency overrides
    app.dependency_overrides = {}
    response = client.get("/protected")
    assert response.status_code == 401

def test_protected_route_success():
    async def mock_dependency():
        return {"email": "test@example.com"}
    
    app.dependency_overrides[verify_authorized_user] = mock_dependency
    
    response = client.get("/protected")
    assert response.status_code == 200
    assert response.json() == {"message": "You are authorized!"}
    
    # Clean up
    app.dependency_overrides = {}

@patch("app.core.auth.oauth.google.authorize_access_token")
def test_auth_callback_success(mock_token):
    mock_token.return_value = {
        "userinfo": {
            "email": "test@example.com",
            "name": "Test User"
        }
    }
    
    # We need to ensure ALLOWED_USERS contains test@example.com
    # settings.ALLOWED_USERS is loaded from .env which we set to ["test@example.com"]
    
    response = client.get("/auth/callback")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "test@example.com"
    
    # Check if cookie is set
    assert "session" in response.cookies

@patch("app.core.auth.oauth.google.authorize_access_token")
def test_auth_callback_forbidden(mock_token):
    mock_token.return_value = {
        "userinfo": {
            "email": "intruder@example.com",
            "name": "Intruder"
        }
    }
    
    response = client.get("/auth/callback")
    assert response.status_code == 403
