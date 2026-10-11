"""
DevPilot AI - Sample Target E-Commerce API Main Application.
"""

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from .routes import (
    auth as auth_routes,
    users as users_routes,
    products as products_routes,
    orders as orders_routes,
    admin as admin_routes,
)

app = FastAPI(
    title="DevPilot AI Sample E-Commerce Target API",
    description=(
        "Production-style target API simulating an EA gaming e-commerce platform. "
        "Provides realistic authentication, user profiles, inventory catalog, "
        "order processing, and configurable defect injection hooks for test automation evaluation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_routes.router)
app.include_router(users_routes.router)
app.include_router(products_routes.router)
app.include_router(orders_routes.router)
app.include_router(admin_routes.router)


@app.get("/", status_code=status.HTTP_200_OK, tags=["System"])
def root() -> dict:
    """Root metadata endpoint."""
    return {
        "service": "DevPilot AI Sample Target API",
        "status": "healthy",
        "version": "1.0.0",
        "documentation": "/docs",
        "openapi_spec": "/openapi.json",
    }


@app.get("/health", status_code=status.HTTP_200_OK, tags=["System"])
def health_check() -> dict:
    """Health check endpoint for container probes and test harness readiness."""
    return {
        "status": "healthy",
        "uptime": "operational",
    }
