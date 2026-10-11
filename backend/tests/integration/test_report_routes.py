"""
DevPilot AI - Integration Tests for Report Export Routes.
Verifies GET /projects/{id}/runs/{run_id}/report.html and /report/download.
"""

import pytest
from fastapi.testclient import TestClient


def test_html_report_endpoints_lifecycle(client: TestClient, sample_spec_content: str) -> None:
    """
    Test full lifecycle of HTML report generation and downloading:
    1. Upload spec and execute workflow
    2. View HTML report inline (GET /report.html)
    3. Download HTML report as attachment (GET /report/download)
    4. Verify 404 error responses for invalid projects or runs
    """
    # 1. Create Project & Upload Spec
    proj_resp = client.post("/api/v1/projects", json={"name": "Report Demo Project"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("spec.json", sample_spec_content.encode("utf-8"), "application/json")},
    )
    assert upload_resp.status_code == 201

    endpoints_resp = client.get(f"/api/v1/projects/{project_id}/endpoints")
    assert endpoints_resp.status_code == 200
    endpoints = endpoints_resp.json()
    target_ep = next((ep for ep in endpoints if ep["path"] == "/orders" and ep["method"] == "POST"), endpoints[0])

    # 2. Trigger Workflow Run
    wf_payload = {
        "endpoint_id": target_ep["id"],
        "target_base_url": "http://localhost:8000",
        "testing_objective": "Test order processing for reporting demonstration",
        "categories": ["positive", "negative"],
        "max_repair_attempts": 1,
    }
    wf_resp = client.post(f"/api/v1/projects/{project_id}/workflows/run", json=wf_payload)
    assert wf_resp.status_code == 201
    wf_data = wf_resp.json()
    run_uuid = wf_data["run_uuid"]

    # Retrieve DB Run ID from list endpoint
    list_resp = client.get(f"/api/v1/projects/{project_id}/runs")
    assert list_resp.status_code == 200
    runs = list_resp.json()["items"]
    matched_run = next(r for r in runs if r["run_uuid"] == run_uuid)
    db_run_id = matched_run["id"]

    # 3. View HTML Report Inline
    report_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/report.html")
    assert report_resp.status_code == 200
    assert "text/html" in report_resp.headers["content-type"]
    assert f'inline; filename="report-{db_run_id}.html"' in report_resp.headers["content-disposition"]
    html_content = report_resp.text
    assert "<!DOCTYPE html>" in html_content
    assert "DevPilot AI" in html_content
    assert "Report Demo Project" in html_content
    assert run_uuid in html_content
    assert "5-Way Failure Taxonomy Breakdown" in html_content
    assert "Execution Audit Log Transcript" in html_content

    # Can also view by run_uuid
    report_uuid_resp = client.get(f"/api/v1/projects/{project_id}/runs/{run_uuid}/report.html")
    assert report_uuid_resp.status_code == 200
    assert "<!DOCTYPE html>" in report_uuid_resp.text

    # 4. Download HTML Report Attachment
    download_resp = client.get(f"/api/v1/projects/{project_id}/runs/{db_run_id}/report/download")
    assert download_resp.status_code == 200
    assert "text/html" in download_resp.headers["content-type"]
    assert f'attachment; filename="devpilot-report-{db_run_id}.html"' in download_resp.headers["content-disposition"]
    assert "<!DOCTYPE html>" in download_resp.text

    # 5. Verify 404 for nonexistent run or project
    missing_proj = client.get("/api/v1/projects/fake-proj-id/runs/run-1/report.html")
    assert missing_proj.status_code == 404

    missing_run = client.get(f"/api/v1/projects/{project_id}/runs/fake-run-id/report.html")
    assert missing_run.status_code == 404
