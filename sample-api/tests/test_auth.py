"""
DevPilot AI - Authentication Endpoint Tests (POST /auth/login)
"""

import httpx


def test_login_success(client: httpx.Client) -> None:
    """Test successful authentication with valid credentials."""
    response = client.post(
        "/auth/login",
        json={"username": "qa_user", "password": "SecretPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "qa_user"
    assert data["user_id"] == 1
    assert data["role"] == "user"


def test_login_invalid_password(client: httpx.Client) -> None:
    """Test authentication failure with incorrect password."""
    response = client.post(
        "/auth/login",
        json={"username": "qa_user", "password": "WrongPassword999!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid username or password"


def test_login_nonexistent_user(client: httpx.Client) -> None:
    """Test authentication failure with unknown username."""
    response = client.post(
        "/auth/login",
        json={"username": "ghost_user", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Invalid username or password"


def test_login_inactive_user(client: httpx.Client) -> None:
    """Test that deactivated accounts cannot authenticate."""
    response = client.post(
        "/auth/login",
        json={"username": "inactive_user", "password": "InactivePass123!"},
    )
    assert response.status_code == 403
    data = response.json()
    assert "inactive" in data["detail"].lower()


def test_login_missing_fields(client: httpx.Client) -> None:
    """Test validation rejection when required fields are missing."""
    response = client.post("/auth/login", json={"username": "qa_user"})
    assert response.status_code == 422

    empty_response = client.post("/auth/login", json={})
    assert empty_response.status_code == 422
