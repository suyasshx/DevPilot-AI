"""
DevPilot AI - Test Execution and Regression Rerun Service.
Manages querying test run telemetry, results inspection, and deterministic regression reruns.
"""

import uuid
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from ..models.execution import TestRun, TestResult, ExecutionLog
from ..models.evaluation import TestEvaluation
from ..models.test_case import TestCase
from ..models.spec import ApiEndpoint
from ..schemas.test_case import GeneratedTestCaseItem
from ..schemas.execution import (
    TestRunSummaryResponse,
    TestRunDetailResponse,
    TestResultResponse,
    ExecutionLogResponse,
    TestEvaluationResponse,
    TestRunRerunRequest,
    PaginatedTestRunsResponse,
    PaginatedTestResultsResponse,
)
from ..agent.executor import TestHarnessExecutor, ExecutionResultItem
from ..agent.classifier import FailureTaxonomyClassifier, FailureClassification
from ..services.telemetry_broadcaster import telemetry_broadcaster
from ..db.base import utc_now


def _calc_duration(started_at: Optional[datetime], completed_at: Optional[datetime]) -> Optional[float]:
    if started_at and completed_at:
        return max(0.0, (completed_at - started_at).total_seconds())
    return None


def _calc_pass_rate(total: int, passed: int) -> float:
    if total <= 0:
        return 0.0
    return round((passed / total) * 100.0, 2)


