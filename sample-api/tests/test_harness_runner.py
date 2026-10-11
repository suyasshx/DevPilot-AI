"""
DevPilot AI - Deterministic Test Harness Runner.

A standalone HTTPX-based execution engine that executes declarative test cases,
records latencies, captures sanitized telemetry, evaluates assertions,
and produces a structured JSON execution summary.
"""

import sys
import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_API_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if SAMPLE_API_DIR not in sys.path:
    sys.path.insert(0, SAMPLE_API_DIR)

from app.main import app
from app.auth import create_access_token


class DeterministicHarnessRunner:
    """Executes declarative API test cases against the sample API using HTTPX."""

    def __init__(self, base_url: str = "http://testserver", use_asgi: bool = True) -> None:
        self.base_url = base_url
        self.use_asgi = use_asgi

    def _create_client(self) -> httpx.Client:
        if self.use_asgi:
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            return httpx.Client(transport=transport, base_url=self.base_url, timeout=10.0)
        return httpx.Client(base_url=self.base_url, timeout=10.0)

    def execute_test(self, client: httpx.Client, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an individual declarative test case and capture outcome telemetry."""
        test_id = test_case.get("test_id", "TC-UNKNOWN")
        name = test_case.get("name", "Unnamed Test")
        method = test_case.get("method", "GET").upper()
        path = test_case.get("path", "/")
        headers = test_case.get("headers", {})
        body = test_case.get("body", None)
        expected_status = test_case.get("expected_status", 200)
        expected_keys = test_case.get("expected_keys", [])

        start_time = time.perf_counter()
        status = "passed"
        failure_category = "none"
        error_message = None
        evidence = []
        actual_status = None
        response_body = {}

        try:
            response = client.request(
                method=method,
                url=path,
                headers=headers,
                json=body if body is not None else None,
            )
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            actual_status = response.status_code

            try:
                response_body = response.json()
            except Exception:
                response_body = {"raw_text": response.text[:200]}

            # 1. Status Code Check
            if actual_status != expected_status:
                status = "failed"
                evidence.append(
                    f"Expected status {expected_status}, but received {actual_status}."
                )

                if actual_status >= 500:
                    failure_category = "execution_error"
                    error_message = f"Server crashed with HTTP {actual_status} Internal Error."
                else:
                    failure_category = "contract_violation"
                    error_message = (
                        f"Status mismatch: expected {expected_status}, received {actual_status}."
                    )

            # 2. Key Presence Checks (Contract verification)
            if status == "passed" and isinstance(response_body, dict):
                for k in expected_keys:
                    if k not in response_body:
                        status = "failed"
                        failure_category = "contract_violation"
                        evidence.append(f"Missing required response key '{k}'.")
                        error_message = f"Response schema missing required key '{k}'."

        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as net_err:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status = "error"
            failure_category = "infrastructure_failure"
            error_message = f"Network or timeout failure: {str(net_err)}"
            evidence.append(error_message)

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            status = "error"
            failure_category = "execution_error"
            error_message = f"Execution exception: {str(exc)}"
            evidence.append(error_message)

        # Sanitize sensitive data in request headers
        sanitized_headers = {
            k: ("***REDACTED***" if "auth" in k.lower() or "token" in k.lower() else v)
            for k, v in headers.items()
        }

        return {
            "test_id": test_id,
            "name": name,
            "method": method,
            "path": path,
            "duration_ms": duration_ms,
            "status": status,
            "failure_category": failure_category,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "sanitized_request_headers": sanitized_headers,
            "sanitized_response_body": response_body,
            "evidence": evidence,
            "error_message": error_message,
        }

    def run_suite(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a full test suite and compile aggregate metrics."""
        results = []
        with self._create_client() as client:
            for tc in test_cases:
                res = self.execute_test(client, tc)
                results.append(res)

        total = len(results)
        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        errors = sum(1 for r in results if r["status"] == "error")

        durations = [r["duration_ms"] for r in results]
        avg_latency = round(sum(durations) / max(total, 1), 2)
        sorted_durations = sorted(durations)
        p95_idx = int(0.95 * len(sorted_durations))
        p95_latency = sorted_durations[p95_idx] if sorted_durations else 0.0

        return {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "pass_rate_pct": round((passed / max(total, 1)) * 100, 2),
                "avg_latency_ms": avg_latency,
                "p95_latency_ms": p95_latency,
                "executed_at": datetime.now(timezone.utc).isoformat(),
            },
            "results": results,
        }


