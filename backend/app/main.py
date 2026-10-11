"""
DevPilot AI - Backend Main Application Entrypoint.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .db.session import init_db
from .api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing startup database initialization."""
    # Auto-initialize database tables on startup
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "DevPilot AI: RAG-Powered AI-Assisted Test Automation Platform. "
        "Provides contract-grounded test generation, deterministic test validation, "
        "automated execution, and 5-way failure taxonomy classification."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
def root() -> dict:
    """Root metadata probe."""
    return {
        "service": settings.PROJECT_NAME,
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health() -> dict:
    """Service health probe."""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
    }
