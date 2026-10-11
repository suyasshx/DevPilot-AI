"""
DevPilot AI - Unit Tests for Agent Tools, Harness Executor, and Taxonomy Classifier.
"""

import pytest
from app.agent.tools import validate_test_cases, classify_test_failure
from app.agent.classifier import FailureTaxonomyClassifier
from app.agent.executor import TestHarnessExecutor
from app.schemas.test_case import GeneratedTestCaseItem


def test_classify_all_five_taxonomy_archetypes() -> None:
    # 1. Passed test -> "none"
    res_pass = FailureTaxonomyClassifier.classify(
        expected_status=200,
        actual_status=200,
    )
    assert res_pass.category == "none"
    assert res_pass.is_failure is False

    # 2. Generation Error
    res_gen = FailureTaxonomyClassifier.classify(
        expected_status=200,
        actual_status=None,
        error_type="pydantic_validation",
        error_message="Missing required field 'name'",
    )
    assert res_gen.category == "generation_error"
    assert res_gen.is_failure is True

    # 3. Invalid Test
    res_inv = FailureTaxonomyClassifier.classify(
        expected_status=999,  # Invalid status range
        actual_status=None,
        error_type="invalid_test",
        error_message="Status 999 is outside HTTP specification",
    )
    assert res_inv.category == "invalid_test"
    assert res_inv.is_failure is True

    # 4. Execution Error (Server Crash)
    res_crash = FailureTaxonomyClassifier.classify(
        expected_status=200,
        actual_status=500,
        error_message="Internal Server Error: Unhandled KeyError",
    )
    assert res_crash.category == "execution_error"
    assert res_crash.is_failure is True
    assert "crashed" in res_crash.reason.lower()

    # 5. Contract Violation
    res_violation = FailureTaxonomyClassifier.classify(
        expected_status=400,
        actual_status=200,  # Bad payload accepted by server!
    )
    assert res_violation.category == "contract_violation"
    assert res_violation.is_failure is True

    # 6. Infrastructure Failure
    res_infra = FailureTaxonomyClassifier.classify(
        expected_status=200,
        actual_status=None,
        error_type="connect_error",
        error_message="Connection refused to localhost:8000",
    )
    assert res_infra.category == "infrastructure_failure"
    assert res_infra.is_failure is True


def test_validate_test_cases_tool() -> None:
    endpoint_meta = {
        "path": "/orders",
        "method": "POST",
        "parameters_schema": [],
        "request_body_schema": {
            "required": True,
            "schema": {
                "type": "object",
                "required": ["customer_id"],
                "properties": {"customer_id": {"type": "string"}},
            },
        },
        "responses_schema": {"201": {}, "400": {}},
        "auth_required": True,
    }

    raw_cases = [
        {
            "test_id_code": "TC-ORD-VALID",
            "name": "Valid Order",
            "description": "Standard positive order creation",
            "category": "positive",
            "request_body": {"customer_id": "cust-101"},
            "expected_status": 201,
        },
        {
            "test_id_code": "TC-ORD-INVALID-BODY",
            "name": "Missing Required Field",
            "description": "Positive test missing customer_id",
            "category": "positive",
            "request_body": {},  # Missing required customer_id!
            "expected_status": 201,
        },
    ]

    result = validate_test_cases(raw_cases, endpoint_meta)
    assert result["valid_count"] == 1
    assert result["invalid_count"] == 1
    assert result["valid_cases"][0]["test_id_code"] == "TC-ORD-VALID"
    assert result["validation_failures"][0]["test_id_code"] == "TC-ORD-INVALID-BODY"


@pytest.mark.asyncio
async def test_test_harness_executor_ssrf_guardrail() -> None:
    executor = TestHarnessExecutor(base_url="http://evil-external-host.com")
    tc = GeneratedTestCaseItem(
        test_id_code="TC-SSRF",
        name="Disallowed Host",
        description="Attempts to request non-allowlisted host",
        category="positive",
        expected_status=200,
    )

    with pytest.raises(ValueError, match="Security violation: Target host"):
        await executor.execute_test(
            endpoint_path="/api/test",
            http_method="GET",
            test_case=tc,
        )
