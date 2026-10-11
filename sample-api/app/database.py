"""
DevPilot AI - In-Memory Seed Database for Sample Target API.

Provides isolated seed data with thread-safe reset helpers for repeatable
test automation execution.
"""

from typing import Dict, Any, List
from threading import Lock
from datetime import datetime, timezone
import copy

INITIAL_USERS: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "username": "qa_user",
        "email": "qa_user@devpilot.internal",
        "password": "SecretPass123!",
        "role": "user",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
    },
    2: {
        "id": 2,
        "username": "admin_user",
        "email": "admin@devpilot.internal",
        "password": "AdminPass123!",
        "role": "admin",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z",
    },
    3: {
        "id": 3,
        "username": "inactive_user",
        "email": "inactive@devpilot.internal",
        "password": "InactivePass123!",
        "role": "user",
        "is_active": False,
        "created_at": "2026-01-01T00:00:00Z",
    },
}

INITIAL_PRODUCTS: Dict[int, Dict[str, Any]] = {
    1: {
        "id": 1,
        "name": "EA Sports Pro Wireless Controller",
        "category": "hardware",
        "price": 69.99,
        "stock": 50,
        "description": "High-precision low-latency wireless gamepad with haptic triggers.",
    },
    2: {
        "id": 2,
        "name": "Apex Legends Mechanical Gaming Keyboard",
        "category": "hardware",
        "price": 129.99,
        "stock": 30,
        "description": "RGB tactile mechanical keyboard tuned for esports competition.",
    },
    3: {
        "id": 3,
        "name": "Battlefield Spatial Audio Headset",
        "category": "audio",
        "price": 89.50,
        "stock": 45,
        "description": "7.1 surround sound gaming headset with noise-cancelling boom mic.",
    },
    4: {
        "id": 4,
        "name": "The Sims 4 Collectors Plush Toy",
        "category": "merchandise",
        "price": 24.99,
        "stock": 100,
        "description": "Plush Plumbob collectible toy.",
    },
    5: {
        "id": 5,
        "name": "Digital Game Pass 3-Month Subscription",
        "category": "digital",
        "price": 29.99,
        "stock": 9999,
        "description": "Unlimited digital game library access for 90 days.",
    },
    6: {
        "id": 6,
        "name": "Limited Edition Sold-Out Trophy",
        "category": "merchandise",
        "price": 199.99,
        "stock": 0,
        "description": "Exclusive trophy item currently out of stock.",
    },
}

INITIAL_ORDERS: Dict[int, Dict[str, Any]] = {
    101: {
        "id": 101,
        "user_id": 1,
        "items": [
            {
                "product_id": 1,
                "product_name": "EA Sports Pro Wireless Controller",
                "unit_price": 69.99,
                "quantity": 1,
                "subtotal": 69.99,
            }
        ],
        "total_amount": 69.99,
        "status": "completed",
        "shipping_address": "100 EA Way, Redwood City, CA",
        "created_at": "2026-02-15T12:00:00Z",
    }
}


class InMemoryDatabase:
    """Thread-safe in-memory database with transaction-like rollback."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.users: Dict[int, Dict[str, Any]] = {}
        self.products: Dict[int, Dict[str, Any]] = {}
        self.orders: Dict[int, Dict[str, Any]] = {}
        self.user_seq = 3
        self.order_seq = 101
        self.reset()

    def reset(self) -> None:
        """Reset state to original seed data."""
        with self._lock:
            self.users = copy.deepcopy(INITIAL_USERS)
            self.products = copy.deepcopy(INITIAL_PRODUCTS)
            self.orders = copy.deepcopy(INITIAL_ORDERS)
            self.user_seq = max(self.users.keys(), default=0)
            self.order_seq = max(self.orders.keys(), default=100)

    def next_user_id(self) -> int:
        with self._lock:
            self.user_seq += 1
            return self.user_seq

    def next_order_id(self) -> int:
        with self._lock:
            self.order_seq += 1
            return self.order_seq


# Global DB instance
db = InMemoryDatabase()
