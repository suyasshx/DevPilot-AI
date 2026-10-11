"""
DevPilot AI - Product Catalog Route: GET /products
"""

from typing import Optional, List, Any
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse
from ..models import ProductListResponse, ProductResponse
from ..database import db
from ..defects import defect_manager

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=ProductListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        422: {"description": "Validation error (invalid pagination limits)"},
    },
    summary="List products with pagination and category filtering",
)
def list_products(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., 'hardware', 'audio')"),
) -> Any:
    """Fetch paginated product catalog with optional category filtering."""
    filtered = list(db.products.values())
    if category:
        filtered = [p for p in filtered if p["category"].lower() == category.lower()]

    total = len(filtered)
    paginated = filtered[skip : skip + limit]

    # Defect injection trigger: schema contract break
    if defect_manager.is_enabled("broken_schema_on_products"):
        # Intentionally break the contract by corrupting the price field data type
        corrupted_items = []
        for p in paginated:
            item_copy = dict(p)
            item_copy["price"] = "CORRUPTED_STRING_VALUE_INSTEAD_OF_FLOAT"
            corrupted_items.append(item_copy)
        return JSONResponse(
            status_code=200,
            content={
                "total": total,
                "items": corrupted_items,
                "skip": skip,
                "limit": limit,
            },
        )

    items = [ProductResponse(**p) for p in paginated]
    return ProductListResponse(total=total, items=items, skip=skip, limit=limit)
