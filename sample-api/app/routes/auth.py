"""
DevPilot AI - Authentication Route: POST /auth/login
"""

from fastapi import APIRouter, HTTPException, status
from ..models import LoginRequest, TokenResponse, ErrorResponse
from ..database import db
from ..auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Account inactive"},
        422: {"description": "Validation error"},
    },
    summary="Authenticate user and issue JWT bearer token",
)
def login(payload: LoginRequest) -> TokenResponse:
    """
    Authenticate user with username and password.
    Returns a signed JWT bearer token and basic profile metadata.
    """
    matched_user = None
    for user in db.users.values():
        if user["username"] == payload.username:
            matched_user = user
            break

    if not matched_user or matched_user["password"] != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not matched_user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    token = create_access_token(
        data={
            "sub": str(matched_user["id"]),
            "username": matched_user["username"],
            "role": matched_user["role"],
        }
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=matched_user["id"],
        username=matched_user["username"],
        role=matched_user["role"],
    )
