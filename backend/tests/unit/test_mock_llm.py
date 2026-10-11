"""
DevPilot AI - Unit Tests for Mock LLM Provider, Prompts, and Deduplication.
"""

import json
import pytest
from app.llm.mock_provider import MockLLMProvider
from app.llm.prompts import (
    SYSTEM_PROMPT,
    build_generation_user_prompt,
    build_repair_user_prompt,
)
from app.schemas.test_case import GeneratedTestCaseItem
from app.validation.deduplicator import TestCaseDeduplicator


@pytest.mark.asyncio
async def test_mock_llm_synthesizes_valid_json_cases() -> None:
    provider = MockLLMProvider()
    user_prompt = "HTTP Method: POST\nPath: /api/v1/orders\nSummary: Create order"

    response = await provider.generate_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    assert response.raw_text
    assert response.latency_ms > 0
    assert response.metadata["mock"] is True

    parsed = json.loads(response.raw_text)
    assert "test_cases" in parsed
    assert len(parsed["test_cases"]) >= 5

    # Check Pydantic validation for all generated cases
    for case_data in parsed["test_cases"]:
        item = GeneratedTestCaseItem(**case_data)
        assert item.test_id_code
        assert item.name
        assert item.category in ("positive", "negative", "boundary", "security", "regression")
        assert 100 <= item.expected_status <= 599


@pytest.mark.asyncio
async def test_mock_llm_simulates_malformed_then_recovers() -> None:
    """Verifies that simulate_malformed_attempts behaves as expected for self-repair verification."""
    provider = MockLLMProvider(simulate_malformed_attempts=1)
    prompt = "HTTP Method: GET\nPath: /api/v1/products"

    # Attempt 1: Should fail JSON parsing
    resp1 = await provider.generate_completion(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
    with pytest.raises(json.JSONDecodeError):
        json.loads(resp1.raw_text)

    # Attempt 2: Should succeed with valid JSON
    resp2 = await provider.generate_completion(system_prompt=SYSTEM_PROMPT, user_prompt=prompt)
    data = json.loads(resp2.raw_text)
    assert "test_cases" in data
    assert len(data["test_cases"]) > 0


def test_generation_user_prompt_formatting() -> None:
    prompt = build_generation_user_prompt(
        endpoint_path="/api/v1/orders",
        method="POST",
        summary="Create order",
        parameters_schema=[],
        request_body_schema={"required": True},
        responses_schema={"201": {}},
        auth_required=True,
        rag_context="<qa_testing_guidelines>\nGuideline content\n</qa_testing_guidelines>",
        testing_objective="Verify boundary and security cases",
        categories=["positive", "boundary", "security"],
    )

    assert "HTTP Method: POST" in prompt
    assert "Path: /api/v1/orders" in prompt
    assert "<qa_testing_guidelines>" in prompt
    assert "Verify boundary and security cases" in prompt
    assert "positive, boundary, security" in prompt


def test_repair_user_prompt_formatting() -> None:
    prompt = build_repair_user_prompt(
        raw_response='{"test_cases": [{"name": "bad"}]}',
        validation_errors=["Missing required field 'expected_status'"],
        endpoint_path="/api/v1/orders",
        method="POST",
    )

    assert "Missing required field 'expected_status'" in prompt
    assert "POST /api/v1/orders" in prompt
    assert "Self-Repair Instructions:" in prompt


def test_test_case_deduplicator() -> None:
    tc1 = GeneratedTestCaseItem(
        test_id_code="TC-ORD-001",
        name="Order 1",
        description="Test 1",
        category="positive",
        expected_status=201,
        request_body={"customer_id": "cust-1", "items": [{"id": 1}]},
    )
    tc2 = GeneratedTestCaseItem(
        test_id_code="TC-ORD-002",
        name="Order Duplicate",
        description="Duplicate with same body and params",
        category="positive",
        expected_status=201,
        request_body={"customer_id": "cust-1", "items": [{"id": 1}]},
    )
    tc3 = GeneratedTestCaseItem(
        test_id_code="TC-ORD-003",
        name="Order Different",
        description="Different body",
        category="positive",
        expected_status=201,
        request_body={"customer_id": "cust-2", "items": [{"id": 2}]},
    )

    unique_items, dup_count = TestCaseDeduplicator.deduplicate(
        test_cases=[tc1, tc2, tc3],
        endpoint_id="ep-1",
        http_method="POST",
        existing_signatures=set(),
    )

    assert len(unique_items) == 2
    assert dup_count == 1
    assert unique_items[0].test_id_code == "TC-ORD-001"
    assert unique_items[1].test_id_code == "TC-ORD-003"
