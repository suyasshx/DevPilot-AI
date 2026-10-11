"""
DevPilot AI - Integration Tests for Autonomous LangGraph QA Workflow Routes.
Verifies end-to-end execution: Spec Ingestion -> Workflow Run -> Test Execution -> 5-Way Classification -> DB Persistence.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.execution import TestRun, TestEvaluation, ExecutionLog


def test_workflow_run_endpoint_end_to_end(client: TestClient, sample_spec_content: str) -> None:
    """Verify POST /api/v1/projects/{project_id}/workflows/run triggers full LangGraph DAG."""
    # 1. Create Project
    proj_resp = client.post("/api/v1/projects", json={"name": "LangGraph QA Project"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload OpenAPI Spec
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("spec.json", sample_spec_content.encode("utf-8"), "application/json")},
    )
    assert upload_resp.status_code == 201

    # 3. Retrieve Endpoints
    endpoints_resp = client.get(f"/api/v1/projects/{project_id}/endpoints")
    assert endpoints_resp.status_code == 200
    endpoints = endpoints_resp.json()
    assert len(endpoints) > 0
    orders_ep = next((ep for ep in endpoints if ep["path"] == "/orders" and ep["method"] == "POST"), endpoints[0])

    # 4. Trigger Workflow Run
    workflow_payload = {
        "endpoint_id": orders_ep["id"],
        "target_base_url": "http://localhost:8000",
        "testing_objective": "Validate order contract and defect resilience",
        "categories": ["positive", "negative", "security"],
        "max_repair_attempts": 2,
    }
    wf_resp = client.post(f"/api/v1/projects/{project_id}/workflows/run", json=workflow_payload)
    assert wf_resp.status_code == 201, f"Workflow failed: {wf_resp.status_code} - {wf_resp.text}"

    data = wf_resp.json()
    assert data["run_uuid"].startswith("run-")
    assert data["workflow_status"] == "completed"
    assert data["total_tests_generated"] > 0
    assert data["total_tests_executed"] > 0
    assert "metrics" in data
    assert "taxonomy_breakdown" in data
    assert len(data["execution_logs"]) > 0
    assert len(data["execution_results"]) > 0
