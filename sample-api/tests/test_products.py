"""
DevPilot AI - Product Catalog Endpoint Tests (GET /products)
"""

import httpx


def test_get_products_default(client: httpx.Client) -> None:
    """Test retrieving products with default pagination."""
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 6
    assert data["skip"] == 0
    assert data["limit"] == 10
    assert len(data["items"]) == data["total"]

    # Verify item schema
    item = data["items"][0]
    assert "id" in item
    assert "name" in item
    assert "category" in item
    assert "price" in item
    assert isinstance(item["price"], (int, float))
    assert "stock" in item


def test_get_products_pagination(client: httpx.Client) -> None:
    """Test limit and skip pagination parameters."""
    response = client.get("/products?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["skip"] == 1
    assert data["limit"] == 2
    assert len(data["items"]) == 2


def test_get_products_filter_by_category(client: httpx.Client) -> None:
    """Test category filtering."""
    response = client.get("/products?category=hardware")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["category"] == "hardware"


def test_get_products_filter_nonexistent_category(client: httpx.Client) -> None:
    """Test category filtering with unknown category returns empty list."""
    response = client.get("/products?category=nonexistent_genre")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_get_products_invalid_pagination(client: httpx.Client) -> None:
    """Test rejection of negative skip or out-of-bounds limit."""
    # Negative skip
    resp1 = client.get("/products?skip=-5")
    assert resp1.status_code == 422

    # Zero limit (must be >= 1)
    resp2 = client.get("/products?limit=0")
    assert resp2.status_code == 422

    # Excessive limit (> 100)
    resp3 = client.get("/products?limit=500")
    assert resp3.status_code == 422
