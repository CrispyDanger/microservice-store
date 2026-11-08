# auth

Shared access-token verification for every service.

- `decode_access_token(token, public_key)`: verifies an RS256 access token issued by the user service and returns `AccessClaims(user_id, role, expires_at)`.
- `JWTAuth(public_key)`: a FastAPI dependency that reads `Authorization: Bearer ...` and returns `AccessClaims`, with `require_role(role)` for role checks.

Services get only the **public** key, so they can verify tokens but never create them.
