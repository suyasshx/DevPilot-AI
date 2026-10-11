"""
DevPilot AI - Integration Tests for Test Execution Runs, Results, Reruns, and Telemetry Streaming.
"""

import pytest
from fastapi.testclient import TestClient


def test_execution_runs_lifecycle_and_telemetry(client: TestClient, sample_spec_content: str) -> None:
    """
    Test full lifecycle of execution endpoints:
    1. Upload spec and execute LangGraph workflow
    2. List runs (GET /projects/{id}/runs)
    3. Get run detail (GET /projects/{id}/runs/{run_id})
    4. List run results (GET /projects/{id}/runs/{run_id}/results)
    5. Get single result detail (GET /projects/{id}/runs/{run_id}/results/{result_id})
    6. Execute regression rerun (POST /projects/{id}/runs/{run_id}/rerun)
    7. Stream telemetry via SSE (GET /projects/{id}/runs/{run_id}/stream)
    """
    # 1. Create Project
    proj_resp = client.post("/api/v1/projects", json={"name": "Execution Telemetry Project"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload Spec
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("spec.json", sample_spec_content.encode("utf-8"), "application/json")},
    )
    assert upload_resp.status_code == 201

    # 3. Retrieve Endpoints
    endpoints_resp = client.get(f"/api/v1/projects/{project_id}/endpoints")
    assert endpoints_resp.status_code == 200
    endpoints = endpoints_resp.json()
    orders_ep = next((ep for ep in endpoints if ep["path"] == "/orders" and ep["method"] == "POST"), endpoints[0])

    # 4. Trigger Workflow Run
    wf_payload = {
        "endpoint_id": orders_ep["id"],
        "target_base_url": "http://localhost:8000",
        "testing_objective": "Test order processing with defect handling",
        "categories": ["positive", "negative"],
        "max_repair_attempts": 1,
    }
    wf_resp = client.post(f"/api/v1/projects/{project_id}/workflows/run", json=wf_payload)
    assert wf_resp.status_code == 201
    wf_data = wf_resp.json()
    run_uuid = wf_data["run_uuid"]

    # 5. List Runs
    list_resp = client.get(f"/api/v1/projects/{project_id}/runs")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(r["run_uuid"] == run_uuid for r in list_data["items"])

    matched_run = next(r for r in list_data["items"] if r["run_uuid"] == run_uuid)
    db_run_id = matched_run["id"]

    # 6. Get Run Detail by DB ID and run_uuid
    detail_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["run_uuid"] == run_uuid
    assert detail_data["total_tests"] > 0
    assert detail_data["evaluation"] is not None
    assert len(detail_data["recent_logs"]) > 0

    detail_uuid_resp = client.get(f"/api/v1/projects/{project_id}/runs/{run_uuid}")
    assert detail_uuid_resp.status_code == 200
    assert detail_uuid_resp.json()["id"] == db_run_id

    # 7. List Run Results
    results_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/results")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert results_data["total"] > 0
    first_result = results_data["items"][0]
    result_id = first_result["id"]
    assert "test_id_code" in first_result
    assert "failure_category" in first_result
    assert "response_time_ms" in first_result

    # Test filtering by status
    passed_results = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/results?status=passed")
    assert passed_results.status_code == 200

    # 8. Get Single Result Detail
    single_res_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/results/{result_id}")
    assert single_res_resp.status_code == 200
    single_data = single_res_resp.json()
    assert single_data["id"] == result_id
    assert single_data["run_id"] == db_run_id

    # 9. Execute Regression Rerun (full)
    rerun_payload = {"failed_only": False}
    rerun_resp = client.post(f"/api/v1/projects/{project_id}/runs/{db_run_id}/rerun", json=rerun_payload)
    assert rerun_resp.status_code == 201
    rerun_data = rerun_resp.json()
    assert rerun_data["parent_run_id"] == db_run_id
    assert rerun_data["run_uuid"].startswith("rerun-")
    assert rerun_data["total_tests"] == detail_data["total_tests"]

    # 10. Stream Telemetry via SSE
    stream_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/stream")
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers["content-type"]
    stream_content = stream_resp.text
    assert "event: log" in stream_content or "event: completed" in stream_content
