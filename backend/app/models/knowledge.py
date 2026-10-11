"""
DevPilot AI - Knowledge Base and Document Chunks ORM Models.
"""

import uuid
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from .project import Project
    from .spec import ApiEndpoint


class KnowledgeDocument(Base, TimestampMixin):
    """Ingested QA guide, synthetic bug report, or business rule."""

    __tablename__ = "knowledge_documents"

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
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="qa_guideline, bug_report, auth_rule, sla_spec",
    )
    source_uri: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="knowledge_documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunk(Base, TimestampMixin):
    """Normalized logical chunk with vector embedding and metadata."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    endpoint_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("api_endpoints.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # Embeddings: list of 384 floats stored as JSON (portable across SQLite & Postgres)
    embedding: Mapped[List[float]] = mapped_column(JSON, nullable=False)

    # Relationships
    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")
    endpoint: Mapped[Optional["ApiEndpoint"]] = relationship("ApiEndpoint", back_populates="document_chunks")
