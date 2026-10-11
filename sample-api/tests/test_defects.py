"""
DevPilot AI - Defect Injection Verification Tests.
Verifies that the synthetic defect toggles accurately reproduce target defects
for demonstration and evaluation of DevPilot AI's 5-way Failure Taxonomy.
"""

from typing import Dict
import httpx


def test_defect_negative_quantity_allowed(client: httpx.Client, user_auth_headers: Dict[str, str]) -> None:
    """
    Verify that enabling 'negative_quantity_allowed' reproduces the regression bug:
    Orders with negative quantity succeed with 201 Created and negative order total.
    """
    # 1. Enable defect
    toggle_resp = client.post(
        "/admin/defects/toggle",
        json={"defect_name": "negative_quantity_allowed", "enabled": True},
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["defects"]["negative_quantity_allowed"] is True

    # 2. Submit negative quantity order
    payload = {
        "items": [{"product_id": 1, "quantity": -3}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload, headers=user_auth_headers)

    # In defect mode: improperly returns 201 and negative total
    assert response.status_code == 201
    data = response.json()
    assert data["items"][0]["quantity"] == -3
    assert data["total_amount"] < 0  # Bug reproduced!


def test_defect_unhandled_500_on_user_not_found(client: httpx.Client) -> None:
    """
    Verify that enabling 'unhandled_500_on_user_not_found' reproduces an uncaught server crash:
    GET /users/999 returns 500 instead of the documented 404.
    """
    # 1. Enable defect
    client.post(
        "/admin/defects/toggle",
        json={"defect_name": "unhandled_500_on_user_not_found", "enabled": True},
    )

    # 2. Query non-existent user
    response = client.get("/users/99999")
    assert response.status_code == 500  # Uncaught crash reproduced!


def test_defect_broken_schema_on_products(client: httpx.Client) -> None:
    """
    Verify that enabling 'broken_schema_on_products' reproduces a contract schema violation:
    Product price field is returned as corrupted string instead of float.
    """
    # 1. Enable defect
    client.post(
        "/admin/defects/toggle",
        json={"defect_name": "broken_schema_on_products", "enabled": True},
    )

    # 2. Query product catalog
    response = client.get("/products")
    assert response.status_code == 200
    data = response.json()
    first_item = data["items"][0]
    # Price is a corrupted string instead of a float
    assert isinstance(first_item["price"], str)
    assert "CORRUPTED_STRING" in first_item["price"]  # Contract broken!


def test_defect_auth_bypass_on_orders(client: httpx.Client) -> None:
    """
    Verify that enabling 'auth_bypass_on_orders' reproduces a security bypass defect:
    Unauthenticated user can place orders without 401 Unauthorized.
    """
    # 1. Enable defect
    client.post(
        "/admin/defects/toggle",
        json={"defect_name": "auth_bypass_on_orders", "enabled": True},
    )

    # 2. Submit order without auth headers
    payload = {
        "items": [{"product_id": 1, "quantity": 1}],
        "shipping_address": "500 Electronic Arts Way",
        "payment_method": "credit_card",
    }
    response = client.post("/orders", json=payload)  # No auth headers!
    assert response.status_code == 201  # Security bypass reproduced!


def test_admin_reset_restores_clean_baseline(client: httpx.Client) -> None:
    """Verify that /admin/reset cleanly restores all defects and database data."""
    # Enable all defects
    client.post("/admin/defects/toggle", json={"defect_name": "negative_quantity_allowed", "enabled": True})
    client.post("/admin/defects/toggle", json={"defect_name": "unhandled_500_on_user_not_found", "enabled": True})

    # Call reset
    reset_resp = client.post("/admin/reset")
    assert reset_resp.status_code == 200

    # Verify defects are all False
    defects_resp = client.get("/admin/defects")
    for name, state in defects_resp.json()["defects"].items():
        assert state is False, f"Defect '{name}' was not reset to False"
