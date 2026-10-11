# QA Guideline: Authentication, Authorization & Security Testing

## 1. Purpose
Define mandatory security test scenarios for protected REST API endpoints.

## 2. Authentication Scenarios
- **Missing Authorization Header:** On any endpoint requiring authentication, verify that omitting the `Authorization` header completely yields `401 Unauthorized` and includes a `WWW-Authenticate: Bearer` challenge header.
- **Malformed Bearer Header:** Test missing `Bearer` prefix (e.g., `Authorization: Token xyz` or `Authorization: xyz`). Must return `401 Unauthorized`.
- **Invalid Signature / Corrupted Token:** Test Bearer tokens with altered payloads or invalid cryptographic signatures. Must return `401 Unauthorized`.
- **Expired Tokens:** Test tokens whose `exp` claim is in the past. Verify that the response explicitly mentions token expiration and rejects with `401`.

## 3. Authorization & Role-Based Access Control (RBAC)
- **Role Invariant:** Endpoints restricted to `admin` or `auditor` roles must return `403 Forbidden` when accessed using a valid token belonging to a standard `user`.
- **Deactivated / Inactive Accounts:** Test authentication using accounts marked with `is_active = False`. The API MUST return `403 Forbidden` and deny all session creation.
- **Cross-Tenant Data Access:** Attempting to retrieve another user's private data or orders using a different user's valid token must be denied or scoped strictly to the authenticated subject.
