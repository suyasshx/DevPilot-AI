"""
DevPilot AI - Test Generation and Test Case Management API Routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ...db.session import get_db
from ...models.project import Project
from ...models.test_case import TestCase
from ...schemas.test_case import (
    TestGenerationRequest,
    GenerationSessionResponse,
    TestCaseResponse,
    TestCaseUpdateRequest,
)
from ...services.generation_service import generation_service, GenerationServiceError

router = APIRouter(prefix="/projects/{project_id}", tags=["Test Generation & Test Cases"])


@router.post(
    "/generation/generate",
    response_model=GenerationSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate declarative test cases for an endpoint using contract RAG",
)
async def generate_test_cases(
    project_id: str,
    request: TestGenerationRequest,
    db: AsyncSession = Depends(get_db),
) -> GenerationSessionResponse:
    """
    Generate contract-grounded automated test cases for an endpoint.
    Performs RAG retrieval, LLM generation, Pydantic validation with self-repair,
    OpenAPI contract validation, deduplication, and database persistence.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")

    try:
        session_result = await generation_service.generate_test_cases(
            db=db,
            request=request,
        )
        return session_result
    except GenerationServiceError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test generation failed: {str(err)}",
        )


@router.get(
    "/test-cases",
    response_model=List[TestCaseResponse],
    summary="List all generated test cases for a project",
)
async def list_test_cases(
    project_id: str,
    endpoint_id: Optional[str] = Query(None, description="Filter by API endpoint UUID"),
    category: Optional[str] = Query(None, description="Filter by category (positive, negative, etc.)"),
    is_approved: Optional[bool] = Query(None, description="Filter by approval status"),
    requires_review: Optional[bool] = Query(None, description="Filter by review requirement"),
    is_active: bool = Query(True, description="Filter active test cases"),
    db: AsyncSession = Depends(get_db),
) -> List[TestCaseResponse]:
    """Retrieve test cases for a project with optional filtering."""
    query = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.is_active == is_active,
    )

    if endpoint_id:
        query = query.where(TestCase.endpoint_id == endpoint_id)
    if category:
        query = query.where(TestCase.category == category)
    if is_approved is not None:
        query = query.where(TestCase.is_approved == is_approved)
    if requires_review is not None:
        query = query.where(TestCase.requires_review == requires_review)

    query = query.order_by(TestCase.created_at.desc())
    result = await db.execute(query)
    test_cases = result.scalars().all()
    return [TestCaseResponse.model_validate(tc) for tc in test_cases]


@router.get(
    "/test-cases/{test_id}",
    response_model=TestCaseResponse,
    summary="Get single test case details",
)
async def get_test_case(
    project_id: str,
    test_id: str,
    db: AsyncSession = Depends(get_db),
) -> TestCaseResponse:
    """Retrieve details for a specific test case."""
    test_case = await db.get(TestCase, test_id)
    if not test_case or test_case.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found.")
    return TestCaseResponse.model_validate(test_case)


@router.patch(
    "/test-cases/{test_id}",
    response_model=TestCaseResponse,
    summary="Update or approve a test case",
)
async def update_test_case(
    project_id: str,
    test_id: str,
    payload: TestCaseUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> TestCaseResponse:
    """
    Update test case parameters, approve/reject test case, or modify review status.
    """
    test_case = await db.get(TestCase, test_id)
    if not test_case or test_case.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(test_case, field_name, value)

    await db.commit()
    await db.refresh(test_case)
    return TestCaseResponse.model_validate(test_case)


@router.delete(
    "/test-cases/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a test case",
)
async def delete_test_case(
    project_id: str,
    test_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a test case by marking is_active = False."""
    test_case = await db.get(TestCase, test_id)
    if not test_case or test_case.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found.")

    test_case.is_active = False
    await db.commit()
