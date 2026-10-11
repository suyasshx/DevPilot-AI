"""
DevPilot AI - Structured Tools Layer for Autonomous QA Agents.
Provides strictly typed tool interfaces callable by LangGraph nodes or LLM function calling.
"""

import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.spec import ApiEndpoint, ApiSpecification
from ..models.execution import TestRun, TestResult, ExecutionLog
from ..models.evaluation import TestEvaluation
from ..models.test_case import TestCase
from ..schemas.test_case import GeneratedTestCaseItem
from ..rag.retriever import rag_retriever
from ..validation.contract_validator import ContractValidator
from ..llm.mock_provider import MockLLMProvider
from ..llm.factory import get_llm_provider
from ..llm.prompts import SYSTEM_PROMPT, build_generation_user_prompt
from .executor import TestHarnessExecutor, ExecutionResultItem
from .classifier import FailureTaxonomyClassifier, FailureClassification
from ..db.base import utc_now


async def search_qa_knowledge(
    db: AsyncSession,
    project_id: str,
    endpoint_path: str,
    method: str,
    testing_objective: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Retrieve grounded QA guidelines and bug reports via semantic RAG search."""
    context = await rag_retriever.retrieve_context(
        db=db,
        project_id=project_id,
        endpoint_path=endpoint_path,
        method=method,
        testing_objective=testing_objective,
        top_k=top_k,
    )
    return {
        "prompt_context": context.prompt_context,
        "source_references": context.source_references,
        "retrieved_count": len(context.retrieved_chunks),
    }


async def get_api_schema(
    db: AsyncSession,
    endpoint_id: str,
) -> Dict[str, Any]:
    """Retrieve OpenAPI specification contract details for target endpoint."""
    endpoint = await db.get(ApiEndpoint, endpoint_id)
    if not endpoint:
        raise ValueError(f"Endpoint '{endpoint_id}' not found.")

    spec = await db.get(ApiSpecification, endpoint.spec_id)
    project_id = spec.project_id if spec else ""

    return {
        "id": endpoint.id,
        "project_id": project_id,
        "spec_id": endpoint.spec_id,
        "path": endpoint.path,
        "method": endpoint.method,
        "summary": endpoint.summary or "",
        "parameters_schema": endpoint.parameters_schema or [],
        "request_body_schema": endpoint.request_body_schema or {},
        "responses_schema": endpoint.responses_schema or {},
        "auth_required": endpoint.auth_required,
        "tags": endpoint.tags or [],
    }


async def generate_test_cases(
    endpoint_meta: Dict[str, Any],
    rag_context: str,
    objective: str,
    categories: List[str],
    provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Synthesize declarative test cases using LLM or contract-grounded mock."""
    active_provider = provider or get_llm_provider(force_mock=True)

    user_prompt = build_generation_user_prompt(
        endpoint_path=endpoint_meta["path"],
        method=endpoint_meta["method"],
        summary=endpoint_meta.get("summary", ""),
        parameters_schema=endpoint_meta.get("parameters_schema", []),
        request_body_schema=endpoint_meta.get("request_body_schema", {}),
        responses_schema=endpoint_meta.get("responses_schema", {}),
        auth_required=endpoint_meta.get("auth_required", False),
        rag_context=rag_context,
        testing_objective=objective,
        categories=categories,
    )

    response = await active_provider.generate_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_format_json=True,
    )

    import json
    parsed = json.loads(response.raw_text)
    raw_cases = parsed.get("test_cases", [])

    return {
        "raw_test_cases": raw_cases,
        "model_used": response.model_name,
        "total_generated": len(raw_cases),
    }


def validate_test_cases(
    raw_test_cases: List[Dict[str, Any]],
    endpoint_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """Validate declarative test cases against OpenAPI contract."""
    # Build synthetic ApiEndpoint for validator
    synthetic_endpoint = ApiEndpoint(
        id=endpoint_meta.get("id", "temp-id"),
        spec_id=endpoint_meta.get("spec_id", "temp-spec"),
        path=endpoint_meta["path"],
        method=endpoint_meta["method"],
        summary=endpoint_meta.get("summary"),
        parameters_schema=endpoint_meta.get("parameters_schema", []),
        request_body_schema=endpoint_meta.get("request_body_schema", {}),
        responses_schema=endpoint_meta.get("responses_schema", {}),
        auth_required=endpoint_meta.get("auth_required", False),
    )

    validator = ContractValidator()
    valid_cases: List[GeneratedTestCaseItem] = []
    validation_failures: List[Dict[str, Any]] = []

    for item in raw_test_cases:
        try:
            tc = GeneratedTestCaseItem(**item)
            outcome = validator.validate_test_case(tc, synthetic_endpoint)
            if outcome.is_valid:
                if outcome.requires_review:
                    tc.requires_review = True
                valid_cases.append(tc)
            else:
                validation_failures.append({
                    "test_id_code": tc.test_id_code,
                    "errors": outcome.errors,
                    "warnings": outcome.warnings,
                })
        except Exception as p_err:
            validation_failures.append({
                "test_id_code": item.get("test_id_code", "UNKNOWN"),
                "errors": [f"Schema parse error: {str(p_err)}"],
                "warnings": [],
            })

    return {
        "is_all_valid": len(validation_failures) == 0,
        "valid_cases": [vc.model_dump() for vc in valid_cases],
        "validation_failures": validation_failures,
        "valid_count": len(valid_cases),
        "invalid_count": len(validation_failures),
    }


async def execute_test_cases(
    endpoint_path: str,
    method: str,
    valid_test_cases: List[Dict[str, Any]],
    target_base_url: str,
    auth_token: Optional[str] = None,
) -> List[ExecutionResultItem]:
    """Execute test cases via isolated HTTPX test harness."""
    executor = TestHarnessExecutor(base_url=target_base_url)
    results: List[ExecutionResultItem] = []

    for tc_dict in valid_test_cases:
        tc_item = GeneratedTestCaseItem(**tc_dict)
        res = await executor.execute_test(
            endpoint_path=endpoint_path,
            http_method=method,
            test_case=tc_item,
            auth_token_override=auth_token,
        )
        results.append(res)

    return results


def classify_test_failure(
    expected_status: int,
    actual_status: Optional[int],
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    response_body: Optional[Any] = None,
) -> FailureClassification:
    """Classify execution outcome into the 5-way taxonomy."""
    return FailureTaxonomyClassifier.classify(
        expected_status=expected_status,
        actual_status=actual_status,
        response_body=response_body,
        error_type=error_type,
        error_message=error_message,
    )
