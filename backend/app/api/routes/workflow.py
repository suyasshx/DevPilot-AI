"""
DevPilot AI - Autonomous QA Workflow Routes.
Exposes REST endpoints to trigger multi-step LangGraph test automation DAGs,
monitor execution telemetry, and review 5-way failure taxonomy classifications.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db.session import get_db
from ...models.project import Project
from ...models.spec import ApiEndpoint
from ...models.test_case import TestCase
from ...models.execution import TestRun, TestResult, ExecutionLog
from ...models.evaluation import TestEvaluation
from ...schemas.workflow import WorkflowExecutionRequest, WorkflowExecutionResponse
from ...agent.graph import run_qa_agent_workflow
from ...db.base import utc_now

router = APIRouter(prefix="/projects/{project_id}", tags=["Autonomous QA Workflow"])


@router.post(
    "/workflows/run",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute multi-step LangGraph autonomous QA workflow",
)
async def run_workflow(
    project_id: str,
    request: WorkflowExecutionRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowExecutionResponse:
    """
    Launch end-to-end multi-step LangGraph workflow:
    Discovery -> RAG Grounding -> Test Generation -> Contract Validation -> Self-Repair ->
    Isolated HTTPX Execution -> 5-Way Failure Taxonomy Classification -> Reporting.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    endpoint = await db.get(ApiEndpoint, request.endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Endpoint '{request.endpoint_id}' not found.")

    # Assemble initial state
    initial_state = {
        "project_id": project_id,
        "endpoint_id": request.endpoint_id,
        "target_base_url": request.target_base_url,
        "testing_objective": request.testing_objective,
        "categories": request.categories,
        "auth_token_override": request.auth_token_override,
        "repair_attempts": 0,
        "max_repair_attempts": request.max_repair_attempts,
        "execution_logs": [],
    }

    try:
        final_state = await run_qa_agent_workflow(
            initial_state=initial_state,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph agent workflow failed during execution: {str(exc)}",
        )

    # Persist TestRun and TestResult records in DB
    run_uuid = final_state.get("run_uuid", "run-auto")
    metrics = final_state.get("metrics", {})
    taxonomy = metrics.get("taxonomy_breakdown", {})

    test_run = TestRun(
        project_id=project_id,
        run_uuid=run_uuid,
        target_base_url=request.target_base_url,
        status="completed",
        started_at=utc_now(),
        completed_at=utc_now(),
        total_tests=metrics.get("total_tests", 0),
        passed_tests=metrics.get("passed_tests", 0),
        failed_tests=metrics.get("failed_tests", 0),
        error_tests=metrics.get("error_tests", 0),
        summary_metrics=metrics,
    )
    db.add(test_run)
    await db.flush()

    # Persist Evaluation
    test_eval = TestEvaluation(
        run_id=test_run.id,
        structural_validity_rate=metrics.get("structural_validity_rate", 100.0),
        contract_compliance_rate=metrics.get("contract_compliance_rate", 100.0),
        pass_rate=metrics.get("pass_rate", 0.0),
        avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
        p95_latency_ms=metrics.get("p95_latency_ms", 0.0),
    )
    db.add(test_eval)

    # Persist Execution Logs
    for log_line in final_state.get("execution_logs", []):
        db.add(ExecutionLog(run_id=test_run.id, log_level="INFO", message=log_line))

    await db.commit()

    return WorkflowExecutionResponse(
        run_uuid=run_uuid,
        project_id=project_id,
        endpoint_id=request.endpoint_id,
        workflow_status=final_state.get("workflow_status", "completed"),
        status_message=final_state.get("status_message", "Completed"),
        total_tests_generated=len(final_state.get("raw_generated_tests", [])),
        total_tests_executed=len(final_state.get("execution_results", [])),
        metrics=metrics,
        taxonomy_breakdown=taxonomy,
        execution_logs=final_state.get("execution_logs", []),
        execution_results=final_state.get("execution_results", []),
    )
