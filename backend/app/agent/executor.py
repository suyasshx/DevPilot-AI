"""
DevPilot AI - Isolated Test Harness Executor.
Executes declarative test cases against target APIs using HTTPX,
captures evidentiary request/response telemetry, and validates assertions.
"""

import time
import urllib.parse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import httpx

from ..schemas.test_case import GeneratedTestCaseItem
from ..core.config import settings


@dataclass
class ExecutionResultItem:
    """Evidentiary result from executing a single test case."""
    test_id_code: str
    test_name: str
    category: str
    expected_status: int
    actual_status: Optional[int]
    is_passed: bool
    response_time_ms: float
    request_sent: Dict[str, Any]
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_body: Optional[Any] = None
    assertion_evidence: List[str] = field(default_factory=list)
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class TestHarnessExecutor:
    """Executes declarative test cases safely and deterministically against target services."""

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        allowed_hosts: Optional[List[str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.allowed_hosts = allowed_hosts or settings.ALLOWED_TARGET_HOSTS

    def _validate_host_security(self, url: str) -> None:
        """Enforce SSRF guardrail checking host allowlist."""
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in self.allowed_hosts:
            raise ValueError(
                f"Security violation: Target host '{host}' is not in ALLOWED_TARGET_HOSTS ({self.allowed_hosts})."
            )

    async def execute_test(
        self,
        endpoint_path: str,
        http_method: str,
        test_case: GeneratedTestCaseItem,
        auth_token_override: Optional[str] = None,
    ) -> ExecutionResultItem:
        """Execute a single test case and collect telemetry."""
        # Interpolate path params into path
        resolved_path = endpoint_path
        for param_key, param_val in test_case.path_params.items():
            resolved_path = resolved_path.replace(f"{{{param_key}}}", str(param_val))

        full_url = f"{self.base_url}{resolved_path}"
        self._validate_host_security(full_url)

        headers = dict(test_case.request_headers)
        if auth_token_override and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {auth_token_override}"

        # Request payload record (sanitized)
        request_record = {
            "method": http_method.upper(),
            "url": full_url,
            "headers": {k: ("***" if "auth" in k.lower() else v) for k, v in headers.items()},
            "query_params": test_case.query_params,
            "body": test_case.request_body,
        }

        assertion_evidence: List[str] = []
        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                req_kwargs: Dict[str, Any] = {
                    "method": http_method.upper(),
                    "url": full_url,
                    "headers": headers,
                    "params": test_case.query_params or None,
                }
                if http_method.upper() in ("POST", "PUT", "PATCH") and test_case.request_body:
                    req_kwargs["json"] = test_case.request_body

                resp = await client.request(**req_kwargs)
                latency_ms = (time.perf_counter() - start_time) * 1000.0

                actual_status = resp.status_code
                try:
                    resp_body = resp.json()
                except Exception:
                    resp_body = resp.text

                # Check status code assertion
                status_matched = (actual_status == test_case.expected_status)
                if status_matched:
                    assertion_evidence.append(
                        f"Status code check PASSED: Received HTTP {actual_status} (expected {test_case.expected_status})"
                    )
                else:
                    assertion_evidence.append(
                        f"Status code check FAILED: Received HTTP {actual_status} (expected {test_case.expected_status})"
                    )

                # Custom response checks
                checks_passed = True
                checks = test_case.expected_response_checks or {}
                if checks.get("check_error_field_present"):
                    has_error = isinstance(resp_body, dict) and any(k in resp_body for k in ("error", "detail", "message"))
                    if has_error:
                        assertion_evidence.append("Error field check PASSED: Response contains standard error field.")
                    else:
                        assertion_evidence.append("Error field check FAILED: Response does not contain 'error' or 'detail'.")
                        checks_passed = False

                is_passed = status_matched and checks_passed
                error_type = None if is_passed else ("assertion_error" if actual_status != 500 else "server_crash")
                error_msg = None if is_passed else (
                    f"Expected status {test_case.expected_status}, received {actual_status}"
                )

                return ExecutionResultItem(
                    test_id_code=test_case.test_id_code,
                    test_name=test_case.name,
                    category=test_case.category,
                    expected_status=test_case.expected_status,
                    actual_status=actual_status,
                    is_passed=is_passed,
                    response_time_ms=latency_ms,
                    request_sent=request_record,
                    response_headers=dict(resp.headers),
                    response_body=resp_body,
                    assertion_evidence=assertion_evidence,
                    error_type=error_type,
                    error_message=error_msg,
                )

        except (httpx.ConnectError, httpx.ConnectTimeout) as conn_err:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResultItem(
                test_id_code=test_case.test_id_code,
                test_name=test_case.name,
                category=test_case.category,
                expected_status=test_case.expected_status,
                actual_status=None,
                is_passed=False,
                response_time_ms=latency_ms,
                request_sent=request_record,
                assertion_evidence=["Connection failed: Host unreachable or connection refused."],
                error_type="connect_error",
                error_message=f"Target connection failed: {str(conn_err)}",
            )
        except httpx.TimeoutException as timeout_err:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResultItem(
                test_id_code=test_case.test_id_code,
                test_name=test_case.name,
                category=test_case.category,
                expected_status=test_case.expected_status,
                actual_status=None,
                is_passed=False,
                response_time_ms=latency_ms,
                request_sent=request_record,
                assertion_evidence=[f"Request timed out after {self.timeout_seconds}s."],
                error_type="timeout",
                error_message=f"Request timed out: {str(timeout_err)}",
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResultItem(
                test_id_code=test_case.test_id_code,
                test_name=test_case.name,
                category=test_case.category,
                expected_status=test_case.expected_status,
                actual_status=None,
                is_passed=False,
                response_time_ms=latency_ms,
                request_sent=request_record,
                assertion_evidence=[f"Execution exception: {str(exc)}"],
                error_type="execution_exception",
                error_message=str(exc),
            )
