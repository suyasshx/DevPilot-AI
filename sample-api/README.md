# DevPilot AI — Sample Target E-Commerce API

This service acts as the realistic target API for **DevPilot AI** test generation, automated execution, and evaluation. It simulates an Electronic Arts (EA) gaming e-commerce and account backend with realistic endpoints, strict OpenAPI 3.0 schema contracts, and intentionally introduced defect toggles.

## Endpoints

| Method | Path | Summary | Auth Required |
|---|---|---|---|
| `POST` | `/auth/login` | Authenticate with username and password, returns JWT token | No |
| `POST` | `/users` | Register a new user account | No |
| `GET` | `/users/{user_id}` | Fetch user profile by ID | No |
| `GET` | `/products` | List products with pagination (`skip`, `limit`) and category filter | No |
| `POST` | `/orders` | Place order for authenticated user with inventory deduction | **Yes (Bearer)** |
| `GET` | `/admin/defects` | Inspect current defect toggle states | No |
| `POST` | `/admin/defects/toggle` | Enable/disable a specific defect | No |
| `POST` | `/admin/reset` | Restore seed data and reset all defects to False | No |

## Defect Injection Hooks (For 5-Way Failure Taxonomy Demonstration)

- `negative_quantity_allowed`: Allows negative item quantity in `/orders`, returning `201 Created` with a negative total balance (demonstrating regression bug detection).
- `unhandled_500_on_user_not_found`: Throws unhandled exception on `GET /users/{id}` for missing users, causing HTTP `500 Internal Server Error` (demonstrating execution error detection).
- `broken_schema_on_products`: Replaces `price` float with a string in `GET /products` (demonstrating contract violation detection).
- `auth_bypass_on_orders`: Bypasses JWT Bearer token check on `POST /orders` (demonstrating security regression detection).

## Running the API Locally

```bash
# From workspace root:
uvicorn app.main:app --app-dir sample-api --host 127.0.0.1 --port 8001 --reload
```

## Running the Automated Test Suite

```bash
# Run pytest with 97%+ code coverage:
pytest sample-api/tests -v --cov=sample-api/app --cov-report=term-missing

# Run standalone deterministic HTTPX harness:
python sample-api/tests/test_harness_runner.py
```
