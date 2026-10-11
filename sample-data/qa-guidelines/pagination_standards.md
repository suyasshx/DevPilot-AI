# QA Guideline: Pagination and Resource Query Standards

## 1. Purpose
Define verification rules for collection endpoints supporting pagination and filtering parameters.

## 2. Offset and Limit Boundaries
- **Default Pagination:** Querying without pagination parameters MUST return default values (e.g., `skip = 0`, `limit = 10` or `limit = 20`) without errors.
- **Negative Offsets:** Passing negative `skip` values (e.g., `skip = -1`) MUST be rejected with `422 Unprocessable Entity`.
- **Zero Limit:** Requesting a page limit of `0` MUST be rejected with `422` (minimum limit is `1`).
- **Maximum Limit:** Requesting a limit exceeding the documented ceiling (e.g., `limit = 500` when max is `100`) MUST be rejected with `422`.
- **High Offset Beyond Total:** When `skip` exceeds the total number of records in the database, the API MUST return HTTP `200 OK` with an empty array `items: []` and accurate `total` count. It must NEVER raise an index out of bounds exception.

## 3. Filtering and Case-Insensitivity
- **Unknown Filter Values:** Filtering by non-existent categories or tags should return HTTP `200 OK` with empty list `items: []`, not a 404 or 500 error.
- **Case Sensitivity:** Category and tag filters should be tested with mixed-case strings (`HARDWARE`, `hardware`) to verify case-insensitivity.