class ExecutionService:
    """Service handling test runs query, detailed inspection, and regression reruns."""

    @staticmethod
    async def list_runs(
        db: AsyncSession,
        project_id: str,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
    ) -> PaginatedTestRunsResponse:
        """List test runs for a project with optional status filter."""
        stmt = select(TestRun).where(TestRun.project_id == project_id)
        if status_filter:
            stmt = stmt.where(TestRun.status == status_filter)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = stmt.order_by(desc(TestRun.created_at)).offset(skip).limit(limit)
        runs = (await db.execute(stmt)).scalars().all()

        items = [
            TestRunSummaryResponse(
                id=r.id,
                project_id=r.project_id,
                run_uuid=r.run_uuid,
                target_base_url=r.target_base_url,
                status=r.status,
                parent_run_id=r.parent_run_id,
                started_at=r.started_at,
                completed_at=r.completed_at,
                duration_seconds=_calc_duration(r.started_at, r.completed_at),
                total_tests=r.total_tests,
                passed_tests=r.passed_tests,
                failed_tests=r.failed_tests,
                error_tests=r.error_tests,
                pass_rate_pct=_calc_pass_rate(r.total_tests, r.passed_tests),
                summary_metrics=r.summary_metrics or {},
                created_at=r.created_at,
            )
            for r in runs
        ]

        return PaginatedTestRunsResponse(total=total, items=items)

    @staticmethod
    async def get_run_detail(
        db: AsyncSession,
        project_id: str,
        run_identifier: str,
    ) -> Optional[TestRunDetailResponse]:
        """Fetch test run by DB UUID or run_uuid, loading evaluation and logs."""
        stmt = (
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .where((TestRun.id == run_identifier) | (TestRun.run_uuid == run_identifier))
            .options(
                selectinload(TestRun.evaluation),
                selectinload(TestRun.logs),
            )
        )
        run = (await db.execute(stmt)).scalar_one_or_none()
        if not run:
            return None

        eval_resp = None
        if run.evaluation:
            eval_resp = TestEvaluationResponse.model_validate(run.evaluation)

        # Sort logs by timestamp ascending
        sorted_logs = sorted(run.logs or [], key=lambda l: l.timestamp or utc_now())
        log_responses = [
            ExecutionLogResponse.model_validate(l) for l in sorted_logs[-100:]
        ]

        return TestRunDetailResponse(
            id=run.id,
            project_id=run.project_id,
            run_uuid=run.run_uuid,
            target_base_url=run.target_base_url,
            status=run.status,
            parent_run_id=run.parent_run_id,
            started_at=run.started_at,
            completed_at=run.completed_at,
            duration_seconds=_calc_duration(run.started_at, run.completed_at),
            total_tests=run.total_tests,
            passed_tests=run.passed_tests,
            failed_tests=run.failed_tests,
            error_tests=run.error_tests,
            pass_rate_pct=_calc_pass_rate(run.total_tests, run.passed_tests),
            summary_metrics=run.summary_metrics or {},
            created_at=run.created_at,
            evaluation=eval_resp,
            recent_logs=log_responses,
        )

    @staticmethod
    async def list_run_results(
        db: AsyncSession,
        run_id: str,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
        failure_category_filter: Optional[str] = None,
    ) -> PaginatedTestResultsResponse:
        """List individual test results for a run, joined with TestCase metadata."""
        # Find run to support lookup by run_uuid or id
        run_stmt = select(TestRun.id).where((TestRun.id == run_id) | (TestRun.run_uuid == run_id))
        resolved_run_id = (await db.execute(run_stmt)).scalar_one_or_none()
        if not resolved_run_id:
            return PaginatedTestResultsResponse(total=0, items=[])

        stmt = (
            select(TestResult, TestCase)
            .join(TestCase, TestResult.test_case_id == TestCase.id)
            .where(TestResult.run_id == resolved_run_id)
        )
        if status_filter:
            stmt = stmt.where(TestResult.status == status_filter)
        if failure_category_filter:
            stmt = stmt.where(TestResult.failure_category == failure_category_filter)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(TestResult.created_at.asc()).offset(skip).limit(limit)
        rows = (await db.execute(stmt)).all()

        items = []
        for result, test_case in rows:
            items.append(
                TestResultResponse(
                    id=result.id,
                    run_id=result.run_id,
                    test_case_id=result.test_case_id,
                    test_id_code=test_case.test_id_code,
                    test_name=test_case.name,
                    category=test_case.category,
                    status=result.status,
                    failure_category=result.failure_category,
                    request_sent_sanitized=result.request_sent_sanitized or {},
                    response_status_code=result.response_status_code,
                    response_headers_sanitized=result.response_headers_sanitized or {},
                    response_body_sanitized=result.response_body_sanitized or {},
                    response_time_ms=result.response_time_ms,
                    assertion_evidence=result.assertion_evidence or [],
                    error_message=result.error_message,
                    created_at=result.created_at,
                )
            )

        return PaginatedTestResultsResponse(total=total, items=items)

    @staticmethod
    async def get_result_detail(
        db: AsyncSession,
        result_id: str,
    ) -> Optional[TestResultResponse]:
        """Fetch a single TestResult with its linked TestCase metadata."""
        stmt = (
            select(TestResult, TestCase)
            .join(TestCase, TestResult.test_case_id == TestCase.id)
            .where(TestResult.id == result_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return None

        result, test_case = row
        return TestResultResponse(
            id=result.id,
            run_id=result.run_id,
            test_case_id=result.test_case_id,
            test_id_code=test_case.test_id_code,
            test_name=test_case.name,
            category=test_case.category,
            status=result.status,
            failure_category=result.failure_category,
            request_sent_sanitized=result.request_sent_sanitized or {},
            response_status_code=result.response_status_code,
            response_headers_sanitized=result.response_headers_sanitized or {},
            response_body_sanitized=result.response_body_sanitized or {},
            response_time_ms=result.response_time_ms,
            assertion_evidence=result.assertion_evidence or [],
            error_message=result.error_message,
            created_at=result.created_at,
        )

    @staticmethod
    async def rerun_run(
        db: AsyncSession,
        project_id: str,
        run_identifier: str,
        request: TestRunRerunRequest,
    ) -> TestRun:
        """
        Execute regression rerun of a previous test run.
        Optionally filters for only failed tests.
        """
        # Resolve source run
        run_stmt = (
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .where((TestRun.id == run_identifier) | (TestRun.run_uuid == run_identifier))
        )
        source_run = (await db.execute(run_stmt)).scalar_one_or_none()
        if not source_run:
            raise ValueError(f"Source test run '{run_identifier}' not found in project '{project_id}'.")

        # Load previous results joined with TestCase and ApiEndpoint
        results_stmt = (
            select(TestResult, TestCase, ApiEndpoint)
            .join(TestCase, TestResult.test_case_id == TestCase.id)
            .join(ApiEndpoint, TestCase.endpoint_id == ApiEndpoint.id)
            .where(TestResult.run_id == source_run.id)
        )
        if request.failed_only:
            results_stmt = results_stmt.where(TestResult.status != "passed")

        rows = (await db.execute(results_stmt)).all()
        if not rows:
            if request.failed_only:
                raise ValueError("No failed tests found to rerun in this test run.")
            raise ValueError("No test cases found in this test run to rerun.")

        target_base_url = request.target_base_url or source_run.target_base_url
        new_run_uuid = f"rerun-{uuid.uuid4().hex[:12]}"
        now = utc_now()

        # Create new TestRun record
        new_run = TestRun(
            project_id=project_id,
            parent_run_id=source_run.id,
            run_uuid=new_run_uuid,
            target_base_url=target_base_url,
            status="running",
            started_at=now,
        )
        db.add(new_run)
        await db.flush()

        logs: List[str] = [
            f"[RERUN] Initialized regression rerun '{new_run_uuid}' based on parent run '{source_run.run_uuid}'.",
            f"[RERUN] Target base URL: {target_base_url}. Re-executing {len(rows)} test cases (failed_only={request.failed_only}).",
        ]
        for l in logs:
            await telemetry_broadcaster.publish(new_run.id, "log", {"message": l})
            await telemetry_broadcaster.publish(new_run_uuid, "log", {"message": l})

        executor = TestHarnessExecutor(base_url=target_base_url)
        latencies: List[float] = []
        passed_count = 0
        failed_count = 0
        error_count = 0

        taxonomy_counts: Dict[str, int] = {
            "none": 0,
            "generation_error": 0,
            "invalid_test": 0,
            "contract_violation": 0,
            "execution_error": 0,
            "infrastructure_failure": 0,
        }

        # Execute tests sequentially
        for prev_result, test_case, endpoint in rows:
            tc_item = GeneratedTestCaseItem(
                test_id_code=test_case.test_id_code,
                name=test_case.name,
                description=test_case.description or "",
                category=test_case.category,
                priority=test_case.priority,
                request_headers=test_case.request_headers or {},
                path_params=test_case.path_params or {},
                query_params=test_case.query_params or {},
                request_body=test_case.request_body or {},
                expected_status=test_case.expected_status,
                expected_response_checks=test_case.expected_response_checks or {},
                source_references=test_case.source_references or [],
                requires_review=test_case.requires_review,
            )

            res: ExecutionResultItem = await executor.execute_test(
                endpoint_path=endpoint.path,
                http_method=endpoint.http_method,
                test_case=tc_item,
                auth_token_override=request.auth_token_override,
            )

            latencies.append(res.response_time_ms)

            # Classify
            if res.is_passed:
                cat_name = "none"
                status_str = "passed"
                passed_count += 1
            else:
                verdict: FailureClassification = FailureTaxonomyClassifier.classify(
                    expected_status=res.expected_status,
                    actual_status=res.actual_status,
                    response_body=res.response_body,
                    error_type=res.error_type,
                    error_message=res.error_message,
                )
                cat_name = verdict.category
                if cat_name in ("execution_error", "infrastructure_failure"):
                    status_str = "error"
                    error_count += 1
                else:
                    status_str = "failed"
                    failed_count += 1

            taxonomy_counts[cat_name] = taxonomy_counts.get(cat_name, 0) + 1

            # Save TestResult
            sanitized_body = res.response_body if isinstance(res.response_body, (dict, list)) else {"raw": res.response_body}
            new_result = TestResult(
                run_id=new_run.id,
                test_case_id=test_case.id,
                status=status_str,
                failure_category=cat_name,
                request_sent_sanitized=res.request_sent or {},
                response_status_code=res.actual_status,
                response_headers_sanitized=res.response_headers or {},
                response_body_sanitized=sanitized_body,
                response_time_ms=res.response_time_ms,
                assertion_evidence=res.assertion_evidence or [],
                error_message=res.error_message,
            )
            db.add(new_result)

            log_msg = f"[RERUN] {test_case.test_id_code} -> {status_str.upper()} ({res.response_time_ms:.1f}ms, taxonomy: {cat_name})"
            logs.append(log_msg)
            await telemetry_broadcaster.publish(new_run.id, "log", {"message": log_msg})
            await telemetry_broadcaster.publish(new_run_uuid, "log", {"message": log_msg})

        # Calculate metrics
        total_tests = len(rows)
        pass_rate = round((passed_count / total_tests) * 100.0, 2) if total_tests > 0 else 0.0
        avg_latency = float(np.mean(latencies)) if latencies else 0.0
        p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0

        metrics = {
            "total_tests": total_tests,
            "passed_tests": passed_count,
            "failed_tests": failed_count,
            "error_tests": error_count,
            "pass_rate": pass_rate,
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "taxonomy_breakdown": taxonomy_counts,
        }

        # Update new_run
        completed_time = utc_now()
        new_run.status = "completed"
        new_run.completed_at = completed_time
        new_run.total_tests = total_tests
        new_run.passed_tests = passed_count
        new_run.failed_tests = failed_count
        new_run.error_tests = error_count
        new_run.summary_metrics = metrics

        # Evaluation
        new_eval = TestEvaluation(
            run_id=new_run.id,
            structural_validity_rate=100.0,
            contract_compliance_rate=100.0,
            pass_rate=pass_rate,
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
        )
        db.add(new_eval)

        # Execution Logs
        for msg in logs:
            db.add(ExecutionLog(run_id=new_run.id, log_level="INFO", message=msg))

        await db.commit()
        await db.refresh(new_run)

        # Broadcast completion
        await telemetry_broadcaster.publish(new_run.id, "completed", {"run_uuid": new_run_uuid, "metrics": metrics})
        await telemetry_broadcaster.publish(new_run_uuid, "completed", {"run_uuid": new_run_uuid, "metrics": metrics})

        return new_run
