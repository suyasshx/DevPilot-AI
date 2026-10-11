"""
DevPilot AI - Logical Contract-Aware Chunking Engine.

Splits OpenAPI endpoints, Markdown QA guidelines, and synthetic bug reports
into semantic, metadata-rich chunks for RAG embedding and vector search.
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class DocumentChunkData:
    """Normalized logical chunk ready for embedding and persistence."""
    chunk_text: str
    chunk_index: int
    doc_type: str
    title: str
    source_uri: Optional[str] = None
    endpoint_path: Optional[str] = None
    http_method: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LogicalChunker:
    """Deconstructs testing knowledge and API specifications into semantic chunks."""

    def chunk_endpoint(self, endpoint_data: Dict[str, Any], doc_title: str) -> DocumentChunkData:
        """
        Convert a parsed OpenAPI endpoint into a structured, contract-grounded chunk.
        """
        path = endpoint_data.get("path", "")
        method = endpoint_data.get("method", "GET").upper()
        summary = endpoint_data.get("summary", "")
        auth = "Required (Bearer Token)" if endpoint_data.get("auth_required") else "None (Public)"

        lines = [
            f"[API-CONTRACT] {method} {path}",
            f"Summary: {summary}",
            f"Authentication: {auth}",
            f"Tags: {', '.join(endpoint_data.get('tags', []))}",
            "",
            "PARAMETERS:",
        ]

        params = endpoint_data.get("parameters_schema", [])
        if params:
            for p in params:
                req = "REQUIRED" if p.get("required") else "OPTIONAL"
                schema_info = p.get("schema", {})
                p_type = schema_info.get("type", "any")
                lines.append(f"  - {p.get('name')} ({p.get('in')}, {req}, type={p_type})")
        else:
            lines.append("  (No parameters)")

        body_schema = endpoint_data.get("request_body_schema", {})
        if body_schema:
            lines.append("")
            lines.append("REQUEST BODY:")
            lines.append(f"  Required: {body_schema.get('_required', False)}")
            props = body_schema.get("properties", {})
            for prop_name, prop_def in props.items():
                lines.append(f"  - {prop_name}: type={prop_def.get('type')}, description={prop_def.get('description', '')}")

        responses = endpoint_data.get("responses_schema", {})
        if responses:
            lines.append("")
            lines.append("DOCUMENTED RESPONSES:")
            for code, resp_def in responses.items():
                lines.append(f"  - HTTP {code}: {resp_def.get('description', '')}")

        chunk_text = "\n".join(lines)
        return DocumentChunkData(
            chunk_text=chunk_text,
            chunk_index=0,
            doc_type="endpoint_contract",
            title=f"Contract: {method} {path}",
            endpoint_path=path,
            http_method=method,
            metadata={
                "endpoint": path,
                "method": method,
                "doc_type": "endpoint_contract",
                "auth_required": endpoint_data.get("auth_required", False),
            },
        )

    def chunk_markdown_guide(self, markdown_text: str, doc_title: str, source_uri: Optional[str] = None) -> List[DocumentChunkData]:
        """
        Split Markdown QA guidelines by section headers (##) to maintain logical coherence.
        """
        chunks: List[DocumentChunkData] = []
        # Split by level-2 markdown headers
        sections = re.split(r"\n(?=##\s+)", markdown_text.strip())

        for idx, sec in enumerate(sections):
            sec = sec.strip()
            if not sec:
                continue

            header_match = re.match(r"^##\s+(.+)$", sec, re.MULTILINE)
            section_title = header_match.group(1).strip() if header_match else f"{doc_title} (Section {idx + 1})"

            chunk_text = f"[QA-GUIDELINE] {doc_title} - {section_title}\n\n{sec}"
            chunks.append(
                DocumentChunkData(
                    chunk_text=chunk_text,
                    chunk_index=idx,
                    doc_type="qa_guideline",
                    title=f"{doc_title}: {section_title}",
                    source_uri=source_uri,
                    metadata={
                        "doc_type": "qa_guideline",
                        "section_title": section_title,
                        "guide_title": doc_title,
                    },
                )
            )

        return chunks

    def chunk_bug_report(self, bug_json_str: str, source_uri: Optional[str] = None) -> DocumentChunkData:
        """
        Convert a synthetic bug report into a structured regression knowledge chunk.
        """
        data = json.loads(bug_json_str)
        bug_id = data.get("bug_id", "BUG-UNKNOWN")
        title = data.get("title", "")
        endpoint = data.get("affected_endpoint", "")
        method = data.get("http_method", "GET").upper()

        chunk_text = (
            f"[HISTORICAL-BUG-REPORT] ID: {bug_id}\n"
            f"Title: {title}\n"
            f"Endpoint: {method} {endpoint}\n"
            f"Severity: {data.get('severity', 'MEDIUM')}\n\n"
            f"Symptom:\n{data.get('symptom', '')}\n\n"
            f"Root Cause:\n{data.get('root_cause', '')}\n\n"
            f"Regression Test Requirement:\n{data.get('regression_test_requirement', '')}"
        )

        return DocumentChunkData(
            chunk_text=chunk_text,
            chunk_index=0,
            doc_type="bug_report",
            title=f"Bug {bug_id}: {title}",
            source_uri=source_uri,
            endpoint_path=endpoint,
            http_method=method,
            metadata={
                "doc_type": "bug_report",
                "bug_id": bug_id,
                "endpoint": endpoint,
                "method": method,
                "severity": data.get("severity"),
            },
        )
