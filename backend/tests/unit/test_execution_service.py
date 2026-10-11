"""
DevPilot AI - Unit Tests for ExecutionService and TelemetryBroadcaster.
Verifies run querying, result filtering, rerun engine logic, and SSE telemetry publishing.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.spec import ApiSpecification, ApiEndpoint
from app.models.test_case import TestCase
from app.models.execution import TestRun, TestResult, ExecutionLog
from app.models.evaluation import TestEvaluation
from app.schemas.execution import TestRunRerunRequest
from app.services.execution_service import ExecutionService
from app.services.telemetry_broadcaster import TelemetryBroadcaster
from app.db.base import utc_now


@pytest.mark.asyncio
async def test_telemetry_broadcaster_publish_and_subscribe() -> None:
    """Verify TelemetryBroadcaster queues and formats SSE streams accurately."""
    broadcaster = TelemetryBroadcaster(max_history=50)
    run_id = "test-run-123"

    # 1. Publish initial events
    await broadcaster.publish(run_id, "stage", {"stage": "generation", "status": "in_progress"})
    await broadcaster.publish(run_id, "log", {"message": "Generated 5 tests"})

    # 2. Subscribe and verify history playback
    received_events = []

    async def _collector():
        async for sse_event in broadcaster.subscribe(run_id, initial_history=True, heartbeat_interval=0.5):
            received_events.append(sse_event)
            if "completed" in sse_event:
                break

    task = asyncio.create_task(_collector())

    # Wait briefly and publish completion
    await asyncio.sleep(0.05)
    await broadcaster.publish(run_id, "completed", {"total": 5, "status": "done"})

    await asyncio.wait_for(task, timeout=2.0)

    assert len(received_events) >= 3
    assert any("event: stage" in ev for ev in received_events)
    assert any("event: log" in ev for ev in received_events)
    assert any("event: completed" in ev for ev in received_events)
    assert any("Generated 5 tests" in ev for ev in received_events)


@pytest.mark.asyncio
async def test_execution_service_list_and_detail(async_db: AsyncSession) -> None:
    """Verify listing runs with pagination and fetching detailed run with evaluations."""
    # Setup test project
    project = Project(name="Execution Service Test Project", description="Testing telemetry")
    async_db.add(project)
    await async_db.flush()

    # Create two test runs
    run1 = TestRun(
        project_id=project.id,
        run_uuid="run-001",
        target_base_url="http://localhost:8000",
        status="completed",
        started_at=utc_now(),
        completed_at=utc_now(),
        total_tests=10,
        passed_tests=8,
        failed_tests=2,
        error_tests=0,
        summary_metrics={"pass_rate": 80.0},
    )
    run2 = TestRun(
        project_id=project.id,
        run_uuid="run-002",
        target_base_url="http://localhost:8000",
        status="failed",
        started_at=utc_now(),
        completed_at=utc_now(),
        total_tests=5,
        passed_tests=1,
        failed_tests=4,
        error_tests=0,
        summary_metrics={"pass_rate": 20.0},
    )
    async_db.add_all([run1, run2])
    await async_db.flush()

    # Add evaluation and logs for run1
    eval1 = TestEvaluation(
        run_id=run1.id,
        structural_validity_rate=100.0,
        contract_compliance_rate=95.0,
        pass_rate=80.0,
        avg_latency_ms=42.5,
        p95_latency_ms=68.0,
    )
    log1 = ExecutionLog(run_id=run1.id, log_level="INFO", message="Run 1 completed successfully.")
    async_db.add_all([eval1, log1])
    await async_db.commit()

    # 1. Test list_runs
    list_resp = await ExecutionService.list_runs(async_db, project.id, skip=0, limit=10)
    assert list_resp.total == 2
    assert len(list_resp.items) == 2

    # 2. Test status filter
    failed_only = await ExecutionService.list_runs(async_db, project.id, status_filter="failed")
    assert failed_only.total == 1
    assert failed_only.items[0].run_uuid == "run-002"

    # 3. Test get_run_detail by ID
    detail_by_id = await ExecutionService.get_run_detail(async_db, project.id, run1.id)
    assert detail_by_id is not None
    assert detail_by_id.run_uuid == "run-001"
    assert detail_by_id.pass_rate_pct == 80.0
    assert detail_by_id.evaluation is not None
    assert detail_by_id.evaluation.contract_compliance_rate == 95.0
    assert len(detail_by_id.recent_logs) == 1
    assert detail_by_id.recent_logs[0].message == "Run 1 completed successfully."

    # 4. Test get_run_detail by run_uuid
    detail_by_uuid = await ExecutionService.get_run_detail(async_db, project.id, "run-002")
    assert detail_by_uuid is not None
    assert detail_by_uuid.id == run2.id
    assert detail_by_uuid.status == "failed"


@pytest.mark.asyncio
async def test_execution_service_results_query(async_db: AsyncSession) -> None:
    """Verify granular test results listing, filtering by taxonomy, and single result inspection."""
    project = Project(name="Results Query Project")
    async_db.add(project)
    await async_db.flush()

    spec = ApiSpecification(project_id=project.id, title="Test Spec", version="1.0.0", spec_type="openapi_json")
    async_db.add(spec)
    await async_db.flush()

    endpoint = ApiEndpoint(
        spec_id=spec.id,
        path="/items",
        http_method="GET",
        summary="Get items",
        request_schema={},
        response_schema={},
    )
    async_db.add(endpoint)
    await async_db.flush()

    tc1 = TestCase(
        project_id=project.id,
        endpoint_id=endpoint.id,
        test_id_code="TC-ITM-001",
        name="Get Items Success",
        category="positive",
        expected_status=200,
    )
    tc2 = TestCase(
        project_id=project.id,
        endpoint_id=endpoint.id,
        test_id_code="TC-ITM-002",
        name="Get Items Contract Violation",
        category="negative",
        expected_status=400,
    )
    async_db.add_all([tc1, tc2])
    await async_db.flush()

    test_run = TestRun(
        project_id=project.id,
        run_uuid="run-results-test",
        target_base_url="http://localhost:8000",
        status="completed",
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
    )
    async_db.add(test_run)
    await async_db.flush()

    res1 = TestResult(
        run_id=test_run.id,
        test_case_id=tc1.id,
        status="passed",
        failure_category="none",
        response_status_code=200,
        response_time_ms=15.0,
        assertion_evidence=["Status code 200 matches expected 200"],
    )
    res2 = TestResult(
        run_id=test_run.id,
        test_case_id=tc2.id,
        status="failed",
        failure_category="contract_violation",
        response_status_code=500,
        response_time_ms=25.0,
        assertion_evidence=["Status code 500 does not match expected 400"],
        error_message="Unexpected internal server error on bad input",
    )
    async_db.add_all([res1, res2])
    await async_db.commit()

    # 1. List all results
    all_results = await ExecutionService.list_run_results(async_db, test_run.id)
    assert all_results.total == 2
    assert len(all_results.items) == 2

    # 2. Filter by status == 'failed'
    failed_results = await ExecutionService.list_run_results(async_db, test_run.id, status_filter="failed")
    assert failed_results.total == 1
    assert failed_results.items[0].test_id_code == "TC-ITM-002"
    assert failed_results.items[0].failure_category == "contract_violation"

    # 3. Filter by taxonomy == 'contract_violation'
    cv_results = await ExecutionService.list_run_results(
        async_db, test_run.id, failure_category_filter="contract_violation"
    )
    assert cv_results.total == 1
    assert cv_results.items[0].test_id_code == "TC-ITM-002"

    # 4. Get single result detail
    single_res = await ExecutionService.get_result_detail(async_db, res2.id)
    assert single_res is not None
    assert single_res.test_name == "Get Items Contract Violation"
    assert single_res.error_message == "Unexpected internal server error on bad input"
