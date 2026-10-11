"""
DevPilot AI - Unit Tests for ContractValidator.
Verifies pre-execution deterministic validation rules against OpenAPI specifications.
"""

import pytest
from app.validation.contract_validator import ContractValidator
from app.schemas.test_case import GeneratedTestCaseItem
from app.models.spec import ApiEndpoint


@pytest.fixture
def sample_orders_endpoint() -> ApiEndpoint:
    """Fixture providing a mock ApiEndpoint representing POST /api/v1/orders."""
    return ApiEndpoint(
        id="ep-orders-post",
        spec_id="spec-ecommerce",
        path="/api/v1/orders",
        method="POST",
        summary="Create a new customer order",
        auth_required=True,
        parameters_schema=[],
        request_body_schema={
            "required": True,
            "schema": {
                "type": "object",
                "required": ["customer_id", "items"],
                "properties": {
                    "customer_id": {"type": "string"},
                    "items": {"type": "array"},
                    "shipping_address": {"type": "string"},
                },
            },
        },
        responses_schema={
            "201": {"description": "Order successfully created"},
            "400": {"description": "Bad Request / Invalid Order Data"},
            "401": {"description": "Unauthorized"},
        },
    )


@pytest.fixture
def sample_order_detail_endpoint() -> ApiEndpoint:
    """Fixture providing a mock ApiEndpoint with path parameter GET /api/v1/orders/{order_id}."""
    return ApiEndpoint(
        id="ep-orders-get-detail",
        spec_id="spec-ecommerce",
        path="/api/v1/orders/{order_id}",
        method="GET",
        summary="Retrieve order details by order_id",
        auth_required=True,
        parameters_schema=[
            {"name": "order_id", "in": "path", "required": True, "schema": {"type": "string"}}
        ],
        request_body_schema=None,
        responses_schema={
            "200": {"description": "Order details returned"},
            "404": {"description": "Order not found"},
        },
    )


def test_valid_positive_test_case_passes(sample_orders_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-001",
        name="Valid Order Creation",
        description="Submits valid order payload and verifies HTTP 201 response.",
        category="positive",
        priority="critical",
        request_headers={"Authorization": "Bearer token"},
        path_params={},
        query_params={},
        request_body={
            "customer_id": "cust-123",
            "items": [{"product_id": "prod-1", "quantity": 1}],
        },
        expected_status=201,
        expected_response_checks={"status_code": 201},
        source_references=["API Spec"],
        requires_review=False,
    )

    outcome = validator.validate_test_case(tc, sample_orders_endpoint)
    assert outcome.is_valid is True
    assert len(outcome.errors) == 0
    assert outcome.requires_review is False


def test_missing_path_parameter_fails_validation(sample_order_detail_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-GET-001",
        name="Get Order Without Path Param",
        description="Fails to provide required order_id path param.",
        category="positive",
        priority="high",
        path_params={},  # Missing order_id!
        expected_status=200,
    )

    outcome = validator.validate_test_case(tc, sample_order_detail_endpoint)
    assert outcome.is_valid is False
    assert any("Missing required path parameter 'order_id'" in err for err in outcome.errors)


def test_invalid_status_code_range_fails(sample_orders_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-INV-STATUS",
        name="Invalid Status Code Test",
        description="Specifies nonsense HTTP 999 status.",
        category="negative",
        expected_status=999,
    )

    outcome = validator.validate_test_case(tc, sample_orders_endpoint)
    assert outcome.is_valid is False
    assert any("Must be between 100 and 599" in err for err in outcome.errors)


def test_undocumented_standard_error_flags_review(sample_order_detail_endpoint: ApiEndpoint) -> None:
    """GET /orders/{order_id} documents only 200 and 404. If test expects 401, it flags review."""
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-GET-SEC-001",
        name="Unauthorized Order Access",
        description="Tests missing auth returning 401 when 401 is not explicitly declared.",
        category="security",
        path_params={"order_id": "ord-123"},
        expected_status=401,
    )

    outcome = validator.validate_test_case(tc, sample_order_detail_endpoint)
    assert outcome.is_valid is True  # Allowed as standard HTTP error code
    assert outcome.requires_review is True  # But flagged for QA review!
    assert any("not explicitly documented" in warn for warn in outcome.warnings)


def test_missing_required_property_in_positive_body_fails(sample_orders_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-BODY-FAIL",
        name="Missing Customer ID",
        description="Positive test missing required customer_id property.",
        category="positive",
        request_body={"items": [{"product_id": "prod-1"}]},  # Missing customer_id
        expected_status=201,
    )

    outcome = validator.validate_test_case(tc, sample_orders_endpoint)
    assert outcome.is_valid is False
    assert any("missing required schema property 'customer_id'" in err for err in outcome.errors)


def test_body_type_mismatch_fails_in_positive_test(sample_orders_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-TYPE-FAIL",
        name="Wrong items type",
        description="Positive test sends string instead of array for items.",
        category="positive",
        request_body={"customer_id": "cust-1", "items": "not-an-array"},
        expected_status=201,
    )

    outcome = validator.validate_test_case(tc, sample_orders_endpoint)
    assert outcome.is_valid is False
    assert any("Property 'items' expected array type" in err for err in outcome.errors)


def test_security_ssrf_disallowed_header_fails(sample_orders_endpoint: ApiEndpoint) -> None:
    validator = ContractValidator()
    tc = GeneratedTestCaseItem(
        test_id_code="TC-ORD-SSRF",
        name="Host Header Injection Test",
        description="Injects malicious X-Forwarded-Host.",
        category="security",
        request_headers={"X-Forwarded-Host": "attacker-controlled-host.com"},
        request_body={"customer_id": "cust-1", "items": []},
        expected_status=400,
    )

    outcome = validator.validate_test_case(tc, sample_orders_endpoint)
    assert outcome.is_valid is False
    assert any("header 'X-Forwarded-Host' is restricted" in err for err in outcome.errors)
