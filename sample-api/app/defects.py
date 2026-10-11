"""
DevPilot AI - Defect Injection Controller for Sample Target API.

This module provides intentionally introduced, isolated, togglable defects
used to demonstrate DevPilot AI's ability to detect:
1. API Contract Violations (Schema breaks, unexpected response types)
2. Negative value bypasses (Domain logic failure, negative order values)
3. Unhandled 500 runtime exceptions (Internal server errors)
4. Authentication bypass defects (Security regressions)

IMPORTANT: In clean/normal mode, all defects are disabled (False), and the API
strictly complies with its documented OpenAPI 3.0 specification.
"""

from typing import Dict
from threading import Lock


class DefectController:
    """Thread-safe manager for synthetic test defect toggles."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._defects: Dict[str, bool] = {
            "negative_quantity_allowed": False,
            "unhandled_500_on_user_not_found": False,
            "broken_schema_on_products": False,
            "auth_bypass_on_orders": False,
        }

    def is_enabled(self, defect_name: str) -> bool:
        """Check if a specific defect toggle is active."""
        with self._lock:
            return self._defects.get(defect_name, False)

    def set_defect(self, defect_name: str, enabled: bool) -> bool:
        """
        Set the state of a defect toggle.
        Returns True if the defect exists and was updated, False otherwise.
        """
        with self._lock:
            if defect_name in self._defects:
                self._defects[defect_name] = enabled
                return True
            return False

    def reset_all(self) -> None:
        """Reset all defect toggles to normal/clean state (all False)."""
        with self._lock:
            for k in self._defects:
                self._defects[k] = False

    def get_status(self) -> Dict[str, bool]:
        """Return a snapshot of all defect toggle states."""
        with self._lock:
            return dict(self._defects)


# Global singleton instance
defect_manager = DefectController()
