"""
DevPilot AI - Unit Tests for Logical Chunker.
"""

from app.ingestion.chunking import LogicalChunker


def test_chunk_endpoint() -> None:
    """Test converting OpenAPI endpoint into structured contract chunk."""
    chunker = LogicalChunker()
    ep_data = {
        "path": "/orders",
        "method": "POST",
        "summary": "Create order",
        "auth_required": True,
        "tags": ["Orders"],
        "parameters_schema": [],
        "request_body_schema": {
            "_required": True,
            "properties": {
                "items": {"type": "array", "description": "Order items"},
                "shipping_address": {"type": "string"},
            },
        },
        "responses_schema": {
            "201": {"description": "Order created successfully"},
            "422": {"description": "Validation error"},
        },
    }

    chunk = chunker.chunk_endpoint(ep_data, doc_title="Orders API")
    assert chunk.doc_type == "endpoint_contract"
    assert chunk.endpoint_path == "/orders"
    assert chunk.http_method == "POST"
    assert "[API-CONTRACT] POST /orders" in chunk.chunk_text
    assert "Authentication: Required (Bearer Token)" in chunk.chunk_text
    assert "HTTP 201" in chunk.chunk_text
    assert "items" in chunk.chunk_text


def test_chunk_markdown_guide() -> None:
    """Test splitting Markdown guideline by headers."""
    chunker = LogicalChunker()
    markdown = """# QA Testing Standards

## Section 1: Boundary Rules
Always test zero and negative integers.

## Section 2: Header Checks
Always test missing Bearer token.
"""
    chunks = chunker.chunk_markdown_guide(markdown, doc_title="QA Testing Standards")
    assert len(chunks) == 2
    assert chunks[0].doc_type == "qa_guideline"
    assert "Section 1: Boundary Rules" in chunks[0].title
    assert "Section 2: Header Checks" in chunks[1].title
    assert "zero and negative integers" in chunks[0].chunk_text


def test_chunk_bug_report() -> None:
    """Test converting JSON bug report into regression knowledge chunk."""
    chunker = LogicalChunker()
    bug_json = """{
        "bug_id": "BUG-ORD-042",
        "title": "Negative quantity allowed",
        "affected_endpoint": "/orders",
        "http_method": "POST",
        "severity": "CRITICAL",
        "symptom": "Allowed negative item quantity",
        "root_cause": "Missing Pydantic ge=1 constraint",
        "regression_test_requirement": "Assert quantity <= 0 returns 422"
    }"""

    chunk = chunker.chunk_bug_report(bug_json)
    assert chunk.doc_type == "bug_report"
    assert chunk.endpoint_path == "/orders"
    assert chunk.http_method == "POST"
    assert "[HISTORICAL-BUG-REPORT] ID: BUG-ORD-042" in chunk.chunk_text
    assert "Missing Pydantic ge=1 constraint" in chunk.chunk_text
    assert "Assert quantity <= 0 returns 422" in chunk.chunk_text
