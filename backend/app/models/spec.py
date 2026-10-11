"""
DevPilot AI - OpenAPI Specification and Endpoint ORM Models.
"""

import uuid
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project
    from .test_case import TestCase
    from .knowledge import DocumentChunk


class ApiSpecification(Base, TimestampMixin):
    """Raw and parsed OpenAPI specification record."""

    __tablename__ = "api_specifications"

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
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    spec_format: Mapped[str] = mapped_column(String(10), default="json")
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="specifications")
    endpoints: Mapped[List["ApiEndpoint"]] = relationship(
        "ApiEndpoint",
        back_populates="specification",
        cascade="all, delete-orphan",
    )


class ApiEndpoint(Base, TimestampMixin):
    """Granular endpoint and schema constraints extracted from OpenAPI specification."""

    __tablename__ = "api_endpoints"
    __table_args__ = (
        UniqueConstraint("spec_id", "path", "method", name="uq_endpoint_spec_path_method"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    spec_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("api_specifications.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured contract definitions stored as JSON
    parameters_schema: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    request_body_schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    responses_schema: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[List[str]] = mapped_column(JSON, default=list)

    # Relationships
    specification: Mapped["ApiSpecification"] = relationship("ApiSpecification", back_populates="endpoints")
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )
    document_chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="endpoint",
        cascade="all, delete-orphan",
    )
