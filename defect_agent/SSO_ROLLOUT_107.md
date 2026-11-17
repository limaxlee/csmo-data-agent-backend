# DefectAgent SSO backend rollout (issue 107)

> Current behavior: SSO verification is always active. Local password signup is
> always rejected. The frontend no longer offers temporary password sessions.
> Login/refresh/link endpoints remain only for existing-account migration;
> this release does not remove existing users or reassign their data.
> Configure SERVICE_JWT_SECRET and a separate SECRET_KEY before starting the API.



## Configuration and order

1. Apply the new migration before enabling SSO: `uv run alembic upgrade head`.
2. Give DefectAgent and central `web-auth` the same **separate, randomly generated**
   `SERVICE_JWT_SECRET`. Existing central keys, including 22-byte keys, remain compatible.
   Keep it different from DefectAgent's `SECRET_KEY`.
3. Configure the central auth routes and shared service signing key before startup.
4. Local password registration is permanently disabled in every environment.

5. Deploy the frontend after this backend is running. Central auth must allow
   the DefectAgent callback URL and route `/auth`.

SSO verification is always active. A missing, placeholder,
or reused signing secret fails startup. Existing local users, IDs, roles, and
foreign-key ownership are unchanged.

## Browser-facing API

- A linked service bearer token works on ordinary protected endpoints.
- `GET /api/auth/me` with a valid but unlinked service token returns HTTP 409
  with `{"code":"sso_account_unlinked", ...}`.
- `POST /api/auth/sso/link`: local **access** bearer token plus
  `{"service_token":"<central service JWT>"}`. The backend requires matching
  normalized emails and attaches the SSO login ID to the existing UUID.
- `POST /api/auth/sso/provision`: central service bearer token. Creates a
  passwordless account with local role `user` when neither email nor login ID
  belongs to another user. Retrying the same identity returns the same user.
- Link conflicts return HTTP 409 with `sso_account_conflict` or
  `sso_email_mismatch`; invalid or expired credentials return HTTP 401.

The service JWT must never be treated as a local password or refresh token. The
frontend should not persist it in local storage.

## Administratively verified mapping

Use this only when self-service linking cannot succeed, such as the seeded
admin's `admin@example.com` address differing from their corporate SSO email.
Do not map accounts based on an email match alone.

1. Record an approved support ticket identifying the person, their verified
   corporate SSO login ID from central auth, the target local UUID, and the
   independent evidence that they own that local account. For the seeded admin,
   verify who holds the admin role and their corporate identity with the
   application owner. Never grant an admin role based on SSO group claims.
2. Have a database operator check the target user and confirm no other user
   owns the canonical login ID. Take a backup before applying the mapping.
3. On PostgreSQL, run the following transaction with the *verified canonical*
   login ID, UUID, operator ID, and ticket ID. Use bind parameters in your SQL
   client; do not paste service JWTs or passwords into SQL or logs.

```sql
BEGIN;
SELECT id, email, role, sso_loginid
FROM users WHERE id = :local_uuid FOR UPDATE;
SELECT id FROM users WHERE sso_loginid = :canonical_loginid FOR UPDATE;
-- Stop if the target is absent, already linked, or the login ID is in use.
WITH linked AS (
    UPDATE users SET sso_loginid = :canonical_loginid
    WHERE id = :local_uuid AND sso_loginid IS NULL
    RETURNING id
)
INSERT INTO sso_link_audit
    (user_id, sso_loginid, actor_type, actor, evidence_ref)
SELECT id, :canonical_loginid, 'admin', :operator_id, :ticket_id
FROM linked
RETURNING id;
-- Require exactly one returned audit row; otherwise ROLLBACK.
COMMIT;
```

4. Verify `/api/auth/me` with a fresh service JWT returns the same local UUID and
   role as before, and confirm the `sso_link_audit` entry. Store the ticket and
   operator approval in your normal audit system. The mapping changes no role
   or ownership column.

The database unique constraint rejects a login ID already linked to another
user. Every successful self-service link and SSO provisioning also writes an
immutable `sso_link_audit` row. Do not edit audit rows.
