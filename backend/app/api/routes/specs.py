"""
DevPilot AI - OpenAPI Specification and Endpoint Routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.session import get_db
from ...services.spec_service import spec_service
from ...schemas.spec import (
    ApiSpecificationResponse,
    ApiEndpointResponse,
    SpecUploadResponse,
)
from ...ingestion.openapi_parser import OpenAPIValidationError
from ...models.project import Project
from ..dependencies import get_project_or_404
from ...core.config import settings

router = APIRouter(prefix="/projects/{project_id}", tags=["API Specifications"])


@router.post(
    "/specs/upload",
    response_model=SpecUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest OpenAPI specification (JSON or YAML)",
)
async def upload_specification(
    file: UploadFile = File(...),
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> SpecUploadResponse:
    """
    Upload an OpenAPI 3.0/3.1 JSON or YAML specification.
    Validates structure, dereferences internal components, extracts endpoints, and persists metadata.
    """
    content_bytes = await file.read()
    if len(content_bytes) > settings.MAX_SPEC_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_SPEC_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
        )

    try:
        raw_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content must be valid UTF-8 text.",
        )

    try:
        spec, endpoints = await spec_service.ingest_specification(
            db=db,
            project_id=project.id,
            raw_content=raw_text,
        )
    except OpenAPIValidationError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"OpenAPI validation error: {str(val_err)}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal specification ingestion error: {str(exc)}",
        )

    spec_resp = ApiSpecificationResponse(
        id=spec.id,
        project_id=spec.project_id,
        title=spec.title,
        version=spec.version,
        spec_format=spec.spec_format,
        checksum_sha256=spec.checksum_sha256,
        is_active=spec.is_active,
        endpoints_count=len(endpoints),
        created_at=spec.created_at,
    )
    endpoint_resps = [ApiEndpointResponse.model_validate(ep) for ep in endpoints]

    return SpecUploadResponse(
        specification=spec_resp,
        endpoints=endpoint_resps,
        message=f"Successfully ingested specification '{spec.title}' with {len(endpoints)} endpoints.",
    )


@router.get(
    "/specs",
    response_model=List[ApiSpecificationResponse],
    status_code=status.HTTP_200_OK,
    summary="List specifications for a project",
)
async def list_specifications(
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> List[ApiSpecificationResponse]:
    """Retrieve all uploaded specifications with endpoint counts for the project."""
    specs_with_counts = await spec_service.list_specifications(db, project.id)
    responses = []
    for spec, count in specs_with_counts:
        responses.append(
            ApiSpecificationResponse(
                id=spec.id,
                project_id=spec.project_id,
                title=spec.title,
                version=spec.version,
                spec_format=spec.spec_format,
                checksum_sha256=spec.checksum_sha256,
                is_active=spec.is_active,
                endpoints_count=count,
                created_at=spec.created_at,
            )
        )
    return responses


@router.get(
    "/endpoints",
    response_model=List[ApiEndpointResponse],
    status_code=status.HTTP_200_OK,
    summary="List extracted endpoints with filters",
)
async def list_endpoints(
    spec_id: Optional[str] = Query(None, description="Filter by specification ID"),
    path: Optional[str] = Query(None, description="Substring search on endpoint path"),
    method: Optional[str] = Query(None, description="HTTP method filter: GET, POST, etc."),
    tag: Optional[str] = Query(None, description="Tag filter, e.g. Authentication, Orders"),
    project: Project = Depends(get_project_or_404),
    db: AsyncSession = Depends(get_db),
) -> List[ApiEndpointResponse]:
    """Query all parsed endpoints for this project with optional metadata filtering."""
    endpoints = await spec_service.list_endpoints(
        db=db,
        project_id=project.id,
        spec_id=spec_id,
        path_pattern=path,
        method=method,
        tag=tag,
    )
    return [ApiEndpointResponse.model_validate(ep) for ep in endpoints]
