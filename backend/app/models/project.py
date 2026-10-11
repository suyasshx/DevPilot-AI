"""
DevPilot AI - Project ORM Model.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .spec import ApiSpecification
    from .test_case import TestCase
    from .execution import TestRun
    from .knowledge import KnowledgeDocument


class Project(Base, TimestampMixin):
    """Project grouping specifications, test cases, and execution runs."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    specifications: Mapped[List["ApiSpecification"]] = relationship(
        "ApiSpecification",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    test_runs: Mapped[List["TestRun"]] = relationship(
        "TestRun",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    knowledge_documents: Mapped[List["KnowledgeDocument"]] = relationship(
        "KnowledgeDocument",
        back_populates="project",
        cascade="all, delete-orphan",
    )
