# DICE Web Auth

Central ADFS login service for the DICE web entry point.

This app owns the future shared browser session:

- `/auth/login`
- `/auth/logout`
- `/auth/session`
- `/auth/token`
- `/auth/api/auth/*` (NextAuth callback/session internals)

Platform and Labeler can keep their current NextAuth flows during migration.
After this service is deployed and verified, their API clients can move from
app-local `getSession()` calls to `/auth/token`.

## Local

```bash
cd web-auth
npm install
npm run dev
```

Set `NEXT_PUBLIC_BASE_PATH=/auth` when serving under `/auth`.

## Runtime development login

The same production image can expose the ADFS simulator at runtime in an
isolated environment. It is disabled by default and requires a non-empty login
ID allowlist:

```env
DEV_LOGIN_ENABLED=true
DEV_LOGIN_ALLOWED_IDS=stage.user,stage.admin
DEV_LOGIN_ALLOW_ADMIN=false
```

`DEV_LOGIN_ALLOWED_IDS` is matched case-insensitively. Admin role selection is
available only when `DEV_LOGIN_ALLOW_ADMIN=true`; otherwise every allowed ID is
issued a normal user token. Keep all three values at their defaults in
production. Disabling the feature or removing an ID also invalidates existing
development-login cookies on the next `/session` or `/token` request.

## Admin-only Dashboard navigation

The landing and Download headers show Dashboard only after `/dashboard-access`
confirms an active admin profile from user-service. JWT/session roles alone do
not grant menu visibility. Loading, unauthenticated, non-admin, inactive and
unavailable-profile states hide the link. The check is repeated on window focus
and while the page is visible; stale requests are cancelled when identity changes.
Normal downloads keep their existing authentication policy.

```env
# Full server-side API base, including the actual user-service prefix:
USER_SERVICE_API_URL=http://localhost:8003/user/api/v1
# Browser-visible destination; use /dashboard on the shared production origin:
DASHBOARD_URL=http://localhost:3391/dashboard
```

The Helm ConfigMap supplies the release-local user-service address when no
explicit URL is configured. Helm also sets `DASHBOARD_ENABLED` from
`dashboard.enabled`, so the menu remains hidden until the Dashboard workloads
are enabled. The route forwards the current service JWT, follows no upstream
redirects and times out after five seconds. It returns only menu access and the
configured destination, never the token or user profile.

## Activation API

To preview the issuance UI without login or backend services, set
`NEXT_PUBLIC_ACTIVATION_PREVIEW=true` and open `/activation`. Preview mode uses
sample catalog values and disables key issuance. Leave it unset or `false` for
normal authenticated use.

The activation API is served under the app base path. The current Helm
configuration sets `NEXT_PUBLIC_BASE_PATH=/`, so endpoints start with
`/activation`. It reads and
writes the existing PostgreSQL activation tables created by the Django service;
configure `ACTIVATION_DB_HOST`, `ACTIVATION_DB_PORT`, `ACTIVATION_DB_NAME`,
`ACTIVATION_DB_USER`, and `ACTIVATION_DB_PASSWORD` at runtime. The API fails if
any required connection setting is missing.
Versions that use legacy AES activation keys also require `ACTIVATION_AES_KEY`.
Set it to the existing Python activation key string in the deployment Secret;
changing it breaks compatibility with existing product clients.
The `/activation` route serves the signed-in key issuance page. Issuance and
profile lookup require an active web-auth user profile from user-service.
Product and version catalog endpoints are public.

Available API routes include `GET /activation/profile`,
`POST /activation/products/{product_type}`,
`GET /activation/products`, `GET /activation/info`,
`GET /activation/info/{product_type}`,
and `GET /activation/history`.

Admin-only Dashboard activation APIs are served under `/activation/dashboard`:
`GET /counts`, `/history`, `/analysis`, and `/trends`, plus `PATCH` routes under
`/history/{product_type}` for confirm, ignore, and device-key duplicate checks.
These routes accept the same Bearer service JWT or PAT used with user-service;
the caller must resolve to an active admin there.
The route path follows the Activation API namespace and is implemented under
`app/activation/dashboard`.
