"""
DevPilot AI - Primary API Router Aggregator.
"""

from fastapi import APIRouter
from .routes import projects, specs

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(specs.router)
