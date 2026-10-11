"""
DevPilot AI - Unit Tests for ReportService and HTML Template Rendering.
Verifies offline report generation, 5-way taxonomy visualization, and evidentiary payload formatting.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.spec import ApiSpecification, ApiEndpoint
from app.models.test_case import TestCase
from app.models.execution import TestRun, TestResult, ExecutionLog
from app.models.evaluation import TestEvaluation
from app.services.report_service import ReportService
from app.db.base import utc_now


@pytest.mark.asyncio
async def test_report_service_renders_html_with_all_components(async_db: AsyncSession) -> None:
    """Verify that ReportService renders a complete, offline-viewable HTML test report."""
    # 1. Setup Project & Spec
    project = Project(
        name="EA Sports FC Services",
        slug="ea-sports-fc-services",
        description="Core match and orders services",
    )
    async_db.add(project)
    await async_db.flush()

    spec = ApiSpecification(
        project_id=project.id,
        title="FC Core API",
        version="2.0.0",
        spec_format="json",
        raw_content="{}",
        checksum_sha256="sha-fc-12345",
    )
    async_db.add(spec)
    await async_db.flush()

    endpoint = ApiEndpoint(
        spec_id=spec.id,
        path="/matches",
        method="POST",
        summary="Create Match",
        request_body_schema={},
        responses_schema={},
    )
    async_db.add(endpoint)
    await async_db.flush()

    # 2. Setup TestCases
    tc1 = TestCase(
        project_id=project.id,
        endpoint_id=endpoint.id,
        test_id_code="TC-MAT-001",
        name="Create Match Success",
        category="positive",
        expected_status=201,
    )
    tc2 = TestCase(
        project_id=project.id,
        endpoint_id=endpoint.id,
        test_id_code="TC-MAT-002",
        name="Create Match Invalid Schema Defect",
        category="negative",
        expected_status=400,
    )
    async_db.add_all([tc1, tc2])
    await async_db.flush()

    # 3. Setup TestRun & Evaluation
    now = utc_now()
    test_run = TestRun(
        project_id=project.id,
        run_uuid="run-html-test-999",
        target_base_url="http://localhost:8000",
        status="completed",
        started_at=now,
        completed_at=now,
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        error_tests=0,
    )
    async_db.add(test_run)
    await async_db.flush()

    evaluation = TestEvaluation(
        run_id=test_run.id,
        structural_validity_rate=100.0,
        contract_compliance_rate=95.0,
        pass_rate=50.0,
        avg_latency_ms=28.4,
        p95_latency_ms=45.2,
    )
    async_db.add(evaluation)

    # 4. Setup TestResults
    res1 = TestResult(
        run_id=test_run.id,
        test_case_id=tc1.id,
        status="passed",
        failure_category="none",
        request_sent_sanitized={"method": "POST", "body": {"team": "Arsenal"}},
        response_status_code=201,
        response_headers_sanitized={"content-type": "application/json"},
        response_body_sanitized={"match_id": "m123", "status": "created"},
        response_time_ms=18.5,
        assertion_evidence=["Status code 201 matches expected 201", "Schema matches definition"],
    )
    res2 = TestResult(
        run_id=test_run.id,
        test_case_id=tc2.id,
        status="failed",
        failure_category="contract_violation",
        request_sent_sanitized={"method": "POST", "body": {"team": ""}},
        response_status_code=500,
        response_headers_sanitized={"content-type": "application/json"},
        response_body_sanitized={"detail": "Unhandled NullPointer in match service"},
        response_time_ms=38.3,
        assertion_evidence=["Status code 500 did not match expected 400"],
        error_message="Unexpected internal server error on empty team name",
    )
    log1 = ExecutionLog(run_id=test_run.id, log_level="INFO", message="Workflow started for /matches")
    log2 = ExecutionLog(run_id=test_run.id, log_level="INFO", message="Executed 2 tests. 1 passed, 1 failed.")
    async_db.add_all([res1, res2, log1, log2])
    await async_db.commit()

    # 5. Generate HTML Report
    html = await ReportService.generate_html_report(
        db=async_db,
        project_id=project.id,
        run_identifier=test_run.id,
    )

    # 6. Verify HTML structure & components
    assert "<!DOCTYPE html>" in html
    assert "DevPilot AI" in html
    assert "EA Sports FC Services" in html
    assert "run-html-test-999" in html
    assert "5-Way Failure Taxonomy Breakdown" in html
    assert "TC-MAT-001" in html
    assert "TC-MAT-002" in html
    assert "Create Match Success" in html
    assert "contract_violation" in html
    assert "Unhandled NullPointer in match service" in html
    assert "Workflow started for /matches" in html
    assert "50.0%" in html or "50%" in html
    assert "28.4" in html  # avg latency


@pytest.mark.asyncio
async def test_report_service_raises_on_nonexistent(async_db: AsyncSession) -> None:
    """Verify ValueError is raised when querying nonexistent project or run."""
    with pytest.raises(ValueError, match="Project 'invalid-proj' not found"):
        await ReportService.generate_html_report(async_db, "invalid-proj", "run-123")
