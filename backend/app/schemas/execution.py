"""
DevPilot AI - Test Execution, Results, Telemetry, and Evaluation Pydantic Schemas.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ExecutionLogResponse(BaseModel):
    """Execution audit log line emitted during a test run."""
    id: str
    run_id: str
    log_level: str
    message: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TestEvaluationResponse(BaseModel):
    """Deterministic quality metrics and latency benchmarks for an execution run."""
    __test__ = False

    id: str
    run_id: str
    structural_validity_rate: float
    contract_compliance_rate: float
    duplicate_test_rate: float
    documentation_traceability_rate: float
    pass_rate: float
    endpoint_coverage_pct: float
    avg_latency_ms: float
    p95_latency_ms: float
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestResultResponse(BaseModel):
    """Granular execution telemetry, assertions, and 5-way failure classification for a single test."""
    __test__ = False

    id: str
    run_id: str
    test_case_id: str
    test_id_code: Optional[str] = None
    test_name: Optional[str] = None
    category: Optional[str] = None
    status: str
    failure_category: str
    request_sent_sanitized: Dict[str, Any] = Field(default_factory=dict)
    response_status_code: Optional[int] = None
    response_headers_sanitized: Dict[str, str] = Field(default_factory=dict)
    response_body_sanitized: Any = Field(default_factory=dict)
    response_time_ms: float = 0.0
    assertion_evidence: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestRunSummaryResponse(BaseModel):
    """High-level summary of a test run for listing and dashboards."""
    __test__ = False

    id: str
    project_id: str
    run_uuid: str
    target_base_url: str
    status: str
    parent_run_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    pass_rate_pct: float = 0.0
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TestRunDetailResponse(TestRunSummaryResponse):
    """Detailed test run including evaluation metrics and recent execution logs."""
    __test__ = False

    evaluation: Optional[TestEvaluationResponse] = None
    recent_logs: List[ExecutionLogResponse] = Field(default_factory=list)


class TestRunRerunRequest(BaseModel):
    """Configuration options for triggering a regression rerun."""
    __test__ = False

    failed_only: bool = Field(
        default=False,
        description="If True, only re-execute tests that failed or caused errors in the source run.",
    )
    target_base_url: Optional[str] = Field(
        default=None,
        description="Optional target base URL override for the rerun session.",
    )
    auth_token_override: Optional[str] = Field(
        default=None,
        description="Optional authorization bearer token override.",
    )


class PaginatedTestRunsResponse(BaseModel):
    """Paginated response for test runs."""
    __test__ = False

    total: int
    items: List[TestRunSummaryResponse]


class PaginatedTestResultsResponse(BaseModel):
    """Paginated response for granular test results."""
    __test__ = False

    total: int
    items: List[TestResultResponse]
