"""
DevPilot AI - Mock LLM Provider.
Provides deterministic, contract-grounded test generation for offline development,
continuous integration (CI), and self-repair resilience testing without requiring an active Groq API key.
"""

import json
import re
import time
from typing import Optional, List, Dict, Any
from .base import BaseLLMProvider, LLMResponse


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock provider that synthesizes realistic, contract-grounded test cases.
    Can also simulate malformed responses to test the self-repair retry loop.
    """

    def __init__(
        self,
        model_name: str = "mock-llama-3.3-70b",
        temperature: float = 0.0,
        simulate_malformed_attempts: int = 0,
        custom_responses: Optional[List[str]] = None,
    ) -> None:
        super().__init__(model_name=model_name, temperature=temperature)
        self.simulate_malformed_attempts = simulate_malformed_attempts
        self.attempt_counter = 0
        self.custom_responses = custom_responses or []
        self.call_history: List[Dict[str, Any]] = []

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format_json: bool = True,
        temperature: Optional[float] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate a deterministic completion response."""
        start_time = time.perf_counter()
        self.attempt_counter += 1

        self.call_history.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "attempt": self.attempt_counter,
        })

        # Check if custom scripted responses are queued
        if self.custom_responses:
            raw_text = self.custom_responses.pop(0)
            return self._build_response(raw_text, start_time)

        # Simulate malformed output for self-repair test verification if configured
        if self.attempt_counter <= self.simulate_malformed_attempts:
            # Output broken JSON missing closing brace
            malformed_text = '{"test_cases": [{"test_id_code": "TC-FAIL-001", "name": "Broken'
            return self._build_response(malformed_text, start_time)

        # Synthesize contract-grounded test cases based on user prompt context
        raw_text = self._synthesize_grounded_response(user_prompt)
        return self._build_response(raw_text, start_time)

    def _build_response(self, text: str, start_time: float) -> LLMResponse:
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        return LLMResponse(
            raw_text=text,
            model_name=self.model_name,
            prompt_tokens=450,
            completion_tokens=650,
            total_tokens=1100,
            latency_ms=latency_ms,
            metadata={"mock": True, "attempt": self.attempt_counter},
        )

    def _synthesize_grounded_response(self, user_prompt: str) -> str:
        """Extract endpoint details from user prompt and synthesize grounded test cases."""
        # Detect endpoint path and method from user prompt
        method_match = re.search(r"HTTP Method:\s*(GET|POST|PUT|PATCH|DELETE)", user_prompt, re.IGNORECASE)
        path_match = re.search(r"Path:\s*([/\w\-_\{}]+)", user_prompt)

        method = method_match.group(1).upper() if method_match else "POST"
        path = path_match.group(1) if path_match else "/api/v1/orders"

        # Extract path param names if any
        path_params = re.findall(r"\{([a-zA-Z0-9_\-]+)\}", path)
        sample_path_args = {p: "sample-id-123" if "id" in p.lower() else "test-val" for p in path_params}

        # Build clean test ID prefix
        clean_path_tag = re.sub(r"[^A-Za-z0-9]", "", path.split("/")[-1] or "EP").upper()
        prefix = f"TC-{method[:3]}-{clean_path_tag}"

        test_cases: List[Dict[str, Any]] = []

        # 1. Positive Scenario
        is_write = method in ("POST", "PUT", "PATCH")
        expected_success_code = 201 if method == "POST" else 200

        pos_body: Dict[str, Any] = {}
        if is_write:
            if "order" in path.lower():
                pos_body = {
                    "customer_id": "cust-9988",
                    "items": [{"product_id": "prod-101", "quantity": 2, "price": 49.99}],
                    "shipping_address": "123 EA Games Blvd, Suite 400",
                }
            elif "product" in path.lower():
                pos_body = {
                    "title": "EA Sports FC 26",
                    "price": 69.99,
                    "inventory_count": 100,
                    "category": "Gaming",
                }
            elif "user" in path.lower() or "auth" in path.lower():
                pos_body = {
                    "email": "qa_tester@ea.com",
                    "password": "StrongPassword123!",
                    "role": "tester",
                }
            else:
                pos_body = {"name": "Test Entity", "status": "active"}

        test_cases.append({
            "test_id_code": f"{prefix}-001",
            "name": f"Successful {method} on {path} (Happy Path)",
            "description": f"Verifies standard contract-compliant execution of {method} {path} returning HTTP {expected_success_code}.",
            "category": "positive",
            "priority": "critical",
            "request_headers": {"Content-Type": "application/json", "Authorization": "Bearer test-jwt-token"},
            "path_params": sample_path_args,
            "query_params": {},
            "request_body": pos_body,
            "expected_status": expected_success_code,
            "expected_response_checks": {"check_status_code": expected_success_code, "non_empty_response": True},
            "source_references": ["API Contract Spec", "QA Guideline - Core Contracts"],
            "requires_review": False,
        })

        # 2. Negative Scenario
        neg_body = {}
        if is_write:
            neg_body = dict(pos_body)
            # Corrupt a field or omit required
            if "items" in neg_body:
                neg_body["items"] = []  # Empty items invalid
            elif "price" in neg_body:
                neg_body["price"] = "invalid-not-a-number"
            elif "email" in neg_body:
                neg_body["email"] = "not-an-email"
            else:
                neg_body = {"invalid_field_only": True}

        test_cases.append({
            "test_id_code": f"{prefix}-002",
            "name": f"Reject Malformed Request Payload on {path}",
            "description": f"Validates that invalid parameter data produces HTTP 400 or 422 Unprocessable Entity.",
            "category": "negative",
            "priority": "high",
            "request_headers": {"Content-Type": "application/json", "Authorization": "Bearer test-jwt-token"},
            "path_params": sample_path_args,
            "query_params": {},
            "request_body": neg_body,
            "expected_status": 400 if is_write else 404,
            "expected_response_checks": {"check_error_field_present": True},
            "source_references": ["QA Guideline - Boundary and Negative Rules"],
            "requires_review": False,
        })

        # 3. Boundary Scenario
        bnd_body = {}
        if is_write:
            bnd_body = dict(pos_body)
            if "items" in bnd_body:
                bnd_body["items"] = [{"product_id": "prod-1", "quantity": 1, "price": 0.01}]
            elif "price" in bnd_body:
                bnd_body["price"] = 0.0
            elif "title" in bnd_body:
                bnd_body["title"] = "A" * 255  # Max boundary string

        test_cases.append({
            "test_id_code": f"{prefix}-003",
            "name": f"Boundary Value Edge Case on {path}",
            "description": f"Checks boundary conditions for numeric and string fields against contract limits.",
            "category": "boundary",
            "priority": "medium",
            "request_headers": {"Content-Type": "application/json", "Authorization": "Bearer test-jwt-token"},
            "path_params": sample_path_args,
            "query_params": {"limit": 100, "page": 1} if method == "GET" else {},
            "request_body": bnd_body,
            "expected_status": expected_success_code,
            "expected_response_checks": {"verify_boundary_handled": True},
            "source_references": ["QA Guideline - Boundary Testing Standards"],
            "requires_review": False,
        })

        # 4. Security Scenario
        test_cases.append({
            "test_id_code": f"{prefix}-004",
            "name": f"Unauthorized Access Rejection on {path}",
            "description": f"Validates that missing or expired JWT tokens return HTTP 401 Unauthorized.",
            "category": "security",
            "priority": "critical",
            "request_headers": {"Content-Type": "application/json"},  # Missing Authorization
            "path_params": sample_path_args,
            "query_params": {},
            "request_body": pos_body if is_write else {},
            "expected_status": 401,
            "expected_response_checks": {"check_unauthorized": True},
            "source_references": ["QA Guideline - Auth & Security Rules"],
            "requires_review": False,
        })

        # 5. Regression Scenario
        reg_body = {}
        if is_write and "order" in path.lower():
            reg_body = {
                "customer_id": "cust-9988",
                "items": [{"product_id": "prod-101", "quantity": -5, "price": 49.99}],
                "shipping_address": "123 EA Games Blvd",
            }
        else:
            reg_body = pos_body

        test_cases.append({
            "test_id_code": f"{prefix}-005",
            "name": f"Regression Guard for Known Defects on {path}",
            "description": "Verifies system guards against previously recorded defects (e.g. BUG-001 negative quantities).",
            "category": "regression",
            "priority": "high",
            "request_headers": {"Content-Type": "application/json", "Authorization": "Bearer test-jwt-token"},
            "path_params": sample_path_args,
            "query_params": {},
            "request_body": reg_body,
            "expected_status": 400 if ("order" in path.lower() and is_write) else expected_success_code,
            "expected_response_checks": {"regression_defect_rejected": True},
            "source_references": ["Historical Bug - BUG-001 Negative Quantity"],
            "requires_review": False,
        })

        return json.dumps({"test_cases": test_cases}, indent=2)
