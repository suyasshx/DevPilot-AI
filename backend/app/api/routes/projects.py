"""
DevPilot AI - Projects API Router.
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from ...db.session import get_db
from ...services.spec_service import spec_service
from ...schemas.project import ProjectCreate, ProjectResponse
from ...models.project import Project
from ..dependencies import get_project_or_404

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or retrieve project",
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project workspace or return existing one by slug."""
    project = await spec_service.create_project(
        db=db,
        name=payload.name,
        description=payload.description,
    )
    return ProjectResponse.model_validate(project)


@router.get(
    "",
    response_model=List[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List all projects",
)
async def list_projects(
    db: AsyncSession = Depends(get_db),
) -> List[ProjectResponse]:
    """Retrieve all registered projects ordered by creation date."""
    projects = await spec_service.list_projects(db)
    return [ProjectResponse.model_validate(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project details",
)
async def get_project(
    project: Project = Depends(get_project_or_404),
) -> ProjectResponse:
    """Retrieve details for a specific project."""
    return ProjectResponse.model_validate(project)
