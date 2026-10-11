"""
DevPilot AI - Integration Tests for Project and Specification REST Endpoints.
"""

import io
from fastapi.testclient import TestClient


def test_create_and_list_projects(client: TestClient) -> None:
    """Test project workspace creation and listing."""
    resp = client.post(
        "/api/v1/projects",
        json={"name": "EA Sports FC Services", "description": "Backend services for EA Sports FC"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "EA Sports FC Services"
    assert data["slug"] == "ea-sports-fc-services"
    project_id = data["id"]

    # List projects
    list_resp = client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    projects = list_resp.json()
    assert any(p["id"] == project_id for p in projects)


def test_upload_specification_success(client: TestClient, sample_spec_content: str) -> None:
    """Test uploading valid OpenAPI JSON specification."""
    # 1. Create project
    proj_resp = client.post(
        "/api/v1/projects",
        json={"name": "EA Apex E-Commerce"},
    )
    project_id = proj_resp.json()["id"]

    # 2. Upload spec file
    file_bytes = sample_spec_content.encode("utf-8")
    files = {"file": ("openapi.json", io.BytesIO(file_bytes), "application/json")}
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files=files,
    )
    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()
    spec = upload_data["specification"]
    endpoints = upload_data["endpoints"]

    assert spec["title"] == "DevPilot AI Sample E-Commerce Target API"
    assert spec["version"] == "1.0.0"
    assert spec["endpoints_count"] == 10
    assert len(endpoints) == 10

    # 3. List specifications
    specs_resp = client.get(f"/api/v1/projects/{project_id}/specs")
    assert specs_resp.status_code == 200
    assert len(specs_resp.json()) == 1


def test_specification_deduplication(client: TestClient, sample_spec_content: str) -> None:
    """Verify that uploading identical specification returns existing entity without duplicates."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Deduplication Project"})
    project_id = proj_resp.json()["id"]

    file_bytes = sample_spec_content.encode("utf-8")

    # First upload
    resp1 = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("openapi.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert resp1.status_code == 201
    spec1_id = resp1.json()["specification"]["id"]

    # Second upload of identical content
    resp2 = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("openapi.json", io.BytesIO(file_bytes), "application/json")},
    )
    assert resp2.status_code == 201
    spec2_id = resp2.json()["specification"]["id"]

    # Should reuse existing spec ID
    assert spec1_id == spec2_id

    # Specs count remains 1
    specs_resp = client.get(f"/api/v1/projects/{project_id}/specs")
    assert len(specs_resp.json()) == 1


def test_list_endpoints_with_filters(client: TestClient, sample_spec_content: str) -> None:
    """Test querying and filtering extracted endpoints."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Filtering Project"})
    project_id = proj_resp.json()["id"]

    client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("openapi.json", io.BytesIO(sample_spec_content.encode("utf-8")), "application/json")},
    )

    # All endpoints
    all_resp = client.get(f"/api/v1/projects/{project_id}/endpoints")
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 10

    # Filter by method POST
    post_resp = client.get(f"/api/v1/projects/{project_id}/endpoints?method=POST")
    assert post_resp.status_code == 200
    for ep in post_resp.json():
        assert ep["method"] == "POST"

    # Filter by path substring 'orders'
    orders_resp = client.get(f"/api/v1/projects/{project_id}/endpoints?path=orders")
    assert orders_resp.status_code == 200
    assert len(orders_resp.json()) == 1
    assert orders_resp.json()[0]["path"] == "/orders"

    # Filter by tag 'Authentication'
    auth_resp = client.get(f"/api/v1/projects/{project_id}/endpoints?tag=Authentication")
    assert auth_resp.status_code == 200
    assert len(auth_resp.json()) == 1
    assert auth_resp.json()[0]["path"] == "/auth/login"


def test_upload_invalid_specification(client: TestClient) -> None:
    """Test rejection with 422 when invalid specification is uploaded."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Invalid Spec Project"})
    project_id = proj_resp.json()["id"]

    corrupted_content = b'{"openapi": "3.0.0", "info": {}}'  # Missing paths
    resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("bad_spec.json", io.BytesIO(corrupted_content), "application/json")},
    )
    assert resp.status_code == 422
    assert "validation error" in resp.json()["detail"].lower()
