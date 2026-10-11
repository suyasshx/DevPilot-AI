"""
DevPilot AI - Contract-Aware Deterministic Test Case Validator.
Validates LLM-generated test cases against the ground-truth OpenAPI specification
before tests are approved or allowed to execute.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from ..schemas.test_case import GeneratedTestCaseItem
from ..models.spec import ApiEndpoint
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ValidationOutcome:
    """Detailed result of deterministic contract validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_review: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class ContractValidator:
    """
    Deterministic validator that verifies whether a generated test case
    is grounded in the API's OpenAPI contract.
    """

    def __init__(self, allowed_hosts: Optional[List[str]] = None) -> None:
        self.allowed_hosts = allowed_hosts or settings.ALLOWED_TARGET_HOSTS

    def validate_test_case(
        self,
        test_case: GeneratedTestCaseItem,
        endpoint: ApiEndpoint,
    ) -> ValidationOutcome:
        """
        Validate an AI-generated test case against the target endpoint's contract.
        """
        errors: List[str] = []
        warnings: List[str] = []
        requires_review: bool = test_case.requires_review

        # 1. Verify HTTP Status Code Range
        if not (100 <= test_case.expected_status <= 599):
            errors.append(f"Invalid HTTP status code: {test_case.expected_status}. Must be between 100 and 599.")

        # 2. Status Code Grounding against Contract Declared Responses
        declared_responses = endpoint.responses_schema or {}
        declared_status_codes = [str(k) for k in declared_responses.keys()]

        status_str = str(test_case.expected_status)
        is_declared = (
            status_str in declared_status_codes
            or f"{status_str[0]}XX" in declared_status_codes
            or "default" in declared_status_codes
        )

        if not is_declared:
            # If not explicitly in the spec, standard error codes are allowed but require human review
            standard_error_codes = {400, 401, 403, 404, 405, 409, 422, 429}
            if test_case.expected_status in standard_error_codes:
                warnings.append(
                    f"Expected status {test_case.expected_status} is not explicitly documented "
                    f"in responses for {endpoint.method} {endpoint.path}. Flagged for review."
                )
                requires_review = True
            else:
                errors.append(
                    f"Expected status {test_case.expected_status} is undocumented and non-standard "
                    f"for {endpoint.method} {endpoint.path}. Declared: {list(declared_responses.keys())}"
                )

        # 3. Path Parameters Check
        # Extract {param} placeholders from endpoint path
        expected_path_params = re.findall(r"\{([a-zA-Z0-9_\-]+)\}", endpoint.path)
        for param in expected_path_params:
            if param not in test_case.path_params:
                errors.append(
                    f"Missing required path parameter '{param}' declared in endpoint path '{endpoint.path}'."
                )

        # 4. Query Parameters Validation against Parameter Schema
        params_schema = endpoint.parameters_schema or []
        declared_query_params = {
            p.get("name"): p for p in params_schema if isinstance(p, dict) and p.get("in") == "query"
        }

        # Check required query parameters in positive tests
        if test_case.category == "positive":
            for param_name, param_def in declared_query_params.items():
                if param_def.get("required", False) and param_name not in test_case.query_params:
                    errors.append(
                        f"Missing required query parameter '{param_name}' in positive test scenario."
                    )

        # Flag undocumented query params
        for qp in test_case.query_params.keys():
            if declared_query_params and qp not in declared_query_params:
                warnings.append(
                    f"Query parameter '{qp}' is not documented in the endpoint contract specification."
                )
                requires_review = True

        # 5. Request Body Validation
        body_schema = endpoint.request_body_schema or {}
        has_body_schema = bool(body_schema)

        if endpoint.method.upper() in ("POST", "PUT", "PATCH"):
            # Check if body is marked required in contract
            is_body_required = body_schema.get("required", False) if isinstance(body_schema, dict) else False

            if is_body_required and test_case.category == "positive" and not test_case.request_body:
                errors.append(
                    f"Endpoint requires a request body according to contract, but positive test has empty request_body."
                )

            # Deep check schema properties if present
            schema_content = body_schema.get("schema", {}) if isinstance(body_schema, dict) else {}
            required_properties = schema_content.get("required", []) if isinstance(schema_content, dict) else []
            properties = schema_content.get("properties", {}) if isinstance(schema_content, dict) else {}

            if test_case.category == "positive" and required_properties:
                for req_prop in required_properties:
                    if req_prop not in test_case.request_body:
                        errors.append(
                            f"Positive test body is missing required schema property '{req_prop}'."
                        )

            # Check for property type mismatches in positive tests
            if test_case.category == "positive" and properties:
                for prop_name, prop_val in test_case.request_body.items():
                    if prop_name in properties:
                        expected_type = properties[prop_name].get("type")
                        if expected_type == "integer" and not isinstance(prop_val, int):
                            errors.append(
                                f"Property '{prop_name}' expected integer type, received {type(prop_val).__name__}."
                            )
                        elif expected_type == "string" and not isinstance(prop_val, str):
                            errors.append(
                                f"Property '{prop_name}' expected string type, received {type(prop_val).__name__}."
                            )
                        elif expected_type == "array" and not isinstance(prop_val, list):
                            errors.append(
                                f"Property '{prop_name}' expected array type, received {type(prop_val).__name__}."
                            )
                        elif expected_type == "object" and not isinstance(prop_val, dict):
                            errors.append(
                                f"Property '{prop_name}' expected object type, received {type(prop_val).__name__}."
                            )

        # 6. Security & SSRF Protection Headers Check
        disallowed_header_keys = {"x-forwarded-host", "x-forwarded-for", "forwarded"}
        for h_key, h_val in test_case.request_headers.items():
            if h_key.lower() in disallowed_header_keys:
                errors.append(f"Security violation: header '{h_key}' is restricted and prohibited in test execution.")

            # Ensure header values do not point to malicious or unexpected external schemes
            if any(scheme in str(h_val).lower() for scheme in ("file://", "gopher://", "ftp://")):
                errors.append(f"Security violation: header '{h_key}' contains disallowed URI scheme.")

        is_valid = len(errors) == 0

        return ValidationOutcome(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            requires_review=requires_review,
            details={
                "status_code_declared": is_declared,
                "has_body_schema": has_body_schema,
                "path_params_checked": expected_path_params,
            },
        )
