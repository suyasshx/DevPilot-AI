"""
DevPilot AI - Specification and Endpoint Management Service.
Handles project management, specification upload, checksum deduplication, and endpoint queries.
"""

import re
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.project import Project
from ..models.spec import ApiSpecification, ApiEndpoint
from ..ingestion.openapi_parser import OpenAPIParser, ParsedSpecification


class SpecService:
    """Service handling project and specification persistence operations."""

    def __init__(self, parser: Optional[OpenAPIParser] = None) -> None:
        self.parser = parser or OpenAPIParser()

    @staticmethod
    def _slugify(text: str) -> str:
        """Create URL-safe slug from project name."""
        s = text.lower().strip()
        s = re.sub(r"[^\w\s-]", "", s)
        return re.sub(r"[-\s]+", "-", s)

    async def create_project(self, db: AsyncSession, name: str, description: Optional[str] = None) -> Project:
        """Create a new project or return existing project with identical slug."""
        slug = self._slugify(name)
        result = await db.execute(select(Project).where(Project.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        project = Project(name=name, slug=slug, description=description)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def list_projects(self, db: AsyncSession) -> List[Project]:
        """List all registered projects."""
        result = await db.execute(select(Project).order_by(Project.created_at.desc()))
        return list(result.scalars().all())

    async def get_project(self, db: AsyncSession, project_id: str) -> Optional[Project]:
        """Get project by UUID."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def ingest_specification(
        self,
        db: AsyncSession,
        project_id: str,
        raw_content: str,
    ) -> Tuple[ApiSpecification, List[ApiEndpoint]]:
        """
        Parse raw OpenAPI content, check for deduplication, and store specification + endpoints.
        """
        # 1. Parse and validate specification
        parsed: ParsedSpecification = self.parser.parse(raw_content)

        # 2. Check if identical checksum already exists for this project
        result = await db.execute(
            select(ApiSpecification).where(
                ApiSpecification.project_id == project_id,
                ApiSpecification.checksum_sha256 == parsed.checksum_sha256,
            )
        )
        existing_spec = result.scalar_one_or_none()
        if existing_spec:
            # Return existing spec with its endpoints
            endpoints_res = await db.execute(
                select(ApiEndpoint).where(ApiEndpoint.spec_id == existing_spec.id)
            )
            return existing_spec, list(endpoints_res.scalars().all())

        # 3. Create ApiSpecification entity
        spec_entity = ApiSpecification(
            project_id=project_id,
            title=parsed.title,
            version=parsed.version,
            raw_content=parsed.raw_content,
            spec_format=parsed.spec_format,
            checksum_sha256=parsed.checksum_sha256,
            is_active=True,
        )
        db.add(spec_entity)
        await db.flush()  # Generate spec_entity.id for foreign keys

        # 4. Create ApiEndpoint entities
        endpoint_entities: List[ApiEndpoint] = []
        for ep in parsed.endpoints:
            ep_model = ApiEndpoint(
                spec_id=spec_entity.id,
                path=ep.path,
                method=ep.method,
                summary=ep.summary,
                description=ep.description,
                parameters_schema=ep.parameters,
                request_body_schema=ep.request_body_schema,
                responses_schema=ep.responses_schema,
                auth_required=ep.auth_required,
                tags=ep.tags,
            )
            db.add(ep_model)
            endpoint_entities.append(ep_model)

        await db.commit()
        await db.refresh(spec_entity)
        for ep in endpoint_entities:
            await db.refresh(ep)

        return spec_entity, endpoint_entities

    async def list_specifications(self, db: AsyncSession, project_id: str) -> List[Tuple[ApiSpecification, int]]:
        """List specifications for a project with their endpoint count."""
        stmt = (
            select(ApiSpecification, func.count(ApiEndpoint.id).label("endpoint_count"))
            .outerjoin(ApiEndpoint, ApiSpecification.id == ApiEndpoint.spec_id)
            .where(ApiSpecification.project_id == project_id)
            .group_by(ApiSpecification.id)
            .order_by(ApiSpecification.created_at.desc())
        )
        result = await db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def list_endpoints(
        self,
        db: AsyncSession,
        project_id: str,
        spec_id: Optional[str] = None,
        path_pattern: Optional[str] = None,
        method: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[ApiEndpoint]:
        """Query endpoints across a project with optional filters."""
        query = (
            select(ApiEndpoint)
            .join(ApiSpecification, ApiEndpoint.spec_id == ApiSpecification.id)
            .where(ApiSpecification.project_id == project_id)
        )

        if spec_id:
            query = query.where(ApiEndpoint.spec_id == spec_id)
        if method:
            query = query.where(ApiEndpoint.method == method.upper())
        if path_pattern:
            query = query.where(ApiEndpoint.path.like(f"%{path_pattern}%"))

        query = query.order_by(ApiEndpoint.path.asc(), ApiEndpoint.method.asc())
        result = await db.execute(query)
        endpoints = list(result.scalars().all())

        if tag:
            tag_lower = tag.lower()
            endpoints = [ep for ep in endpoints if any(t.lower() == tag_lower for t in ep.tags)]

        return endpoints


spec_service = SpecService()
