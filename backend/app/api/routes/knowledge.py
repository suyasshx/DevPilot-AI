"""
DevPilot AI - Knowledge Base & RAG Retrieval API Routes.
"""

import json
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...db.session import get_db
from ...models.project import Project
from ...models.knowledge import KnowledgeDocument, DocumentChunk
from ..dependencies import get_project_or_404
from ...schemas.knowledge import (
    KnowledgeDocumentResponse,
    SearchQueryRequest,
    SearchQueryResponse,
    SearchChunkItem,
    EvaluationReportResponse,
)
from ...rag.retriever import rag_retriever
from ...rag.evaluation import retrieval_evaluator

router = APIRouter(prefix="/projects/{project_id}", tags=["Knowledge Base & RAG"])


@router.post(
    "/knowledge/upload",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload QA guideline or synthetic bug report",
)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    doc_type: str = Form(..., description="Document type: 'qa_guideline', 'bug_report', 'auth_rule'"),
    title: Optional[str] = Form(None, description="Optional custom title for document"),
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeDocumentResponse:
    """
    Ingest a QA guideline (Markdown) or synthetic bug report (JSON).
    Normalizes text, chunks content, generates embeddings, and indexes in vector database.
    """
    content_bytes = await file.read()
    raw_text = content_bytes.decode("utf-8")
    doc_title = title or file.filename or "Untitled Document"

    doc = await rag_retriever.ingest_document(
        db=db,
        project_id=project.id,
        title=doc_title,
        doc_type=doc_type,
        raw_text=raw_text,
        source_uri=file.filename,
    )

    # Count generated chunks
    result = await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc.id)
    )
    count = result.scalar() or 0

    return KnowledgeDocumentResponse(
        id=doc.id,
        project_id=doc.project_id,
        title=doc.title,
        doc_type=doc.doc_type,
        source_uri=doc.source_uri,
        chunks_count=count,
        created_at=doc.created_at,
    )


@router.get(
    "/knowledge",
    response_model=List[KnowledgeDocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List all ingested knowledge documents",
)
async def list_knowledge_documents(
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeDocumentResponse]:
    """Retrieve all ingested documents with their chunk counts for a project."""
    stmt = (
        select(KnowledgeDocument, func.count(DocumentChunk.id).label("chunk_count"))
        .outerjoin(DocumentChunk, KnowledgeDocument.id == DocumentChunk.document_id)
        .where(KnowledgeDocument.project_id == project.id)
        .group_by(KnowledgeDocument.id)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    result = await db.execute(stmt)
    responses = []
    for doc, count in result.all():
        responses.append(
            KnowledgeDocumentResponse(
                id=doc.id,
                project_id=doc.project_id,
                title=doc.title,
                doc_type=doc.doc_type,
                source_uri=doc.source_uri,
                chunks_count=count,
                created_at=doc.created_at,
            )
        )
    return responses


@router.post(
    "/knowledge/search",
    response_model=SearchQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Search RAG vector knowledge base",
)
async def search_knowledge(
    payload: SearchQueryRequest,
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> SearchQueryResponse:
    """
    Query vector database with semantic search and metadata filtering.
    Returns matched chunks with relevance scores and bounded context preview.
    """
    context = await rag_retriever.retrieve_context(
        db=db,
        project_id=project.id,
        endpoint_path=payload.endpoint_path or "",
        method=payload.method or "GET",
        testing_objective=payload.query,
        top_k=payload.top_k,
    )

    items = [
        SearchChunkItem(
            chunk_id=r.chunk_id,
            doc_title=r.doc_title,
            doc_type=r.doc_type,
            relevance_score=r.relevance_score,
            chunk_text=r.chunk_text,
            endpoint_path=r.endpoint_path,
            http_method=r.http_method,
        )
        for r in context.retrieved_chunks
    ]

    return SearchQueryResponse(
        query=payload.query,
        total_found=len(items),
        results=items,
        bounded_context_preview=context.prompt_context,
    )


@router.post(
    "/rag/evaluate",
    response_model=EvaluationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Run retrieval benchmark evaluation (Recall@K, MRR)",
)
async def evaluate_rag_retrieval(
    benchmark_file: Optional[UploadFile] = File(None),
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> EvaluationReportResponse:
    """
    Evaluate retrieval precision and recall metrics (Recall@1, Recall@3, Recall@5, MRR)
    against a benchmark query set.
    """
    if benchmark_file:
        content = await benchmark_file.read()
        benchmark_items = json.loads(content.decode("utf-8"))
    else:
        # Default built-in benchmark
        from pathlib import Path
        benchmark_path = Path("sample-data/evaluation/retrieval_benchmark.json")
        if benchmark_path.exists():
            benchmark_items = json.loads(benchmark_path.read_text(encoding="utf-8"))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No benchmark file provided and sample benchmark not found.",
            )

    report = await retrieval_evaluator.evaluate_benchmark(
        db=db,
        project_id=project.id,
        benchmark_items=benchmark_items,
    )

    details = [
        {
            "query": q.query,
            "endpoint": q.endpoint,
            "hit_at_1": q.hit_at_1,
            "hit_at_3": q.hit_at_3,
            "hit_at_5": q.hit_at_5,
            "reciprocal_rank": q.reciprocal_rank,
            "retrieved_titles": q.retrieved_chunk_titles,
        }
        for q in report.query_details
    ]

    return EvaluationReportResponse(
        total_queries=report.total_queries,
        recall_at_1=report.recall_at_1,
        recall_at_3=report.recall_at_3,
        recall_at_5=report.recall_at_5,
        mean_reciprocal_rank=report.mean_reciprocal_rank,
        details=details,
    )
