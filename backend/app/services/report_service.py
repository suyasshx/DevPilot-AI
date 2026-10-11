"""
DevPilot AI - Offline Interactive HTML Test Report Generation Service.
Renders self-contained, offline-viewable HTML test reports with 5-way taxonomy breakdowns,
latency percentiles, and evidentiary audit payloads using Jinja2.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.execution import TestRun, TestResult, ExecutionLog
from ..models.evaluation import TestEvaluation
from ..models.test_case import TestCase
from ..models.spec import ApiEndpoint
from ..models.project import Project
from ..db.base import utc_now

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _safe_json_dumps(data: Any) -> str:
    """Format json safely for code boxes."""
    try:
        return json.dumps(data, indent=2, default=str)
    except Exception:
        return str(data)


class ReportService:
    """Service generating self-contained, interactive HTML execution reports."""

    @staticmethod
    async def generate_html_report(
        db: AsyncSession,
        project_id: str,
        run_identifier: str,
    ) -> str:
        """
        Extract run telemetry, evaluation metrics, and granular test results from database,
        and render an offline-viewable standalone HTML report.
        """
        # 1. Fetch Project
        project = await db.get(Project, project_id)
        if not project:
            raise ValueError(f"Project '{project_id}' not found.")

        # 2. Fetch TestRun with eager relationships
        run_stmt = (
            select(TestRun)
            .where(TestRun.project_id == project_id)
            .where((TestRun.id == run_identifier) | (TestRun.run_uuid == run_identifier))
            .options(
                selectinload(TestRun.evaluation),
                selectinload(TestRun.logs),
            )
        )
        run = (await db.execute(run_stmt)).scalar_one_or_none()
        if not run:
            raise ValueError(f"Test run '{run_identifier}' not found in project '{project_id}'.")

        # 3. Fetch TestResults joined with TestCase and ApiEndpoint
        results_stmt = (
            select(TestResult, TestCase, ApiEndpoint)
            .join(TestCase, TestResult.test_case_id == TestCase.id)
            .join(ApiEndpoint, TestCase.endpoint_id == ApiEndpoint.id)
            .where(TestResult.run_id == run.id)
            .order_by(TestResult.created_at.asc())
        )
        result_rows = (await db.execute(results_stmt)).all()

        # 4. Compute Metrics & Taxonomies
        total_tests = run.total_tests or len(result_rows)
        passed_tests = run.passed_tests
        pass_rate = round((passed_tests / total_tests * 100.0), 1) if total_tests > 0 else 0.0

        taxonomy_counts: Dict[str, int] = {
            "none": 0,
            "contract_violation": 0,
            "execution_error": 0,
            "invalid_test": 0,
            "generation_error": 0,
            "infrastructure_failure": 0,
        }

        enriched_results: List[Dict[str, Any]] = []
        for res, tc, ep in result_rows:
            cat = res.failure_category or "none"
            taxonomy_counts[cat] = taxonomy_counts.get(cat, 0) + 1

            enriched_results.append({
                "id": res.id,
                "test_id_code": tc.test_id_code,
                "test_name": tc.name,
                "http_method": ep.method,
                "endpoint_path": ep.path,
                "category": tc.category,
                "expected_status": tc.expected_status,
                "response_status_code": res.response_status_code,
                "response_time_ms": res.response_time_ms,
                "failure_category": cat,
                "status": res.status,
                "request_json": _safe_json_dumps(res.request_sent_sanitized),
                "response_json": _safe_json_dumps({
                    "status_code": res.response_status_code,
                    "headers": res.response_headers_sanitized,
                    "body": res.response_body_sanitized,
                }),
                "assertion_evidence": res.assertion_evidence or [],
                "error_message": res.error_message,
            })

        # Calculate taxonomy percentages for visual bar
        tax_pcts: Dict[str, float] = {}
        for k, count in taxonomy_counts.items():
            pct = round((count / total_tests * 100.0), 1) if total_tests > 0 else 0.0
            tax_pcts[k] = pct

        # Duration string
        duration_str = "N/A"
        if run.started_at and run.completed_at:
            dur = max(0.0, (run.completed_at - run.started_at).total_seconds())
            duration_str = f"{dur:.2f}s"

        started_at_str = run.started_at.strftime("%Y-%m-%d %H:%M:%S UTC") if run.started_at else "N/A"
        generated_at_str = utc_now().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Evaluation values
        evaluation = run.evaluation
        avg_latency = evaluation.avg_latency_ms if evaluation else 0.0
        p95_latency = evaluation.p95_latency_ms if evaluation else 0.0
        contract_compliance = evaluation.contract_compliance_rate if evaluation else 100.0
        structural_validity = evaluation.structural_validity_rate if evaluation else 100.0

        # Sort logs
        sorted_logs = sorted(run.logs or [], key=lambda l: l.timestamp or utc_now())
        formatted_logs = [
            {
                "timestamp_str": l.timestamp.strftime("%H:%M:%S") if l.timestamp else "00:00:00",
                "log_level": l.log_level or "INFO",
                "message": l.message,
            }
            for l in sorted_logs
        ]

        # 5. Render Jinja Template
        template = jinja_env.get_template("report_template.html")
        html_content = template.render(
            project=project,
            run=run,
            duration_str=duration_str,
            started_at_str=started_at_str,
            generated_at_str=generated_at_str,
            run_pass_rate=pass_rate,
            avg_latency_ms=f"{avg_latency:.1f}",
            p95_latency_ms=f"{p95_latency:.1f}",
            contract_compliance_rate=f"{contract_compliance:.1f}",
            structural_validity_rate=f"{structural_validity:.1f}",
            taxonomy_counts=taxonomy_counts,
            tax_pcts=tax_pcts,
            results=enriched_results,
            logs=formatted_logs,
        )

        return html_content
