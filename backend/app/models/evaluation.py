"""
DevPilot AI - Test Quality Evaluation ORM Model.
"""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .execution import TestRun


class TestEvaluation(Base, TimestampMixin):
    """Deterministic quality evaluation and reliability metrics for an execution run."""

    __tablename__ = "test_evaluations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("test_runs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Deterministic Quality Metrics (0.0 to 100.0 %)
    structural_validity_rate: Mapped[float] = mapped_column(Float, default=0.0)
    contract_compliance_rate: Mapped[float] = mapped_column(Float, default=0.0)
    duplicate_test_rate: Mapped[float] = mapped_column(Float, default=0.0)
    documentation_traceability_rate: Mapped[float] = mapped_column(Float, default=0.0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)
    endpoint_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Latency Percentiles (ms)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    p95_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="evaluation")
