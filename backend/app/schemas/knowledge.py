"""
DevPilot AI - Knowledge Base and RAG Schemas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class KnowledgeDocumentResponse(BaseModel):
    id: str
    project_id: str
    title: str
    doc_type: str
    source_uri: Optional[str] = None
    chunks_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class SearchChunkItem(BaseModel):
    chunk_id: str
    doc_title: str
    doc_type: str
    relevance_score: float
    chunk_text: str
    endpoint_path: Optional[str] = None
    http_method: Optional[str] = None


class SearchQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, examples=["negative item quantity"])
    endpoint_path: Optional[str] = Field(default=None, examples=["/orders"])
    method: Optional[str] = Field(default=None, examples=["POST"])
    top_k: int = Field(default=5, ge=1, le=20)


class SearchQueryResponse(BaseModel):
    query: str
    total_found: int
    results: List[SearchChunkItem]
    bounded_context_preview: str


class EvaluationReportResponse(BaseModel):
    total_queries: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mean_reciprocal_rank: float
    details: List[Dict[str, Any]]
