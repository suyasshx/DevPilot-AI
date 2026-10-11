"""
DevPilot AI - Order Processing Endpoint Tests (POST /orders)
"""

from typing import Dict
import httpx


def test_create_order_success(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test successful order creation with authenticated user."""
    payload = {
        "items": [{"product_id": 1, "quantity": 2}],
        "shipping_address": "500 Electronic Arts Way, Redwood City, CA",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 100
    assert data["user_id"] == 1
    assert data["status"] == "pending"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["unit_price"] == 69.99
    assert data["total_amount"] == 139.98

    # Verify inventory was decremented: Product 1 originally had stock 50, now 48
    prod_resp = client.get("/products")
    prod_items = {p["id"]: p for p in prod_resp.json()["items"]}
    assert prod_items[1]["stock"] == 48


def test_create_order_unauthenticated(client: httpx.Client) -> None:
    """Test that placing an order without authentication returns 401."""
    payload = {
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload)
    assert response.status_code == 401
    assert "missing" in response.json()["detail"].lower()


def test_create_order_invalid_token(client: httpx.Client) -> None:
    """Test that placing an order with invalid token returns 401."""
    payload = {
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    headers = {"Authorization": "Bearer invalid_gibberish_token"}
    response = client.post("/orders", json=payload, headers=headers)
    assert response.status_code == 401


def test_create_order_nonexistent_product(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test rejection when product ID does not exist."""
    payload = {
        "items": [{"product_id": 99999, "quantity": 1}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"].lower()


def test_create_order_insufficient_stock(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test rejection when ordered quantity exceeds current inventory stock."""
    # Product 6 has stock 0
    payload = {
        "items": [{"product_id": 6, "quantity": 1}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 400
    assert "insufficient stock" in response.json()["detail"].lower()


def test_create_order_negative_quantity_clean_mode(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test boundary validation: negative quantity is rejected with 422 in clean mode."""
    payload = {
        "items": [{"product_id": 1, "quantity": -5}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 422
    assert "must be >= 1" in response.json()["detail"].lower()


def test_create_order_zero_quantity_clean_mode(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test boundary validation: zero quantity is rejected with 422 in clean mode."""
    payload = {
        "items": [{"product_id": 1, "quantity": 0}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 422


def test_create_order_empty_items(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """Test validation rejection when items array is empty."""
    payload = {
        "items": [],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)
    assert response.status_code == 422
