"""
DevPilot AI - User Management Routes: POST /users, GET /users/{user_id}
"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Path
from ..models import UserCreate, UserResponse, ErrorResponse
from ..database import db
from ..defects import defect_manager

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Duplicate username or email"},
        422: {"description": "Validation error"},
    },
    summary="Create a new user account",
)
def create_user(payload: UserCreate) -> UserResponse:
    """Register a new user in the system."""
    for user in db.users.values():
        if user["username"].lower() == payload.username.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{payload.username}' is already taken",
            )
        if user["email"].lower() == payload.email.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' is already registered",
            )

    new_id = db.next_user_id()
    new_user = {
        "id": new_id,
        "username": payload.username,
        "email": payload.email,
        "password": payload.password,
        "role": payload.role,
        "is_active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.users[new_id] = new_user

    return UserResponse(
        id=new_user["id"],
        username=new_user["username"],
        email=new_user["email"],
        role=new_user["role"],
        is_active=new_user["is_active"],
        created_at=new_user["created_at"],
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "User not found"},
        422: {"description": "Invalid user ID format"},
        500: {"model": ErrorResponse, "description": "Internal server crash (demonstrated when defect active)"},
    },
    summary="Retrieve user profile by ID",
)
def get_user_by_id(
    user_id: int = Path(..., ge=1, description="Unique positive integer user ID")
) -> UserResponse:
    """Fetch user details by their ID."""
    user = db.users.get(user_id)

    # Defect injection trigger: unhandled 500 when user not found
    if not user:
        if defect_manager.is_enabled("unhandled_500_on_user_not_found"):
            # Intentionally unhandled exception simulating server crash
            raise RuntimeError(
                f"[SIMULATED_DEFECT] NullPointerError in UserService.get_user({user_id}): User entity pointer is null"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
    )
