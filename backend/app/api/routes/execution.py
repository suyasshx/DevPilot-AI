"""
DevPilot AI - Test Runs and Execution Telemetry API Routes.
Provides endpoints for querying past execution sessions, inspecting granular test results,
triggering regression reruns, and streaming live execution telemetry via Server-Sent Events (SSE).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_db
from ...models.project import Project
from ...schemas.execution import (
    PaginatedTestRunsResponse,
    TestRunDetailResponse,
    PaginatedTestResultsResponse,
    TestResultResponse,
    TestRunRerunRequest,
)
from ...services.execution_service import ExecutionService
from ...services.telemetry_broadcaster import telemetry_broadcaster

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["Test Execution & Telemetry"])


async def _verify_project(project_id: str, db: AsyncSession) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return project


@router.get(
    "",
    response_model=PaginatedTestRunsResponse,
    status_code=status.HTTP_200_OK,
    summary="List past test execution runs",
)
async def list_test_runs(
    project_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status: queued, running, completed, failed"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTestRunsResponse:
    """Retrieve paginated test execution runs for a project with duration and pass rate aggregates."""
    await _verify_project(project_id, db)
    return await ExecutionService.list_runs(
        db=db,
        project_id=project_id,
        skip=skip,
        limit=limit,
        status_filter=status,
    )


@router.get(
    "/{run_id}",
    response_model=TestRunDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed test run metrics and audit logs",
)
async def get_test_run(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> TestRunDetailResponse:
    """Fetch complete telemetry for a single test run by database UUID or human-readable run_uuid."""
    await _verify_project(project_id, db)
    run_detail = await ExecutionService.get_run_detail(
        db=db,
        project_id=project_id,
        run_identifier=run_id,
    )
    if not run_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run '{run_id}' not found in project '{project_id}'.",
        )
    return run_detail


@router.get(
    "/{run_id}/results",
    response_model=PaginatedTestResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="List individual test case execution outcomes for a run",
)
async def list_run_test_results(
    project_id: str,
    run_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    status: Optional[str] = Query(None, description="Filter by status: passed, failed, error, skipped"),
    failure_category: Optional[str] = Query(
        None,
        description="Filter by 5-way taxonomy: none, generation_error, invalid_test, contract_violation, execution_error, infrastructure_failure",
    ),
    db: AsyncSession = Depends(get_db),
) -> PaginatedTestResultsResponse:
    """Fetch granular test case results with sanitized payloads, latency, and failure classifications."""
    await _verify_project(project_id, db)
    return await ExecutionService.list_run_results(
        db=db,
        run_id=run_id,
        skip=skip,
        limit=limit,
        status_filter=status,
        failure_category_filter=failure_category,
    )


@router.get(
    "/{run_id}/results/{result_id}",
    response_model=TestResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed evidentiary inspection for a single test execution",
)
async def get_test_result(
    project_id: str,
    run_id: str,
    result_id: str,
    db: AsyncSession = Depends(get_db),
) -> TestResultResponse:
    """Retrieve full evidentiary audit telemetry and assertion failure details for a single test."""
    await _verify_project(project_id, db)
    result = await ExecutionService.get_result_detail(db=db, result_id=result_id)
    if not result or (result.run_id != run_id and run_id not in (result.run_id,)):
        # Check if run_id matched run_uuid
        run_detail = await ExecutionService.get_run_detail(db, project_id, run_id)
        if not run_detail or result.run_id != run_detail.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Test result '{result_id}' not found for run '{run_id}'.",
            )
    return result


@router.post(
    "/{run_id}/rerun",
    response_model=TestRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute regression rerun for a test run",
)
async def rerun_test_run(
    project_id: str,
    run_id: str,
    request: TestRunRerunRequest,
    db: AsyncSession = Depends(get_db),
) -> TestRunDetailResponse:
    """
    Rerun tests from a prior execution session.
    When failed_only is True, selectively re-executes tests that failed or produced errors,
    producing a new tracked TestRun with parent lineage.
    """
    await _verify_project(project_id, db)
    try:
        new_run = await ExecutionService.rerun_run(
            db=db,
            project_id=project_id,
            run_identifier=run_id,
            request=request,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute rerun: {str(exc)}",
        )

    # Return detail of the newly created rerun
    rerun_detail = await ExecutionService.get_run_detail(db=db, project_id=project_id, run_identifier=new_run.id)
    return rerun_detail


@router.get(
    "/{run_id}/stream",
    summary="Stream live telemetry and execution logs via Server-Sent Events (SSE)",
)
async def stream_run_telemetry(
    project_id: str,
    run_id: str,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Subscribes to live Server-Sent Events (SSE) for an active or completed test run.
    Yields historical log buffers followed by real-time execution logs, progress, and done events.
    """
    await _verify_project(project_id, db)
    run_detail = await ExecutionService.get_run_detail(db, project_id, run_id)
    if not run_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run '{run_id}' not found.",
        )

    # Stream from broadcaster using the run's id or run_uuid
    stream_generator = telemetry_broadcaster.subscribe(run_id=run_detail.id)

    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
