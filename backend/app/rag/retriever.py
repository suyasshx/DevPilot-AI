"""
DevPilot AI - RAG Retriever and Context Assembly Service.

Manages knowledge ingestion, embedding generation, similarity retrieval,
and grounded XML context construction for LLM test case generation.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .embeddings import embedding_engine, EmbeddingEngine
from .vector_store import vector_store, VectorStore, SearchResult
from ..ingestion.chunking import LogicalChunker, DocumentChunkData
from ..models.knowledge import KnowledgeDocument, DocumentChunk
from ..models.spec import ApiEndpoint


@dataclass
class RetrievedContext:
    """Bounded, grounded context ready for LLM prompt insertion."""
    prompt_context: str
    source_references: List[str]
    retrieved_chunks: List[SearchResult] = field(default_factory=list)


class RAGRetriever:
    """Service orchestrating knowledge ingestion, retrieval, and prompt context grounding."""

    def __init__(
        self,
        embedder: Optional[EmbeddingEngine] = None,
        store: Optional[VectorStore] = None,
        chunker: Optional[LogicalChunker] = None,
    ) -> None:
        self.embedder = embedder or embedding_engine
        self.store = store or vector_store
        self.chunker = chunker or LogicalChunker()

    async def ingest_document(
        self,
        db: AsyncSession,
        project_id: str,
        title: str,
        doc_type: str,
        raw_text: str,
        source_uri: Optional[str] = None,
    ) -> KnowledgeDocument:
        """
        Ingest a document (QA guideline or bug report), chunk it,
        generate vector embeddings, and persist chunks to the database.
        """
        doc = KnowledgeDocument(
            project_id=project_id,
            title=title,
            doc_type=doc_type,
            source_uri=source_uri,
            raw_text=raw_text,
            metadata_json={"title": title, "doc_type": doc_type, "source_uri": source_uri},
        )
        db.add(doc)
        await db.flush()

        # Chunk document
        chunks_data: List[DocumentChunkData] = []
        if doc_type == "bug_report":
            chunk_item = self.chunker.chunk_bug_report(raw_text, source_uri=source_uri)
            chunks_data.append(chunk_item)
        elif doc_type == "qa_guideline":
            chunks_data = self.chunker.chunk_markdown_guide(raw_text, doc_title=title, source_uri=source_uri)
        else:
            chunks_data = [
                DocumentChunkData(
                    chunk_text=raw_text,
                    chunk_index=0,
                    doc_type=doc_type,
                    title=title,
                    source_uri=source_uri,
                    metadata={"doc_type": doc_type},
                )
            ]

        # Generate embeddings in batch
        texts_to_embed = [c.chunk_text for c in chunks_data]
        embeddings = self.embedder.encode(texts_to_embed)

        for c_data, emb in zip(chunks_data, embeddings):
            chunk_row = DocumentChunk(
                document_id=doc.id,
                chunk_text=c_data.chunk_text,
                chunk_index=c_data.chunk_index,
                metadata_json=c_data.metadata,
                embedding=emb,
            )
            db.add(chunk_row)

        await db.commit()
        await db.refresh(doc)
        return doc

    async def ingest_endpoints(
        self,
        db: AsyncSession,
        project_id: str,
        spec_id: str,
    ) -> int:
        """
        Index all parsed endpoints for an OpenAPI specification as searchable contract chunks.
        """
        result = await db.execute(select(ApiEndpoint).where(ApiEndpoint.spec_id == spec_id))
        endpoints = result.scalars().all()
        if not endpoints:
            return 0

        # Create virtual document for the specification's contracts
        spec_doc = KnowledgeDocument(
            project_id=project_id,
            title="OpenAPI Endpoint Contracts",
            doc_type="endpoint_contract",
            raw_text=f"Indexed {len(endpoints)} endpoint contracts.",
            metadata_json={"spec_id": spec_id},
        )
        db.add(spec_doc)
        await db.flush()

        chunks_data: List[DocumentChunkData] = []
        for ep in endpoints:
            ep_dict = {
                "path": ep.path,
                "method": ep.method,
                "summary": ep.summary,
                "parameters_schema": ep.parameters_schema,
                "request_body_schema": ep.request_body_schema,
                "responses_schema": ep.responses_schema,
                "auth_required": ep.auth_required,
                "tags": ep.tags,
            }
            c_data = self.chunker.chunk_endpoint(ep_dict, doc_title="API Contract")
            chunks_data.append(c_data)

        texts = [c.chunk_text for c in chunks_data]
        embeddings = self.embedder.encode(texts)

        for c_data, emb, ep in zip(chunks_data, embeddings, endpoints):
            chunk_row = DocumentChunk(
                document_id=spec_doc.id,
                endpoint_id=ep.id,
                chunk_text=c_data.chunk_text,
                chunk_index=0,
                metadata_json=c_data.metadata,
                embedding=emb,
            )
            db.add(chunk_row)

        await db.commit()
        return len(chunks_data)

    async def retrieve_context(
        self,
        db: AsyncSession,
        project_id: str,
        endpoint_path: str,
        method: str,
        testing_objective: str,
        top_k: int = 5,
    ) -> RetrievedContext:
        """
        Retrieve relevant knowledge chunks and format bounded XML context for the LLM.
        """
        # Construct hybrid semantic query
        query_text = f"Endpoint {method} {endpoint_path}. Objective: {testing_objective}."
        query_embedding = self.embedder.encode([query_text])[0]

        # Retrieve top chunks with metadata filtering
        results = await self.store.search(
            db=db,
            project_id=project_id,
            query_vector=query_embedding,
            top_k=top_k,
            endpoint_path=endpoint_path,
            method=method,
        )

        # Categorize chunks for structured prompt grounding
        contract_chunks: List[str] = []
        qa_chunks: List[str] = []
        bug_chunks: List[str] = []
        source_refs: List[str] = []

        for r in results:
            ref_label = f"{r.doc_title} (ID: {r.chunk_id[:8]})"
            source_refs.append(ref_label)

            if r.doc_type == "endpoint_contract":
                contract_chunks.append(r.chunk_text)
            elif r.doc_type == "bug_report":
                bug_chunks.append(r.chunk_text)
            else:
                qa_chunks.append(r.chunk_text)

        # Assemble prompt with strict XML boundary delimiters
        prompt_sections = []

        if contract_chunks:
            prompt_sections.append(
                "<ground_truth_api_contract>\n"
                + "\n\n".join(contract_chunks)
                + "\n</ground_truth_api_contract>"
            )

        if qa_chunks:
            prompt_sections.append(
                "<qa_testing_guidelines>\n"
                + "\n\n".join(qa_chunks)
                + "\n</qa_testing_guidelines>"
            )

        if bug_chunks:
            prompt_sections.append(
                "<historical_regression_bugs>\n"
                + "\n\n".join(bug_chunks)
                + "\n</historical_regression_bugs>"
            )

        prompt_context = "\n\n".join(prompt_sections)

        return RetrievedContext(
            prompt_context=prompt_context,
            source_references=source_refs,
            retrieved_chunks=results,
        )


rag_retriever = RAGRetriever()