def get_default_smoke_suite() -> List[Dict[str, Any]]:
    """Generates a standard deterministic smoke test suite."""
    valid_token = create_access_token({"sub": "1", "username": "qa_user", "role": "user"})
    auth_header = {"Authorization": f"Bearer {valid_token}"}

    return [
        {
            "test_id": "SMOKE-AUTH-001",
            "name": "Verify User Login with Valid Credentials",
            "method": "POST",
            "path": "/auth/login",
            "body": {"username": "qa_user", "password": "SecretPass123!"},
            "expected_status": 200,
            "expected_keys": ["access_token", "token_type", "user_id"],
        },
        {
            "test_id": "SMOKE-AUTH-002",
            "name": "Verify Rejection on Invalid Password",
            "method": "POST",
            "path": "/auth/login",
            "body": {"username": "qa_user", "password": "BadPassword123!"},
            "expected_status": 401,
            "expected_keys": ["detail"],
        },
        {
            "test_id": "SMOKE-PROD-001",
            "name": "Verify Product Catalog Retrieval",
            "method": "GET",
            "path": "/products?skip=0&limit=5",
            "expected_status": 200,
            "expected_keys": ["total", "items", "skip", "limit"],
        },
        {
            "test_id": "SMOKE-USER-001",
            "name": "Verify Fetch Existing User Profile",
            "method": "GET",
            "path": "/users/1",
            "expected_status": 200,
            "expected_keys": ["id", "username", "email", "role"],
        },
        {
            "test_id": "SMOKE-USER-002",
            "name": "Verify 404 on Non-Existent User Profile",
            "method": "GET",
            "path": "/users/9999",
            "expected_status": 404,
            "expected_keys": ["detail"],
        },
        {
            "test_id": "SMOKE-ORD-001",
            "name": "Verify Authenticated Order Creation",
            "method": "POST",
            "path": "/orders",
            "headers": auth_header,
            "body": {
                "items": [{"product_id": 1, "quantity": 1}],
                "shipping_address": "100 EA Way, Redwood City, CA",
                "payment_method": "credit_card",
            },
            "expected_status": 201,
            "expected_keys": ["id", "user_id", "total_amount", "status"],
        },
        {
            "test_id": "SMOKE-ORD-002",
            "name": "Verify 401 Rejection on Unauthenticated Order",
            "method": "POST",
            "path": "/orders",
            "body": {
                "items": [{"product_id": 1, "quantity": 1}],
                "shipping_address": "100 EA Way",
                "payment_method": "credit_card",
            },
            "expected_status": 401,
            "expected_keys": ["detail"],
        },
        {
            "test_id": "SMOKE-ORD-003",
            "name": "Verify 422 Rejection on Negative Quantity (Boundary Check)",
            "method": "POST",
            "path": "/orders",
            "headers": auth_header,
            "body": {
                "items": [{"product_id": 1, "quantity": -2}],
                "shipping_address": "100 EA Way",
                "payment_method": "credit_card",
            },
            "expected_status": 422,
            "expected_keys": ["detail"],
        },
    ]


if __name__ == "__main__":
    runner = DeterministicHarnessRunner()
    suite = get_default_smoke_suite()
    print(f"Running DevPilot AI Smoke Suite ({len(suite)} test cases)...")
    report = runner.run_suite(suite)
    print("\n=== EXECUTION SUMMARY ===")
    print(json.dumps(report["summary"], indent=2))
    print("\n=== TEST RESULTS ===")
    for r in report["results"]:
        status_icon = "PASS" if r["status"] == "passed" else "FAIL"
        print(f"[{status_icon}] {r['test_id']}: {r['name']} ({r['duration_ms']}ms) -> HTTP {r['actual_status']}")
