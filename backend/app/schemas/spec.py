"""
DevPilot AI - OpenAPI Specification and Endpoint Schemas.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ApiEndpointResponse(BaseModel):
    id: str
    spec_id: str
    path: str
    method: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters_schema: List[Dict[str, Any]] = Field(default_factory=list)
    request_body_schema: Dict[str, Any] = Field(default_factory=dict)
    responses_schema: Dict[str, Any] = Field(default_factory=dict)
    auth_required: bool = False
    tags: List[str] = Field(default_factory=list)
    created_at: datetime

    class Config:
        from_attributes = True


class ApiSpecificationResponse(BaseModel):
    id: str
    project_id: str
    title: str
    version: str
    spec_format: str
    checksum_sha256: str
    is_active: bool
    endpoints_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class SpecUploadResponse(BaseModel):
    specification: ApiSpecificationResponse
    endpoints: List[ApiEndpointResponse]
    message: str
