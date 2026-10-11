"""
DevPilot AI - Admin & Test Environment Control Routes.
Allows the test automation harness to reset data and toggle intentional defects.
"""

from fastapi import APIRouter, HTTPException, status
from ..models import DefectToggleRequest, DefectStatusResponse
from ..defects import defect_manager
from ..database import db

router = APIRouter(prefix="/admin", tags=["Admin & Test Automation Control"])


@router.get("/defects", response_model=DefectStatusResponse, summary="Inspect defect toggles")
def get_defects() -> DefectStatusResponse:
    """Return current status of all defect toggles."""
    return DefectStatusResponse(defects=defect_manager.get_status())


@router.post("/defects/toggle", response_model=DefectStatusResponse, summary="Toggle intentional defect")
def toggle_defect(payload: DefectToggleRequest) -> DefectStatusResponse:
    """Enable or disable a specific synthetic defect."""
    success = defect_manager.set_defect(payload.defect_name, payload.enabled)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown defect name '{payload.defect_name}'. Available: {list(defect_manager.get_status().keys())}",
        )
    return DefectStatusResponse(defects=defect_manager.get_status())


@router.post("/reset", summary="Reset database and all defect toggles to baseline seed state")
def reset_environment() -> dict:
    """Reset both the database state and all defect toggles."""
    defect_manager.reset_all()
    db.reset()
    return {
        "status": "success",
        "message": "Sample API database and defects reset to clean baseline",
    }
