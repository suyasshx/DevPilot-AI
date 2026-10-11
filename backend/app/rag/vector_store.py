"""
DevPilot AI - Vector Store and Similarity Search Engine.

Supports cosine similarity matching and metadata filtering across stored document chunks.
Compatible with SQLite JSON storage and PostgreSQL pgvector.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.knowledge import DocumentChunk, KnowledgeDocument


@dataclass
class SearchResult:
    """Retrieved chunk with relevance score and provenance metadata."""
    chunk_id: str
    document_id: str
    doc_title: str
    doc_type: str
    chunk_text: str
    relevance_score: float
    endpoint_path: Optional[str] = None
    http_method: Optional[str] = None
    metadata: Dict[str, Any] = None


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Compute cosine similarity between two unit-normalized vectors.
    Since both vectors are normalized, dot product equals cosine similarity.
    """
    if len(vec1) != len(vec2) or not vec1:
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    return max(0.0, min(1.0, float(dot_product)))


class VectorStore:
    """Vector storage and similarity search manager."""

    async def search(
        self,
        db: AsyncSession,
        project_id: str,
        query_vector: List[float],
        top_k: int = 5,
        endpoint_path: Optional[str] = None,
        method: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Execute similarity search against document chunks for the project,
        applying metadata filters and ranking by cosine similarity.
        """
        # Query chunks joined with their parent document
        stmt = (
            select(DocumentChunk, KnowledgeDocument)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.project_id == project_id)
        )

        result = await db.execute(stmt)
        rows = result.all()
        if not rows:
            return []

        scored_results: List[SearchResult] = []
        for chunk, doc in rows:
            # Metadata filtering
            chunk_ep = chunk.metadata_json.get("endpoint")
            chunk_method = chunk.metadata_json.get("method")
            chunk_type = doc.doc_type

            # If doc_type filter requested
            if doc_type and chunk_type != doc_type:
                continue

            # Compute similarity
            score = cosine_similarity(query_vector, chunk.embedding)

            # Relevance boost: if chunk is specifically tied to the target endpoint, boost score
            if endpoint_path and chunk_ep:
                if chunk_ep.lower() == endpoint_path.lower():
                    score = min(1.0, score + 0.15)
                    if method and chunk_method and chunk_method.upper() == method.upper():
                        score = min(1.0, score + 0.10)

            scored_results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    doc_title=doc.title,
                    doc_type=doc.doc_type,
                    chunk_text=chunk.chunk_text,
                    relevance_score=round(score, 4),
                    endpoint_path=chunk_ep,
                    http_method=chunk_method,
                    metadata=chunk.metadata_json,
                )
            )

        # Sort descending by relevance score
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_results[:top_k]


vector_store = VectorStore()
