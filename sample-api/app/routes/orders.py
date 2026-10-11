"""
DevPilot AI - Order Processing Route: POST /orders
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from ..models import OrderCreate, OrderResponse, OrderItemResponse, ErrorResponse
from ..database import db
from ..auth import get_current_user
from ..defects import defect_manager

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Business validation failed (out of stock, invalid product)"},
        401: {"model": ErrorResponse, "description": "Unauthorized - Missing or invalid Bearer token"},
        422: {"description": "Request body validation failed"},
    },
    summary="Create a new order for authenticated user",
)
def create_order(
    payload: OrderCreate,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> OrderResponse:
    """
    Process an order creation request.
    Verifies authentication, stock availability, and creates order record.
    """
    # Defect injection trigger: Authentication bypass
    if defect_manager.is_enabled("auth_bypass_on_orders"):
        user_id = 1  # Fallback to default user without checking token
    else:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing Bearer authentication token",
            )
        user_id = current_user["id"]

    allow_negative = defect_manager.is_enabled("negative_quantity_allowed")

    order_items = []
    total_amount = 0.0

    for item in payload.items:
        # Check quantity boundary
        if not allow_negative and item.quantity < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid quantity {item.quantity} for product {item.product_id}. Must be >= 1",
            )

        product = db.products.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {item.product_id} does not exist",
            )

        # Check stock (only when not in negative defect mode)
        if not allow_negative and product["stock"] < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{product['name']}'. Available: {product['stock']}, Requested: {item.quantity}",
            )

        subtotal = round(product["price"] * item.quantity, 2)
        total_amount += subtotal

        # Deduct stock
        if not allow_negative:
            product["stock"] -= item.quantity

        order_items.append(
            OrderItemResponse(
                product_id=product["id"],
                product_name=product["name"],
                unit_price=product["price"],
                quantity=item.quantity,
                subtotal=subtotal,
            )
        )

    new_order_id = db.next_order_id()
    created_at = datetime.now(timezone.utc).isoformat()
    order_record = {
        "id": new_order_id,
        "user_id": user_id,
        "items": [i.model_dump() for i in order_items],
        "total_amount": round(total_amount, 2),
        "status": "pending",
        "shipping_address": payload.shipping_address,
        "created_at": created_at,
    }
    db.orders[new_order_id] = order_record

    return OrderResponse(
        id=new_order_id,
        user_id=user_id,
        items=order_items,
        total_amount=round(total_amount, 2),
        status="pending",
        shipping_address=payload.shipping_address,
        created_at=created_at,
    )
