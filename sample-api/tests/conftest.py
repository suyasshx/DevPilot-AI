"""
DevPilot AI - PyTest Configuration and Fixtures for Sample Target API.
"""

import sys
import os
from typing import Generator, Dict
import pytest
import httpx

# Ensure sample-api is in Python path for test discovery
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_API_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if SAMPLE_API_DIR not in sys.path:
    sys.path.insert(0, SAMPLE_API_DIR)

from app.main import app
from app.database import db
from app.defects import defect_manager
from app.auth import create_access_token


@pytest.fixture(autouse=True)
def reset_test_state() -> Generator[None, None, None]:
    """Reset database and defect toggles before and after every test."""
    db.reset()
    defect_manager.reset_all()
    yield
    db.reset()
    defect_manager.reset_all()


@pytest.fixture
def client() -> Generator[httpx.Client, None, None]:
    """Synchronous HTTPX client with ASGI transport."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    with httpx.Client(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
def user_auth_headers() -> Dict[str, str]:
    """Return headers containing a valid Bearer token for qa_user (ID 1)."""
    token = create_access_token({"sub": "1", "username": "qa_user", "role": "user"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers() -> Dict[str, str]:
    """Return headers containing a valid Bearer token for admin_user (ID 2)."""
    token = create_access_token({"sub": "2", "username": "admin_user", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}
