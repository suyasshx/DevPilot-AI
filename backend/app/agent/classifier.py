"""
DevPilot AI - 5-Way Failure Taxonomy Classifier.
Classifies automated test results into distinct failure archetypes:
1. generation_error: LLM produced unparseable or schema-invalid test definition.
2. invalid_test: Test definition contains illogical assertions or missing required parameters.
3. contract_violation: Target API returned a response violating OpenAPI contract specifications.
4. execution_error: Target API encountered an unhandled server crash (HTTP 500/502/503).
5. infrastructure_failure: Network timeout, connection refused, or unreachable host.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class FailureClassification:
    """Detailed classification verdict for a test outcome."""
    category: str
    confidence: float
    reason: str
    recommended_action: str
    is_failure: bool


class FailureTaxonomyClassifier:
    """Deterministic, rules-grounded classifier implementing the 5-Way Failure Taxonomy."""

    VALID_CATEGORIES = {
        "none",
        "generation_error",
        "invalid_test",
        "contract_violation",
        "execution_error",
        "infrastructure_failure",
    }

    @classmethod
    def classify(
        cls,
        expected_status: int,
        actual_status: Optional[int],
        response_body: Optional[Any] = None,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        declared_responses: Optional[Dict[str, Any]] = None,
    ) -> FailureClassification:
        """
        Classify execution outcome into the 5-way taxonomy.
        """
        # 1. Passed Condition
        if error_type is None and actual_status == expected_status:
            return FailureClassification(
                category="none",
                confidence=1.0,
                reason="Test passed successfully. Actual status matched expected contract status.",
                recommended_action="No action needed.",
                is_failure=False,
            )

        err_type_lower = (error_type or "").lower()
        err_msg_lower = (error_message or "").lower()

        # 2. Infrastructure Failure
        # Network unreachable, connect error, socket error, timeout
        if (
            "connect" in err_type_lower
            or "timeout" in err_type_lower
            or "dns" in err_type_lower
            or "connection refused" in err_msg_lower
            or "timed out" in err_msg_lower
            or actual_status is None
        ):
            return FailureClassification(
                category="infrastructure_failure",
                confidence=0.98,
                reason=f"Network or infrastructure failure: {error_message or 'Host unreachable'}",
                recommended_action="Verify target service availability, network connectivity, and host allowlist.",
                is_failure=True,
            )

        # 3. Generation Error
        # Malformed JSON, Pydantic validation failure on test case itself
        if (
            "generation" in err_type_lower
            or "pydantic" in err_type_lower
            or "json_decode" in err_type_lower
            or "syntax" in err_type_lower
        ):
            return FailureClassification(
                category="generation_error",
                confidence=0.95,
                reason=f"LLM generated an invalid test schema: {error_message}",
                recommended_action="Trigger self-repair retry loop with explicit schema correction instructions.",
                is_failure=True,
            )

        # 4. Execution Error (Unhandled Server Crash)
        # Server returned 500, 502, 503, 504 and expected status was NOT a 5xx
        if actual_status in (500, 502, 503, 504) and expected_status not in (500, 502, 503, 504):
            return FailureClassification(
                category="execution_error",
                confidence=0.99,
                reason=(
                    f"Target service crashed with unhandled HTTP {actual_status}. "
                    f"Expected HTTP {expected_status}. Error message: {error_message or 'Internal Server Error'}"
                ),
                recommended_action="File a high-priority defect ticket for server crash and exception handling.",
                is_failure=True,
            )

        # 5. Invalid Test Case
        # Test expected something illogical, missing required path param, or invalid status code
        if "invalid_test" in err_type_lower or not (100 <= expected_status <= 599):
            return FailureClassification(
                category="invalid_test",
                confidence=0.92,
                reason=f"Test case definition is invalid or ungrounded: {error_message}",
                recommended_action="Reject test case or revise assertions against OpenAPI specification.",
                is_failure=True,
            )

        # 6. Contract Violation
        # Endpoint returned a response that violates API contract
        # E.g. client sent malformed body, expected 400/422, but server accepted it and returned 200/201 (business rule breach)
        # Or server returned undocumented status code
        if actual_status != expected_status:
            return FailureClassification(
                category="contract_violation",
                confidence=0.94,
                reason=(
                    f"API contract violation: Server returned HTTP {actual_status}, "
                    f"expected contract status HTTP {expected_status}."
                ),
                recommended_action="Investigate API implementation against OpenAPI contract specification.",
                is_failure=True,
            )

        # Default fallback
        return FailureClassification(
            category="contract_violation",
            confidence=0.75,
            reason=f"Test assertion failed: {error_message}",
            recommended_action="Inspect assertion failure details and response body.",
            is_failure=True,
        )
