"""
DevPilot AI - Retrieval Evaluation Metrics Engine.

Computes Recall@K (Recall@1, Recall@3, Recall@5) and Mean Reciprocal Rank (MRR)
against labeled benchmark datasets to evaluate RAG retrieval performance.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from .retriever import RAGRetriever, rag_retriever


@dataclass
class QueryEvaluationResult:
    """Evaluation metrics for a single benchmark query."""
    query: str
    endpoint: str
    method: str
    expected_target_ids: List[str]
    retrieved_chunk_titles: List[str]
    hit_at_1: bool
    hit_at_3: bool
    hit_at_5: bool
    reciprocal_rank: float


@dataclass
class BenchmarkReport:
    """Aggregate benchmark evaluation report."""
    total_queries: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mean_reciprocal_rank: float
    query_details: List[QueryEvaluationResult]


class RetrievalEvaluator:
    """Computes Recall@K and MRR for RAG retrieval."""

    def __init__(self, retriever: Optional[RAGRetriever] = None) -> None:
        self.retriever = retriever or rag_retriever

    async def evaluate_benchmark(
        self,
        db: AsyncSession,
        project_id: str,
        benchmark_items: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> BenchmarkReport:
        """
        Evaluate a list of benchmark queries against the project's vector store.
        Each item must contain: query, endpoint, method, expected_target_ids.
        """
        if not benchmark_items:
            return BenchmarkReport(0, 0.0, 0.0, 0.0, 0.0, [])

        query_results: List[QueryEvaluationResult] = []

        for item in benchmark_items:
            query = item["query"]
            endpoint = item.get("endpoint", "")
            method = item.get("method", "GET")
            expected_targets = [t.lower() for t in item.get("expected_target_ids", [])]

            # Execute retrieval
            context = await self.retriever.retrieve_context(
                db=db,
                project_id=project_id,
                endpoint_path=endpoint,
                method=method,
                testing_objective=query,
                top_k=top_k,
            )

            retrieved_titles = [c.doc_title for c in context.retrieved_chunks]

            # Find rank of first relevant target
            first_hit_rank = 0
            for rank_idx, chunk in enumerate(context.retrieved_chunks, start=1):
                chunk_ident = (
                    f"{chunk.doc_title} {chunk.metadata.get('bug_id', '')} {chunk.chunk_id} {chunk.chunk_text}"
                ).lower()

                if any(target in chunk_ident for target in expected_targets):
                    first_hit_rank = rank_idx
                    break

            hit_1 = (first_hit_rank == 1)
            hit_3 = (0 < first_hit_rank <= 3)
            hit_5 = (0 < first_hit_rank <= 5)
            rr = (1.0 / first_hit_rank) if first_hit_rank > 0 else 0.0

            query_results.append(
                QueryEvaluationResult(
                    query=query,
                    endpoint=endpoint,
                    method=method,
                    expected_target_ids=expected_targets,
                    retrieved_chunk_titles=retrieved_titles,
                    hit_at_1=hit_1,
                    hit_at_3=hit_3,
                    hit_at_5=hit_5,
                    reciprocal_rank=rr,
                )
            )

        total = len(query_results)
        recall_1 = round(sum(1 for q in query_results if q.hit_at_1) / total, 4)
        recall_3 = round(sum(1 for q in query_results if q.hit_at_3) / total, 4)
        recall_5 = round(sum(1 for q in query_results if q.hit_at_5) / total, 4)
        mrr = round(sum(q.reciprocal_rank for q in query_results) / total, 4)

        return BenchmarkReport(
            total_queries=total,
            recall_at_1=recall_1,
            recall_at_3=recall_3,
            recall_at_5=recall_5,
            mean_reciprocal_rank=mrr,
            query_details=query_results,
        )


retrieval_evaluator = RetrievalEvaluator()
