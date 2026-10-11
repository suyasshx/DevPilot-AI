"""
DevPilot AI - Pydantic Data Models for Sample Target API.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field, EmailStr


# ==========================================
# Auth Models
# ==========================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, examples=["testuser"])
    password: str = Field(..., min_length=1, examples=["SecretPass123!"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


# ==========================================
# User Models
# ==========================================
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, examples=["qa_tester"])
    email: EmailStr = Field(..., examples=["qa_tester@devpilot.internal"])
    password: str = Field(..., min_length=6, examples=["ValidPass123!"])
    role: str = Field(default="user", pattern="^(user|admin|auditor)$")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: str


# ==========================================
# Product Models
# ==========================================
class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    price: float = Field(..., ge=0.0)
    stock: int = Field(..., ge=0)
    description: Optional[str] = None


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductResponse]
    skip: int
    limit: int


# ==========================================
# Order Models
# ==========================================
class OrderItem(BaseModel):
    product_id: int = Field(..., ge=1, examples=[1])
    quantity: int = Field(..., examples=[2])  # Validation of >= 1 handled in business logic / defect switch


class OrderCreate(BaseModel):
    items: List[OrderItem] = Field(..., min_length=1)
    shipping_address: str = Field(..., min_length=5, examples=["100 Quality Way, Suite 400"])
    payment_method: str = Field(default="credit_card", pattern="^(credit_card|debit_card|paypal)$")


class OrderItemResponse(BaseModel):
    product_id: int
    product_name: str
    unit_price: float
    quantity: int
    subtotal: float


class OrderResponse(BaseModel):
    id: int
    user_id: int
    items: List[OrderItemResponse]
    total_amount: float
    status: str
    shipping_address: str
    created_at: str


# ==========================================
# Admin & Defect Models
# ==========================================
class DefectToggleRequest(BaseModel):
    defect_name: str
    enabled: bool


class DefectStatusResponse(BaseModel):
    defects: Dict[str, bool]


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
