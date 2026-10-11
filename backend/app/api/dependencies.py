"""
DevPilot AI - API Dependencies.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from ..db.session import get_db
from ..services.spec_service import spec_service
from ..models.project import Project


async def get_project_or_404(
    project_id: str,
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Dependency verifying project existence."""
    project = await spec_service.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found.",
        )
    return project
