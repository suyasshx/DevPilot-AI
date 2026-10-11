"""
DevPilot AI - Test Execution, Results, and Logs ORM Models.
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin, utc_now

if TYPE_CHECKING:
    from .project import Project
    from .test_case import TestCase
    from .evaluation import TestEvaluation


class TestRun(Base, TimestampMixin):
    """Aggregate execution run session."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    run_uuid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    target_base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="queued",
        index=True,
        comment="queued, running, completed, failed",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Aggregates
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed_tests: Mapped[int] = mapped_column(Integer, default=0)
    failed_tests: Mapped[int] = mapped_column(Integer, default=0)
    error_tests: Mapped[int] = mapped_column(Integer, default=0)
    summary_metrics: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="test_runs")
    results: Mapped[List["TestResult"]] = relationship(
        "TestResult",
        back_populates="test_run",
        cascade="all, delete-orphan",
    )
    evaluation: Mapped[Optional["TestEvaluation"]] = relationship(
        "TestEvaluation",
        back_populates="test_run",
        uselist=False,
        cascade="all, delete-orphan",
    )
    logs: Mapped[List["ExecutionLog"]] = relationship(
        "ExecutionLog",
        back_populates="test_run",
        cascade="all, delete-orphan",
    )


class TestResult(Base, TimestampMixin):
    """Granular execution telemetry and 5-way failure classification for a single test."""

    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    test_case_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        comment="passed, failed, error, skipped",
    )
    failure_category: Mapped[str] = mapped_column(
        String(50),
        default="none",
        index=True,
        comment="none, generation_error, invalid_test, contract_violation, execution_error, infrastructure_failure",
    )

    # Sanitized request and response telemetry
    request_sent_sanitized: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    response_status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers_sanitized: Mapped[Dict[str, str]] = mapped_column(JSON, default=dict)
    response_body_sanitized: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    response_time_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Evidentiary audit logs
    assertion_evidence: Mapped[List[str]] = mapped_column(JSON, default=list)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="results")
    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="test_results")


class ExecutionLog(Base):
    """Log entry during test execution."""

    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    log_level: Mapped[str] = mapped_column(String(10), default="INFO")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="logs")
