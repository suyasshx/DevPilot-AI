"""
DevPilot AI - Integration Tests for Test Case Generation and Management Routes.
Tests full pipeline: Spec ingestion -> RAG retrieval -> LLM generation -> Self-repair -> DB persistence -> REST routes.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.spec import ApiEndpoint
from app.models.test_case import TestCase
from app.services.spec_service import SpecService
from app.services.generation_service import generation_service
from app.schemas.test_case import TestGenerationRequest
from app.llm.mock_provider import MockLLMProvider
from app.rag.retriever import rag_retriever


@pytest.mark.asyncio
async def test_generation_service_end_to_end(
    async_db: AsyncSession,
    sample_spec_content: str,
) -> None:
    """Verify full orchestration: RAG context retrieval -> LLM generation -> contract validation -> persistence."""
    # 1. Create Project
    project = Project(
        name="EA Sports E-Commerce QA",
        description="Integration testing for order and product APIs",
    )
    async_db.add(project)
    await async_db.commit()
    await async_db.refresh(project)

    # 2. Ingest OpenAPI spec
    spec_service = SpecService()
    spec = await spec_service.upload_specification(
        db=async_db,
        project_id=project.id,
        raw_content=sample_spec_content,
        format_type="json",
        title="Sample E-Commerce API",
        version="1.0.0",
    )

    # Index endpoints for RAG
    await rag_retriever.ingest_endpoints(async_db, project.id, spec.id)

    # 3. Find POST /api/v1/orders endpoint
    res = await async_db.execute(
        select(ApiEndpoint).where(
            ApiEndpoint.spec_id == spec.id,
            ApiEndpoint.path == "/api/v1/orders",
            ApiEndpoint.method == "POST",
        )
    )
    orders_endpoint = res.scalar_one_or_none()
    assert orders_endpoint is not None

    # 4. Request test case generation
    gen_request = TestGenerationRequest(
        endpoint_id=orders_endpoint.id,
        testing_objective="Validate boundary rules and negative quantity guards for orders",
        categories=["positive", "negative", "boundary", "security", "regression"],
    )

    session_response = await generation_service.generate_test_cases(
        db=async_db,
        request=gen_request,
        force_mock=True,
    )

    # 5. Assertions on generated response
    assert session_response.project_id == project.id
    assert session_response.endpoint_id == orders_endpoint.id
    assert session_response.endpoint_path == "/api/v1/orders"
    assert session_response.http_method == "POST"
    assert len(session_response.generated_test_cases) > 0
    assert session_response.validation_summary["persisted_count"] > 0
    assert session_response.validation_summary["parsing_attempts"] == 1

    # 6. Verify persistence in Database
    db_tests_res = await async_db.execute(
        select(TestCase).where(TestCase.endpoint_id == orders_endpoint.id)
    )
    db_tests = db_tests_res.scalars().all()
    assert len(db_tests) == len(session_response.generated_test_cases)
    assert any(t.category == "positive" for t in db_tests)
    assert any(t.category == "regression" for t in db_tests)


@pytest.mark.asyncio
async def test_generation_service_self_repair_loop(
    async_db: AsyncSession,
    sample_spec_content: str,
) -> None:
    """Verify that if LLM returns malformed JSON on first attempt, self-repair retries and succeeds."""
    project = Project(name="Self Repair Test Project")
    async_db.add(project)
    await async_db.commit()
    await async_db.refresh(project)

    spec_service = SpecService()
    spec = await spec_service.upload_specification(
        db=async_db,
        project_id=project.id,
        raw_content=sample_spec_content,
        format_type="json",
        title="Repair Spec",
    )

    res = await async_db.execute(
        select(ApiEndpoint).where(
            ApiEndpoint.spec_id == spec.id,
            ApiEndpoint.path == "/api/v1/orders",
            ApiEndpoint.method == "POST",
        )
    )
    endpoint = res.scalar_one()

    # Configure mock provider with 1 simulated malformed attempt
    mock_repair_provider = MockLLMProvider(simulate_malformed_attempts=1)

    gen_request = TestGenerationRequest(
        endpoint_id=endpoint.id,
        testing_objective="Verify self-repair resilience",
        categories=["positive", "negative"],
    )

    session_response = await generation_service.generate_test_cases(
        db=async_db,
        request=gen_request,
        llm_provider=mock_repair_provider,
    )

    # Assert that 2 parsing attempts took place (1 failure + 1 recovery)
    assert session_response.validation_summary["parsing_attempts"] == 2
    assert len(session_response.generated_test_cases) > 0


def test_test_case_api_routes(client: TestClient, sample_spec_content: str) -> None:
    """Verify REST endpoints for generation, listing, updating, and deleting test cases."""
    # 1. Create Project
    proj_resp = client.post("/api/v1/projects", json={"name": "API Test Project"})
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload Spec
    upload_resp = client.post(
        f"/api/v1/projects/{project_id}/specs/upload",
        files={"file": ("spec.json", sample_spec_content.encode("utf-8"), "application/json")},
    )
    assert upload_resp.status_code == 201

    # 3. List endpoints to find an endpoint ID
    endpoints_resp = client.get(f"/api/v1/projects/{project_id}/endpoints")
    assert endpoints_resp.status_code == 200
    endpoints = endpoints_resp.json()
    assert len(endpoints) > 0
    orders_ep = next((ep for ep in endpoints if ep["path"] == "/api/v1/orders" and ep["method"] == "POST"), endpoints[0])

    # 4. POST /projects/{project_id}/generation/generate
    gen_payload = {
        "endpoint_id": orders_ep["id"],
        "testing_objective": "Comprehensive API validation",
        "categories": ["positive", "negative", "security"],
    }
    gen_resp = client.post(f"/api/v1/projects/{project_id}/generation/generate", json=gen_payload)
    assert gen_resp.status_code == 201
    gen_data = gen_resp.json()
    assert len(gen_data["generated_test_cases"]) > 0
    first_tc = gen_data["generated_test_cases"][0]
    tc_id = first_tc["id"]

    # 5. GET /projects/{project_id}/test-cases
    list_resp = client.get(f"/api/v1/projects/{project_id}/test-cases")
    assert list_resp.status_code == 200
    tests = list_resp.json()
    assert len(tests) >= len(gen_data["generated_test_cases"])

    # 6. GET /projects/{project_id}/test-cases/{test_id}
    detail_resp = client.get(f"/api/v1/projects/{project_id}/test-cases/{tc_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == tc_id

    # 7. PATCH /projects/{project_id}/test-cases/{test_id} (Approve / update)
    patch_payload = {
        "name": "Updated Test Case Name by QA Lead",
        "is_approved": True,
        "priority": "critical",
    }
    patch_resp = client.patch(f"/api/v1/projects/{project_id}/test-cases/{tc_id}", json=patch_payload)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Updated Test Case Name by QA Lead"
    assert patch_resp.json()["is_approved"] is True
    assert patch_resp.json()["priority"] == "critical"

    # 8. DELETE /projects/{project_id}/test-cases/{test_id} (Soft-delete)
    del_resp = client.delete(f"/api/v1/projects/{project_id}/test-cases/{tc_id}")
    assert del_resp.status_code == 204

    # Verify soft-deleted item is not returned when querying active tests
    active_tests_resp = client.get(f"/api/v1/projects/{project_id}/test-cases?is_active=true")
    active_ids = [t["id"] for t in active_tests_resp.json()]
    assert tc_id not in active_ids
