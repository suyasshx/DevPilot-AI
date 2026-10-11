"""
DevPilot AI - Retrieval Evaluation Benchmark Tests (Recall@K & MRR).
"""

import os
import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.rag.retriever import RAGRetriever
from app.rag.evaluation import RetrievalEvaluator
from app.services.spec_service import spec_service

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.asyncio
async def test_retrieval_evaluation_benchmark(async_db: AsyncSession) -> None:
    """
    Test retrieval evaluation against labeled benchmark dataset.
    Verifies Recall@1, Recall@3, and Mean Reciprocal Rank (MRR).
    """
    # 1. Create project
    project = await spec_service.create_project(async_db, name="Benchmark Evaluation Project")
    retriever = RAGRetriever()

    # 2. Ingest QA guidelines
    guidelines_dir = os.path.join(WORKSPACE_ROOT, "sample-data", "qa-guidelines")
    for fname in os.listdir(guidelines_dir):
        if fname.endswith(".md"):
            path = os.path.join(guidelines_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            title = fname.replace("_", " ").replace(".md", "").title()
            await retriever.ingest_document(
                db=async_db,
                project_id=project.id,
                title=title,
                doc_type="qa_guideline",
                raw_text=content,
                source_uri=fname,
            )

    # 3. Ingest synthetic bug reports
    bugs_dir = os.path.join(WORKSPACE_ROOT, "sample-data", "bug-reports")
    for fname in os.listdir(bugs_dir):
        if fname.endswith(".json"):
            path = os.path.join(bugs_dir, fname)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            await retriever.ingest_document(
                db=async_db,
                project_id=project.id,
                title=f"Bug: {fname}",
                doc_type="bug_report",
                raw_text=content,
                source_uri=fname,
            )

    # 4. Load benchmark dataset
    benchmark_path = os.path.join(WORKSPACE_ROOT, "sample-data", "evaluation", "retrieval_benchmark.json")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_items = json.load(f)

    # 5. Run evaluation
    evaluator = RetrievalEvaluator(retriever=retriever)
    report = await evaluator.evaluate_benchmark(
        db=async_db,
        project_id=project.id,
        benchmark_items=benchmark_items,
        top_k=5,
    )

    # Assertions on metrics
    assert report.total_queries == len(benchmark_items)
    assert report.recall_at_3 >= 0.80, f"Expected Recall@3 >= 80%, got {report.recall_at_3 * 100}%"
    assert report.recall_at_5 >= 0.80, f"Expected Recall@5 >= 80%, got {report.recall_at_5 * 100}%"
    assert report.mean_reciprocal_rank >= 0.60, f"Expected MRR >= 0.60, got {report.mean_reciprocal_rank}"

    print(f"\n[RAG EVALUATION METRICS] Recall@1: {report.recall_at_1 * 100:.1f}%, Recall@3: {report.recall_at_3 * 100:.1f}%, Recall@5: {report.recall_at_5 * 100:.1f}%, MRR: {report.mean_reciprocal_rank:.4f}")
