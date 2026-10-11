"""
DevPilot AI - Integration Tests for RAG Knowledge Ingestion and Retrieval.
"""

import os
import io
from fastapi.testclient import TestClient

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def test_knowledge_upload_and_search(client: TestClient) -> None:
    """Test uploading knowledge documents and querying vector store via REST API."""
    # 1. Create project
    proj_resp = client.post("/api/v1/projects", json={"name": "RAG Knowledge Project"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload QA guideline
    guideline_path = os.path.join(WORKSPACE_ROOT, "sample-data", "qa-guidelines", "boundary_testing_rules.md")
    with open(guideline_path, "rb") as f:
        file_bytes = f.read()

    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/knowledge/upload",
        files={"file": ("boundary_testing_rules.md", io.BytesIO(file_bytes), "text/markdown")},
        data={"doc_type": "qa_guideline", "title": "Boundary Testing Guidelines"},
    )
    assert upload_resp.status_code == 201
    assert upload_resp.json()["chunks_count"] >= 1

    # 3. Upload Bug Report
    bug_path = os.path.join(WORKSPACE_ROOT, "sample-data", "bug-reports", "bug_001_negative_quantity.json")
    with open(bug_path, "rb") as f:
        bug_bytes = f.read()

    bug_upload_resp = client.post(
        f"/api/v1/projects/{project_id}/knowledge/upload",
        files={"file": ("bug_001_negative_quantity.json", io.BytesIO(bug_bytes), "application/json")},
        data={"doc_type": "bug_report", "title": "Historical Bug: Negative Quantity"},
    )
    assert bug_upload_resp.status_code == 201
    assert bug_upload_resp.json()["chunks_count"] == 1

    # 4. List documents
    list_resp = client.get(f"/api/v1/projects/{project_id}/knowledge")
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) == 2

    # 5. Search knowledge base for negative order quantities
    search_payload = {
        "query": "negative item quantity in order payload",
        "endpoint_path": "/orders",
        "method": "POST",
        "top_k": 3,
    }
    search_resp = client.post(
        f"/api/v1/projects/{project_id}/knowledge/search",
        json=search_payload,
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total_found"] > 0
    results = search_data["results"]

    # Verify top result is either the historical bug or boundary rule
    top_titles = [r["doc_title"] for r in results]
    assert any("Negative Quantity" in t or "Boundary" in t for t in top_titles)

    # Verify XML bounded context tags are formatted
    preview = search_data["bounded_context_preview"]
    assert "<historical_regression_bugs>" in preview or "<qa_testing_guidelines>" in preview
