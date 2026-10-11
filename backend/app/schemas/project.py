"""
DevPilot AI - Project Schemas.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, examples=["EA Sports E-Commerce Core"])
    description: Optional[str] = Field(default=None, max_length=1000)


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
