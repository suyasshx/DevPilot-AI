"""
DevPilot AI - Test Case Generation and Orchestration Service.
Coordinates RAG context retrieval, prompt formatting, LLM generation,
Pydantic parsing, self-repair retries, contract validation, and database persistence.
"""

import json
import logging
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.spec import ApiEndpoint
from ..models.test_case import TestCase
from ..schemas.test_case import (
    GeneratedTestCaseItem,
    TestGenerationRequest,
    TestCaseResponse,
    GenerationSessionResponse,
)
from ..rag.retriever import rag_retriever, RAGRetriever
from ..llm.base import BaseLLMProvider
from ..llm.factory import get_llm_provider
from ..llm.prompts import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_generation_user_prompt,
    build_repair_user_prompt,
)
from ..validation.contract_validator import ContractValidator
from ..validation.deduplicator import TestCaseDeduplicator
from ..core.config import settings

logger = logging.getLogger(__name__)


class GenerationServiceError(Exception):
    """Exception raised when test case generation encounters a critical failure."""
    pass


class TestGenerationService:
    """End-to-end service orchestrating contract-grounded automated test generation."""

    def __init__(
        self,
        retriever: Optional[RAGRetriever] = None,
        validator: Optional[ContractValidator] = None,
    ) -> None:
        self.retriever = retriever or rag_retriever
        self.validator = validator or ContractValidator()

    async def generate_test_cases(
        self,
        db: AsyncSession,
        request: TestGenerationRequest,
        llm_provider: Optional[BaseLLMProvider] = None,
        force_mock: bool = False,
    ) -> GenerationSessionResponse:
        """
        Execute full multi-turn test case generation workflow:
        1. Fetch endpoint metadata.
        2. Retrieve RAG grounding knowledge.
        3. Call LLM provider.
        4. Validate with Pydantic & trigger self-repair on error.
        5. Validate against OpenAPI contract.
        6. Deduplicate against existing tests.
        7. Persist to database.
        """
        # 1. Fetch Target Endpoint
        endpoint = await db.get(ApiEndpoint, request.endpoint_id)
        if not endpoint:
            raise GenerationServiceError(f"Endpoint with ID '{request.endpoint_id}' not found.")

        # 2. Retrieve Grounding Knowledge via RAG
        context = await self.retriever.retrieve_context(
            db=db,
            project_id=endpoint.project_id,
            endpoint_path=endpoint.path,
            method=endpoint.method,
            testing_objective=request.testing_objective,
            top_k=5,
        )

        # 3. Initialize Provider
        provider = llm_provider or get_llm_provider(
            force_mock=force_mock,
            model_override=request.model_override,
        )

        # 4. Construct Initial Prompts
        user_prompt = build_generation_user_prompt(
            endpoint_path=endpoint.path,
            method=endpoint.method,
            summary=endpoint.summary or "",
            parameters_schema=endpoint.parameters_schema or [],
            request_body_schema=endpoint.request_body_schema or {},
            responses_schema=endpoint.responses_schema or {},
            auth_required=endpoint.auth_required,
            rag_context=context.prompt_context,
            testing_objective=request.testing_objective,
            categories=request.categories,
        )

        # 5. LLM Call & Self-Repair Retry Turn Loop
        max_retries = settings.LLM_MAX_RETRIES
        current_user_prompt = user_prompt
        last_raw_response = ""
        validated_items: List[GeneratedTestCaseItem] = []
        parsing_attempts = 0

        for attempt in range(max_retries + 1):
            parsing_attempts += 1
            response = await provider.generate_completion(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=current_user_prompt,
                response_format_json=True,
            )
            last_raw_response = response.raw_text

            try:
                # Parse JSON
                # Handle possible markdown wrap in model output
                clean_json = response.raw_text.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.startswith("```"):
                    clean_json = clean_json[3:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()

                parsed_data = json.loads(clean_json)
                if not isinstance(parsed_data, dict) or "test_cases" not in parsed_data:
                    raise ValueError("JSON response must be an object containing a 'test_cases' list.")

                raw_cases = parsed_data["test_cases"]
                if not isinstance(raw_cases, list) or len(raw_cases) == 0:
                    raise ValueError("'test_cases' list is empty or not a valid list.")

                # Pydantic validation of each item
                current_items: List[GeneratedTestCaseItem] = []
                pydantic_errors = []
                for idx, item in enumerate(raw_cases):
                    try:
                        parsed_item = GeneratedTestCaseItem(**item)
                        # Filter by requested categories if requested
                        if parsed_item.category in request.categories:
                            current_items.append(parsed_item)
                    except Exception as pe:
                        pydantic_errors.append(f"Test case index {idx}: {str(pe)}")

                if pydantic_errors:
                    raise ValueError("Pydantic validation errors:\n" + "\n".join(pydantic_errors))

                if not current_items:
                    raise ValueError("No test cases matched the requested categories.")

                # Successfully parsed & Pydantic validated!
                validated_items = current_items
                break

            except Exception as err:
                logger.warning(
                    "LLM generation attempt %d failed parsing/validation: %s",
                    attempt + 1,
                    str(err),
                )
                if attempt < max_retries:
                    # Construct self-repair feedback prompt
                    current_user_prompt = build_repair_user_prompt(
                        raw_response=last_raw_response,
                        validation_errors=[str(err)],
                        endpoint_path=endpoint.path,
                        method=endpoint.method,
                    )
                    continue
                else:
                    raise GenerationServiceError(
                        f"Failed to generate valid test cases after {max_retries + 1} attempts. Last error: {str(err)}"
                    )

        # 6. Contract Validation Turn
        contract_valid_items: List[GeneratedTestCaseItem] = []
        validation_errors_summary: List[Dict[str, Any]] = []
        review_count = 0

        for tc in validated_items:
            outcome = self.validator.validate_test_case(tc, endpoint)
            if outcome.is_valid:
                if outcome.requires_review:
                    tc.requires_review = True
                    review_count += 1
                contract_valid_items.append(tc)
            else:
                validation_errors_summary.append({
                    "test_id_code": tc.test_id_code,
                    "errors": outcome.errors,
                    "warnings": outcome.warnings,
                })

        # 7. Deduplication Turn
        # Fetch existing active test cases for this endpoint
        existing_result = await db.execute(
            select(TestCase).where(
                TestCase.endpoint_id == endpoint.id,
                TestCase.is_active.is_(True),
            )
        )
        existing_tests = existing_result.scalars().all()
        existing_signatures: Set[str] = {
            TestCaseDeduplicator.compute_signature(
                endpoint_id=t.endpoint_id,
                http_method=endpoint.method,
                test_case=GeneratedTestCaseItem(
                    test_id_code=t.test_id_code,
                    name=t.name,
                    description=t.description or "",
                    category=t.category,
                    priority=t.priority,
                    request_headers=t.request_headers,
                    path_params=t.path_params,
                    query_params=t.query_params,
                    request_body=t.request_body,
                    expected_status=t.expected_status,
                    expected_response_checks=t.expected_response_checks,
                    source_references=t.source_references,
                    requires_review=t.requires_review,
                ),
            )
            for t in existing_tests
        }

        unique_tests, duplicate_count = TestCaseDeduplicator.deduplicate(
            test_cases=contract_valid_items,
            endpoint_id=endpoint.id,
            http_method=endpoint.method,
            existing_signatures=existing_signatures,
        )

        # 8. Database Persistence
        persisted_records: List[TestCase] = []
        for tc in unique_tests:
            # Associate RAG references if empty
            refs = tc.source_references if tc.source_references else context.source_references

            db_test = TestCase(
                project_id=endpoint.project_id,
                endpoint_id=endpoint.id,
                test_id_code=tc.test_id_code,
                name=tc.name,
                description=tc.description,
                category=tc.category,
                priority=tc.priority,
                request_headers=tc.request_headers,
                path_params=tc.path_params,
                query_params=tc.query_params,
                request_body=tc.request_body,
                expected_status=tc.expected_status,
                expected_response_checks=tc.expected_response_checks,
                source_references=refs,
                generation_model=provider.model_name,
                prompt_version=PROMPT_VERSION,
                requires_review=tc.requires_review,
                is_approved=not tc.requires_review,
                is_active=True,
            )
            db.add(db_test)
            persisted_records.append(db_test)

        await db.commit()
        for r in persisted_records:
            await db.refresh(r)

        # 9. Format Response Envelope
        response_models = [TestCaseResponse.model_validate(r) for r in persisted_records]

        return GenerationSessionResponse(
            project_id=endpoint.project_id,
            endpoint_id=endpoint.id,
            endpoint_path=endpoint.path,
            http_method=endpoint.method,
            model_used=provider.model_name,
            prompt_version=PROMPT_VERSION,
            retrieved_sources_count=len(context.source_references),
            generated_test_cases=response_models,
            validation_summary={
                "parsing_attempts": parsing_attempts,
                "raw_generated_count": len(validated_items),
                "contract_valid_count": len(contract_valid_items),
                "rejected_contract_count": len(validation_errors_summary),
                "suppressed_duplicates_count": duplicate_count,
                "persisted_count": len(persisted_records),
                "flagged_for_human_review": review_count,
                "contract_rejections": validation_errors_summary,
            },
        )


generation_service = TestGenerationService()
