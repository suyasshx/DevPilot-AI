"""
DevPilot AI - Prompt Templates and Engineering Layer.
Includes Senior QA system persona, XML-bounded RAG context formatting, and self-repair templates.
"""

import json
from typing import List, Dict, Any

PROMPT_VERSION = "v1.2.0-contract-grounded"

SYSTEM_PROMPT = """You are a Lead QA Automation Engineer and API Quality Architect at Electronic Arts (EA).
Your mission is to generate robust, contract-grounded, production-grade automated API test cases.

You will receive:
1. An OpenAPI contract for the target endpoint inside <ground_truth_api_contract>.
2. QA testing standards inside <qa_testing_guidelines>.
3. Historical defects inside <historical_regression_bugs>.

### Core Quality Rules:
1. **Contract Grounding:** Every test case MUST strictly adhere to the schemas, parameters, and status codes declared in <ground_truth_api_contract>. DO NOT invent undocumented routes, query parameters, or arbitrary headers.
2. **Category Coverage:** Generate test cases across the requested categories:
   - `positive`: Valid happy-path requests meeting all contract schema requirements (expected 200, 201, 204).
   - `negative`: Intentionally malformed or incomplete requests testing contract validation and error handling (expected 400, 422, 404).
   - `boundary`: Minimum/maximum field lengths, numeric limits, zero values, or collection boundaries.
   - `security`: Authentication omissions (missing Bearer token), unauthorized access, or privilege elevation tests (expected 401, 403).
   - `regression`: Specifically reproduces or guards against bugs documented in <historical_regression_bugs>.
3. **Traceability:** Populate `source_references` for each test case with the specific guideline title, bug report ID, or contract section that motivated the test.
4. **Ambiguity Flagging:** If a scenario tests an undocumented edge case where the expected status code is an educated inference rather than an explicit OpenAPI contract response, mark `requires_review: true`.
5. **Output Format:** You MUST respond with ONLY a valid, parseable JSON object matching this exact schema:
{
  "test_cases": [
    {
      "test_id_code": "TC-METHOD-SLUG-001",
      "name": "Short descriptive test title",
      "description": "Comprehensive explanation of intent, preconditions, and expected behavior",
      "category": "positive",
      "priority": "critical",
      "request_headers": {"Authorization": "Bearer {{TOKEN}}", "Content-Type": "application/json"},
      "path_params": {},
      "query_params": {},
      "request_body": {},
      "expected_status": 200,
      "expected_response_checks": {"check_field": "value"},
      "source_references": ["QA Guideline - Boundary Rules"],
      "requires_review": false
    }
  ]
}

DO NOT include markdown fences, comments, or preamble. Return ONLY the JSON object.
"""


def build_generation_user_prompt(
    endpoint_path: str,
    method: str,
    summary: str,
    parameters_schema: List[Dict[str, Any]],
    request_body_schema: Dict[str, Any],
    responses_schema: Dict[str, Any],
    auth_required: bool,
    rag_context: str,
    testing_objective: str,
    categories: List[str],
) -> str:
    """Build the structured user prompt containing endpoint metadata and RAG context."""
    endpoint_spec_summary = {
        "path": endpoint_path,
        "method": method.upper(),
        "summary": summary,
        "auth_required": auth_required,
        "parameters": parameters_schema or [],
        "request_body_schema": request_body_schema or {},
        "declared_responses": responses_schema or {},
    }

    categories_list = ", ".join(categories)

    sections = [
        f"### Target Endpoint Information:\n"
        f"HTTP Method: {method.upper()}\n"
        f"Path: {endpoint_path}\n"
        f"Summary: {summary}\n"
        f"Authentication Required: {auth_required}\n",
        f"### Endpoint Contract Details:\n"
        f"```json\n{json.dumps(endpoint_spec_summary, indent=2)}\n```\n",
    ]

    if rag_context.strip():
        sections.append(f"### Retrieved Grounding Context:\n{rag_context}\n")

    sections.append(
        f"### Test Generation Objective:\n"
        f"{testing_objective}\n\n"
        f"Generate declarative test cases covering the following categories: [{categories_list}].\n"
        f"Ensure every test is valid JSON and strictly conforms to the requested schema."
    )

    return "\n".join(sections)


def build_repair_user_prompt(
    raw_response: str,
    validation_errors: List[str],
    endpoint_path: str,
    method: str,
) -> str:
    """
    Construct a self-repair feedback prompt when the LLM generates
    malformed JSON or test cases failing contract validation.
    """
    errors_formatted = "\n".join([f"- {err}" for err in validation_errors])

    return f"""The previous response for endpoint {method.upper()} {endpoint_path} failed validation checks:

### Validation Failures:
{errors_formatted}

### Previous Output (Excerpt):
```
{raw_response[:1000]}
```

### Self-Repair Instructions:
1. Fix all schema and validation errors identified above.
2. Ensure the response is valid, parseable JSON with the top-level key "test_cases".
3. Verify that all required fields (`test_id_code`, `name`, `description`, `category`, `expected_status`) are present and valid.
4. Return ONLY the raw JSON object without markdown fences or additional text.
"""
