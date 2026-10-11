"""
DevPilot AI - User Management Tests (POST /users, GET /users/{user_id})
"""

import httpx


def test_create_user_success(client: httpx.Client) -> None:
    """Test creating a new valid user account."""
    payload = {
        "username": "new_ea_engineer",
        "email": "engineer@ea.internal",
        "password": "StrongPassword2026!",
        "role": "user",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["username"] == "new_ea_engineer"
    assert data["email"] == "engineer@ea.internal"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert "password" not in data  # Ensure password hash/plain text is never leaked!


def test_create_user_duplicate_username(client: httpx.Client) -> None:
    """Test duplicate username rejection with 409 Conflict."""
    payload = {
        "username": "qa_user",  # Existing seed username
        "email": "unique_email_123@ea.internal",
        "password": "ValidPassword123!",
        "role": "user",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 409
    assert "already taken" in response.json()["detail"].lower()


def test_create_user_duplicate_email(client: httpx.Client) -> None:
    """Test duplicate email rejection with 409 Conflict."""
    payload = {
        "username": "unique_username_456",
        "email": "qa_user@devpilot.internal",  # Existing seed email
        "password": "ValidPassword123!",
        "role": "user",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


def test_create_user_invalid_email(client: httpx.Client) -> None:
    """Test validation rejection for malformed email addresses."""
    payload = {
        "username": "valid_user",
        "email": "not-a-valid-email-string",
        "password": "ValidPassword123!",
        "role": "user",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 422


def test_create_user_short_password(client: httpx.Client) -> None:
    """Test validation rejection for passwords under 6 characters."""
    payload = {
        "username": "valid_user",
        "email": "valid@ea.internal",
        "password": "123",
        "role": "user",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 422


def test_get_user_by_id_success(client: httpx.Client) -> None:
    """Test retrieving existing user by ID."""
    response = client.get("/users/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "qa_user"
    assert "password" not in data


def test_get_user_by_id_not_found(client: httpx.Client) -> None:
    """Test that requesting non-existent user returns 404 in clean mode."""
    response = client.get("/users/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_user_by_id_invalid_type(client: httpx.Client) -> None:
    """Test path parameter type validation when non-integer is passed."""
    response = client.get("/users/not_an_integer")
    assert response.status_code == 422
