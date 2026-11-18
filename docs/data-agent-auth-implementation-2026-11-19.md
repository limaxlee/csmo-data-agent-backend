# Data agent authorization: implementation guide

Written 2026-11-19.

This document describes everything needed to put login and access control in front of the data
agent, in the order the work should be done. It assumes no background in authorization.

No secret values are written here on purpose. Where a secret is needed, the document says where
to find it.

It was written from the reference code and deployment information listed in
[Part 9](#part-9-where-each-fact-comes-from). It does not build on the older files in `docs/`
(`authentication.md`, `sso-authorization-plan.md`); those were written before the decision to copy
the defect agent's flow and were not used as a source.

## Contents

- [Summary and status](#summary-and-status)
- [Words used in this document](#words-used-in-this-document)
- [How the login works](#how-the-login-works)
- [Part 1: Add the forwarding rule to DICE (stage)](#part-1-add-the-forwarding-rule-to-dice-stage)
- [Part 2: Checks before starting the implementation](#part-2-checks-before-starting-the-implementation)
- [Part 3: Backend implementation](#part-3-backend-implementation)
- [Part 4: Frontend implementation](#part-4-frontend-implementation)
- [Part 5: Deploying and testing on stage](#part-5-deploying-and-testing-on-stage)
- [Part 6: Going to production later](#part-6-going-to-production-later)
- [Part 7: Missing reference files and configuration](#part-7-missing-reference-files-and-configuration)
- [Part 8: Problems found during the review](#part-8-problems-found-during-the-review)
- [Part 9: Where each fact comes from](#part-9-where-each-fact-comes-from)

---

## Summary and status

**Goal.** A person opens the data agent, is sent to Samsung SSO if not logged in, and comes back
logged in. The backend then knows who they are. A new person is recorded but cannot use the data
agent until an admin approves them. Every visit is recorded with time and IP address. The login
part must behave exactly like the defect agent's.

**How.** The data agent does not talk to Samsung SSO itself. It reuses the DICE login service
(called `web-auth`), the same way the defect agent does. The login service gives the browser a
signed pass, the browser sends the pass with every request, and the backend checks the pass.

**The work, in order.**

1. Add a forwarding rule on the DICE stage address so the data agent can be opened as
   `https://stage.gtrai.sec.samsung.net/data-agent/` (Part 1).
2. Run the checks in Part 2. They confirm that login works on that address and show exactly what
   the pass contains.
3. Backend: check the pass, create the two tables, add the approval gate and the admin
   endpoints (Part 3).
4. Frontend: add the login steps and send the pass with every request (Part 4).
5. Deploy both on stage and test end to end (Part 5).
6. Production comes later and has its own list (Part 6).

**Decisions already made.**

| Decision | Value |
|---|---|
| Login flow | Same as the defect agent: DICE `web-auth` signs a pass, the backend only checks it |
| Environment to start with | Stage (`stage.gtrai.sec.samsung.net`) |
| Address of the frontend | `https://stage.gtrai.sec.samsung.net/data-agent/` |
| Address of the backend | `https://stage.gtrai.sec.samsung.net/data-agent/api/...` |
| Where the servers run | Unchanged: `10.240.35.180` (frontend 13080, backend 18080, MCP 10420 and 10422, Postgres 5432) |
| Existing users | None that matter (test accounts only), so no data migration |
| Admins | A list of login IDs in the backend configuration. An admin page comes later |
| Tables | `user_accounts` (one row per person, with everything SSO sends) and `user_access_log` (one row per visit) |
| Where the forwarding rule is stored | This repo, `deploy/stage/routing.yaml` |

**Status on 2026-11-19.**

- `deploy/stage/routing.yaml` is written. It has not been applied to the cluster.
- No authorization code exists in the backend yet. Today every endpoint is open to anyone who can
  reach port 18080.
- The frontend has not been changed.

---

## Words used in this document

| Word | Meaning |
|---|---|
| Samsung SSO (ADFS) | The company login page where people type their password. Its address is `sts.secsso.net` |
| DICE login service (`web-auth`) | A small website run by DICE. It is the only thing that talks to Samsung SSO. Source: `mvp-vision-ai-platform/web-auth` |
| Cookie | A small note a website stores in the browser. The browser sends it back only to the website that stored it. The login cookie is named `dice.session-token` |
| Pass (token, service JWT) | A short text the login service creates. It says who the person is and when it expires, and it is signed. The technical name is JWT |
| Secret (`SERVICE_JWT_SECRET`) | The password used to sign the pass. The login service and every backend that checks passes hold the same value |
| Bearer | The way the pass is sent to the backend: a request header `Authorization: Bearer <pass>` |
| Authentication | Finding out who someone is. Done by Samsung SSO and the login service |
| Authorization | Deciding what that person may do. Done by the data agent backend |
| Gateway | The entry server that receives every request for a DICE address and decides where to send it by looking at the path |
| Forwarding rule | One entry in the gateway's list: "paths starting with X go to server Y". In the cluster it is an object of kind `VirtualService` |
| `ServiceEntry` | A cluster object that gives a name to a server outside the cluster, so a forwarding rule can point at it |
| Namespace | A named area inside the cluster. Stage things live in `dice-stage`, production things in `dice` |
| Argo CD | The tool that copies configuration from Git repos onto the cluster |
| 401 / 403 | Reply codes. 401: the pass is missing or not valid, log in again. 403: the pass is valid but this person is not allowed |

---

## How the login works

### Who is involved

| Who | Address | Role |
|---|---|---|
| Browser | the person's PC | Holds the cookie and the pass |
| Gateway | `stage.gtrai.sec.samsung.net` | Forwards each request by its path |
| DICE login service | reached as `/auth/...` on the same address | Talks to Samsung SSO, stores the cookie, creates the pass |
| Samsung SSO | `sts.secsso.net` | Checks the password |
| Data agent frontend | `10.240.35.180:13080`, reached as `/data-agent/` | The web page |
| Data agent backend | `10.240.35.180:18080`, reached as `/data-agent/api/` | Checks the pass, decides access |

### The steps

1. The person opens `https://stage.gtrai.sec.samsung.net/data-agent/`. The gateway forwards the
   request to the frontend server.
2. The page asks the login service `GET /auth/session`. The browser attaches the cookie if it has
   one. The answer is `{"authenticated": true, "user": {...}}` or `{"authenticated": false, ...}`.
3. If not authenticated, the page sends the browser to
   `/auth/login?callbackUrl=<the current page address>`. It does this only once per browser tab,
   so a failed login cannot loop forever.
4. The login service sends the browser to Samsung SSO. The person logs in. Samsung SSO sends the
   browser back to the login service, which stores the cookie `dice.session-token` and then sends
   the browser to the `callbackUrl`, which is the data agent page.
5. The page loads again and repeats step 2. This time the answer is authenticated.
6. The page asks the login service `GET /auth/token` and receives
   `{"accessToken": "<pass>", "tokenType": "Bearer", "expiresAt": <unix seconds>}`.
7. The page calls the backend `GET /data-agent/api/auth/me` with the header
   `Authorization: Bearer <pass>`.
8. The backend checks the pass. It creates or updates the person's row in `user_accounts`, adds a
   row to `user_access_log`, and answers with the account, including `is_active`.
9. If `is_active` is false, the page shows "waiting for approval". Otherwise the page starts
   normally. Every later request to the backend carries the same header, and the page uses the
   `user_id` from step 8 in the existing `/apps/users/{user_id}/...` addresses.
10. About a minute before `expiresAt` the page asks `/auth/token` again for a new pass. If the
    backend ever answers 401, the page forgets the pass and starts again at step 2. The logout
    link goes to `/auth/logout`.

Steps 1 to 7, 9 and 10 are what the defect agent's page does today. Step 8 is where the data
agent differs: the defect agent creates the account and lets the person in immediately, with no
approval.

Nothing has to be registered with Samsung SSO for the data agent. Samsung SSO only ever sends the
browser back to the login service.

### Why the address matters

The cookie from step 4 belongs to the address `stage.gtrai.sec.samsung.net` (the login service
sets no wider cookie domain in the Helm values that were reviewed). The browser shows it only to
pages opened under that address. A page opened as `http://10.240.35.180:13080` never gets it, so
step 2 always answers "not authenticated" and login cannot finish. This is the only reason the
forwarding rule in Part 1 is needed. The servers themselves do not move.

### What the pass contains

The login service builds the pass in `web-auth/app/service-token.ts`. It is signed with the
algorithm HS256 and lasts about one hour.

| Field | Content | Notes |
|---|---|---|
| `sub` | Login ID | Taken from SSO in this order: `loginid` claim, the part of the email before `@`, the account part of `unique_name`, the SSO subject. This is the data agent's `user_id` |
| `username` | Same login ID | The backend requires it to equal `sub` |
| `email` | SSO `upn` (the email), or null | |
| `full_name` | `upn`, else `unique_name`, else the login ID | Not a real display name. SSO does not send one |
| `department` | SSO `deptname`, or null | |
| `company` | SSO `busname`, or null | |
| `unique_name` | SSO `unique_name` (for example `DOMAIN\account`), or null | |
| `sid` | SSO `sid`, or null | Meaning not confirmed. See check 4 in Part 2 |
| `roles` | List built from SSO `groups` and `role` | May be empty. Information only. Never use it to grant access |
| `type` | Always `service` | |
| `iss` | Always `web-auth` | Who issued the pass |
| `aud` | Always `dice-backend` | Who the pass is for |
| `iat`, `exp` | Issue time and expiry time, in unix seconds | |

On stage the login service can also run a login simulator ("dev login"). A pass from the
simulator has `email` set to `<login id>@samsung.com`, `full_name` set to the login ID, `roles`
either `["admin"]` or empty, and all other profile fields null.

---

## Part 1: Add the forwarding rule to DICE (stage)

### What gets added

Two objects in the namespace `dice-stage`. Both are in `deploy/stage/routing.yaml`.

| Object | Name | What it does |
|---|---|---|
| `ServiceEntry` | `data-agent-server` | Registers `10.240.35.180` inside the cluster under the name `data-agent.external.local`, with ports 13080 and 18080 |
| `VirtualService` | `data-agent-stage` | On `stage.gtrai.sec.samsung.net`, sends `/data-agent/api/...` to port 18080 with `/data-agent/api` removed, and sends `/data-agent/...` to port 13080 unchanged. Also redirects http to https |

The login paths (`/auth/...`) are not in the file. They are already forwarded on this address by
the defect agent's rule `defect-studio-stage`. This means data agent login depends on that rule
staying in place.

### How to add it through the cluster web page

1. Open the Kubernetes web page you normally use and set the namespace selector to `dice-stage`.
2. Find the button that creates objects from YAML:
   - Kubernetes Dashboard: the `+` at the top right, then the tab "Create from input".
   - Rancher: "Import YAML" at the top right (an arrow pointing up).
3. Open `deploy/stage/routing.yaml`, copy the whole content, and paste it into the box.
4. Click "Upload" (Dashboard) or "Import" (Rancher).
5. If the page refuses the paste, it may not accept two objects at once. Paste the part above the
   `---` line first, then the part below it.

### The same thing with commands

On a computer where `kubectl` is installed and connected to the cluster, from the folder that
holds the file:

```
kubectl get virtualservice -n dice-stage           # should list defect-studio-stage
kubectl apply -f routing.yaml --dry-run=server     # checks the file, changes nothing
kubectl apply -f routing.yaml                      # applies it
```

### Check that it works

Open `https://stage.gtrai.sec.samsung.net/data-agent/api/health` in a browser. The backend's
health reply should appear, with `server_status`, `postgresql_db_status` and
`object_storage_status`.

The page `https://stage.gtrai.sec.samsung.net/data-agent/` will look broken until the frontend is
rebuilt to live under `/data-agent/` (Part 4). That is expected.

### If the check fails

| What you see | Likely cause | What to do |
|---|---|---|
| Error 503 | The cluster cannot reach `10.240.35.180:18080`, usually a firewall | Have the network path from the cluster nodes to that server and port opened |
| Error 503, and the network path is known to be open | The gateway cannot see the `ServiceEntry` | Remove the two `exportTo` lines from the file and apply it again |
| `{"detail":"Not Found"}` | The request reached the backend, but with the wrong path | The path rewriting is not doing what the file intends. Send the exact address you opened and this reply for analysis |
| Another product's page, or a 404 that is not the line above | An older rule on the same address catches paths starting with `/data-agent` first | List all `VirtualService` objects for `stage.gtrai.sec.samsung.net` and look for a prefix that `/data-agent` starts with, such as `/data` |

### Undo

Delete the two objects `data-agent-stage` (kind `VirtualService`) and `data-agent-server` (kind
`ServiceEntry`) in namespace `dice-stage`. With commands: `kubectl delete -f routing.yaml`.

### Why this is safe to try

- Stage and production share one cluster and are separated by namespace and address. The file
  names `dice-stage` and `stage.gtrai.sec.samsung.net`, so production is not touched.
- The rule only handles paths that start with `/data-agent`. It cannot take requests away from
  another product unless that product already uses such paths.
- Argo CD only manages objects it created. It will not remove objects added by hand.

### Not verified

- Whether the cluster can reach `10.240.35.180` on ports 13080 and 18080. The check above answers
  this.
- Whether `/data-agent` is free on the stage address. The main rule lists for the DICE addresses
  were not among the files reviewed (see Part 7).
- The file itself has not been tried against the cluster.

### Making it permanent later

An object added by hand is not recorded anywhere except the cluster. Once the rule works, it
should be applied by Argo CD from a Git repo, the way the defect agent's rule is. Argo CD has to
be able to read that repo. This repo's remote is on github.com, which the cluster's Argo CD very
likely cannot read, so the file would have to live in a repo on the company's GitHub.

---

## Part 2: Checks before starting the implementation

Do these in order. Each one removes an unknown that would otherwise be discovered in the middle
of coding. Checks 1 to 5 need only a browser and a few lines of Python.

### Check 1: the forwarding rule works

Covered in Part 1. Do not continue until the health reply appears through the stage address.

### Check 2: the login service answers on the stage address

Open `https://stage.gtrai.sec.samsung.net/auth/session`.

- Expected: a short reply containing `"authenticated": false` or `"authenticated": true`.
- If you get a 404 or another page: the `/auth` forwarding on stage is not what this document
  assumes. Look at the `defect-studio-stage` rule before going on.

### Check 3: logging in returns you to the data agent address

Open this address (one line):

```
https://stage.gtrai.sec.samsung.net/auth/login?callbackUrl=https%3A%2F%2Fstage.gtrai.sec.samsung.net%2Fdata-agent%2F
```

- Expected: the Samsung SSO page appears, or you are logged in silently. Afterwards the browser's
  address bar shows `https://stage.gtrai.sec.samsung.net/data-agent/`. The page itself may look
  broken. Then `https://stage.gtrai.sec.samsung.net/auth/session` shows `"authenticated": true`
  and your user.
- If a small form titled "DEV MODE" appears instead of Samsung SSO: stage is running the login
  simulator. Only login IDs on the stage allowlist (`DEV_LOGIN_ALLOWED_IDS` in the stage login
  service settings) can log in. Either add your ID there or note that real SSO cannot be tested
  on stage.
- If you end up on the stage home page instead of `/data-agent/`: the login service rejected the
  return address. Add `/data-agent` to `AUTH_ALLOWED_CALLBACK_PREFIXES` in the stage login
  service settings. From reading the code this should not be needed, because a full address on
  the same website is accepted without looking at that list, but this check is the proof.

### Check 4: look inside a real pass

While logged in, open `https://stage.gtrai.sec.samsung.net/auth/token`. Copy the value of
`accessToken`. Then run this on your own computer:

```python
import base64, json

token = "PASTE THE accessToken HERE"
payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(payload)), indent=2, ensure_ascii=False))
```

Do not paste the pass into a website that decodes tokens. For one hour it works as your login.

Write down what you see for: `sub`, `username`, `email`, `full_name`, `department`, `company`,
`unique_name`, `sid`, `roles`.

- Expected: `iss` is `web-auth`, `aud` is `dice-backend`, `type` is `service`, and `sub` equals
  `username`.
- `sub` is your `user_id` in the data agent. It is the value to put in the admin list.
- Look at `sid`. If it starts with `S-1-5-`, it is a permanent Windows account identifier. If it
  changes at every login, it is a session identifier. This decides how useful the column is.
- Look at which fields are null for a real account. All of them are stored either way.

### Check 5: the stage secret verifies that pass

The stage secret is in the cluster: namespace `dice-stage`, secret `dice-stage-runtime`, key
`service-jwt`. Install PyJWT (`pip install pyjwt`) and run:

```python
import jwt

token = "PASTE THE accessToken HERE"
secret = "PASTE THE STAGE SECRET HERE"
print(jwt.decode(token, secret, algorithms=["HS256"], issuer="web-auth",
                 audience="dice-backend", options={"require": ["exp", "sub"]}))
```

- Expected: the same fields as in check 4 are printed.
- `InvalidSignatureError`: wrong secret. The usual mistake is using the production value.
- `ExpiredSignatureError`: the pass is older than an hour. Get a new one and repeat.

This is exactly what the backend will do. If it works here, the backend settings are known to be
right. Do not save the script with the secret in it.

### Check 6: a long agent run survives the gateway

The `/run` endpoint keeps one request open until the agent has finished. Gateways commonly cut a
request on which nothing is sent for several minutes. As far as I know the default of this
gateway type is five minutes, but that is not confirmed for this cluster.

While the backend is still open (before the authorization code is deployed), run from any PC:

```
curl -X POST "https://stage.gtrai.sec.samsung.net/data-agent/api/apps/users/routing-test/sessions"
curl -X POST "https://stage.gtrai.sec.samsung.net/data-agent/api/apps/users/routing-test/sessions/SESSION_ID/run?query=YOUR%20LONGEST%20REALISTIC%20QUESTION"
```

The first command prints a `session_id`. Put it in place of `SESSION_ID` in the second one.

- Expected: the answer arrives, however long the run takes.
- If the request is cut with a 504 or a reset: this is not an authorization problem, but it
  blocks using the data agent through the gateway. Possible fixes are raising the timeout on the
  forwarding rule, or changing `/run` to return at once and letting the page poll the existing
  `run-state` endpoint. Decide before the frontend moves.

### Check 7: where the real IP address arrives

The backend will see every request as coming from the cluster, not from the person's PC. The real
address should arrive in the request header `X-Forwarded-For` or `X-Envoy-External-Address`.
Which one, and at which position in the list, has to be seen once on real traffic.

How: during backend work, temporarily log both headers and `request.client.host` on one endpoint,
call it through the stage address from a PC whose IP you know, and compare.

### Check 8: questions about the frontend

The frontend code was not among the files reviewed. Answer these from the frontend repo:

1. Can it be built to live under `/data-agent/` (the "base path" build setting)?
2. Is the backend address a setting? It must become `/data-agent/api`.
3. Where does the `user_id` in the request addresses come from today? It must come from the
   backend's `/auth/me` reply.
4. How are artifact images shown? An `<img src="...">` cannot send the pass, so images must be
   fetched with the pass and shown from memory (Part 4).
5. Does the page survive a full reload at any moment? The login redirect is a full reload.

### Check 9: the JWT library in the backend environment

In the environment the backend runs in, run `pip show pyjwt`.

- If it is listed: note the version and pin exactly that version in both requirements files. It
  is very likely already installed, because the `mcp` package depends on it.
- If it is not listed: add the current PyJWT 2.x release to both requirements files.

### Check 10: the admin list

Decide the login IDs of the first admins. Use the `sub` value from check 4, in lower case.

### Check 11: fetch the missing references

See Part 7. Only the first two items there are needed before the frontend work starts. The
backend work needs none of them.

---

## Part 3: Backend implementation

All paths in this part are in this repo.

### 3.1 Design in short

- The backend never talks to Samsung SSO or to the login service. It only checks the pass.
- The identity is the pass's `sub` field, lower-cased. It is used as `user_id` everywhere the data
  agent already uses a `user_id` (sessions, run locks, artifact storage keys).
- Checking happens in FastAPI dependencies, which run before the endpoint function. This matters
  because every endpoint in `data_agent/routers/agent.py` wraps its body in
  `except Exception -> 500`. A check placed inside the body would be turned into a 500 error.
- The existing addresses `/apps/users/{user_id}/...` stay. The backend refuses a request whose
  `user_id` in the address is not the caller's own.
- A person who is not approved is refused with 403 on everything except `/auth/me`.
- A login ID in the admin list is always allowed, whatever its `is_active` column says.

Left out on purpose, compared with the defect agent:

- Local password login, token refresh, and account linking. They exist in the defect agent only
  to carry over its old password accounts. The data agent has none.
- A separate "create my account" call. The defect agent's page calls `/api/auth/me`, gets
  `sso_account_unlinked`, then calls `/api/auth/sso/provision`. The data agent creates the row
  inside `/auth/me`. The person sees the same behaviour.

### 3.2 Configuration

Add to `common/config.py`:

```python
class AuthConfig(BaseModel):
    service_jwt_secret: str
    issuer: str = "web-auth"
    audience: str = "dice-backend"
    admin_user_ids: list[str] = []

    @field_validator("service_jwt_secret")
    @classmethod
    def _secret_is_set(cls, value: str) -> str:
        if not value.strip() or value.lower().startswith("change-me"):
            raise ValueError("SERVICE_JWT_SECRET must be set to the web-auth signing secret")
        return value

    @field_validator("admin_user_ids")
    @classmethod
    def _lowercase_ids(cls, value: list[str]) -> list[str]:
        return [item.strip().casefold() for item in value if item.strip()]
```

- Add `auth: AuthConfig` and `cors_origins: list[str] = []` to `Settings`.
- Add to `_ENV_MAP`:
  - `"SERVICE_JWT_SECRET": ("auth.service_jwt_secret", str)`
  - `"AUTH_ADMIN_USER_IDS": ("auth.admin_user_ids", <split on commas>)`
- `issuer`, `audience` and `admin_user_ids` may also be written in `config.yaml` under `auth:`.

Rules:

- The secret comes only from the environment variable `SERVICE_JWT_SECRET`. Never write it in
  `config.yaml`: the `Dockerfile` copies that file into the image, and the repo is on github.com.
- Because `auth` has no default, the backend refuses to start when the secret is missing. This
  matches the defect agent, where a missing or placeholder secret fails startup.
- `SETTINGS` is built when `common.config` is imported. The tests therefore need the variable set
  before that import. Put `os.environ.setdefault("SERVICE_JWT_SECRET", "test-secret-for-unit-tests")`
  at the very top of `tests/conftest.py`, above the other imports.

### 3.3 Library

Add PyJWT to `requirements_py313_prod.txt` and `requirements_py313_dev.txt` (see check 9).

The defect agent uses `python-jose==3.3.0`. PyJWT is the better maintained of the two and does the
same job. Depending on its version, PyJWT may print a warning when the secret is shorter than 32
bytes. The defect agent's rollout notes say such short keys exist in DICE. The warning is
harmless. Do not turn on any strict key-length option.

### 3.4 Checking the pass

New file `data_agent/infra/service_token.py`. The checks are the same as in the defect agent's
`service_token_verifier.py`, with two additions that are marked.

```python
import jwt
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SsoIdentity:
    user_id: str
    email: str | None
    full_name: str | None
    department: str | None
    company: str | None
    unique_name: str | None
    sid: str | None
    roles: list[str]
    claims: dict = field(default_factory=dict)   # the whole pass, as received


class ServiceTokenVerifier:
    def __init__(self, secret: str, issuer: str, audience: str):
        self._secret, self._issuer, self._audience = secret, issuer, audience

    def verify(self, token: str) -> SsoIdentity:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],              # nothing else is accepted
                issuer=self._issuer,               # must be "web-auth"
                audience=self._audience,           # must be "dice-backend"
                options={"require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError as error:
            raise AuthError(401, "invalid_token", "Invalid service token") from error

        if claims.get("type") != "service":
            raise AuthError(401, "invalid_token", "Invalid service token")

        subject, username = claims.get("sub"), claims.get("username")
        if not isinstance(subject, str) or not isinstance(username, str):
            raise AuthError(401, "invalid_token", "Invalid service identity")

        user_id = subject.strip().casefold()
        if (
            not user_id
            or len(user_id) > 255
            or any(ch.isspace() or ord(ch) < 32 for ch in user_id)
            or user_id in {"undefined", "null", "none"}
            or username.strip().casefold() != user_id
            or "/" in user_id or "\\" in user_id      # addition: user_id is part of storage keys
        ):
            raise AuthError(401, "invalid_token", "Invalid service identity")

        return SsoIdentity(
            user_id=user_id,
            email=_text(claims.get("email"), lower=True),
            full_name=_text(claims.get("full_name"), limit=255),
            department=_text(claims.get("department")),
            company=_text(claims.get("company")),
            unique_name=_text(claims.get("unique_name")),
            sid=_text(claims.get("sid")),
            roles=[r for r in claims.get("roles") or [] if isinstance(r, str)],
            claims=claims,                            # addition: kept for the sso_claims column
        )
```

`_text` is a small helper: return the stripped string, or `None` when the value is not a string
or is empty; optionally lower-case it or cut it to a length.

One difference from the defect agent: it validates the email with the `email-validator` package.
The data agent does not need that, because it never matches people by email.

### 3.5 Tables

Created in code with `CREATE TABLE IF NOT EXISTS` at startup, the same way
`data_agent/infra/session_lock.py` creates `session_run_locks`. The repo has no migration tool.

```sql
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id         TEXT PRIMARY KEY,                 -- pass "sub", lower case

    -- owned by the data agent
    is_active       BOOLEAN     NOT NULL DEFAULT false,
    activated_at    TIMESTAMPTZ,
    activated_by    TEXT,                             -- admin's user_id
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_access_at  TIMESTAMPTZ,
    last_access_ip  TEXT,

    -- copied from SSO, refreshed on every /auth/me
    email           TEXT,
    full_name       TEXT,
    department      TEXT,
    company         TEXT,
    unique_name     TEXT,
    sid             TEXT,
    roles           JSONB       NOT NULL DEFAULT '[]'::jsonb,
    sso_claims      JSONB       NOT NULL DEFAULT '{}'::jsonb,   -- the whole pass
    sso_updated_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_access_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES user_accounts(user_id) ON DELETE CASCADE,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address  TEXT,
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS ix_user_access_log_user_time
    ON user_access_log (user_id, accessed_at DESC);
```

Why it is shaped this way:

- **Two tables instead of a list column.** A list inside the account row would be rewritten in
  full at every visit, would grow without limit, and could not be searched or trimmed by date.
- **Everything from SSO is stored.** Each known field has its own column so it can be searched and
  shown. `sso_claims` additionally keeps the whole pass exactly as received, so a field the login
  service adds later is captured without changing the table.
- **`is_active`** is the "activation" column. DICE's own user service uses the same name for the
  same idea.
- **`roles` is information only.** It comes from SSO groups. Never use it to decide `is_active`
  or who is an admin. The defect agent's rollout notes state the same rule.
- **Table names.** The database `cosmoData` also holds the agent framework's own tables
  (`sessions`, `events` and others), so a plain name like `users` is avoided.

This stores personal data (email, department, company, group names, IP addresses). Check whether
company rules require a retention limit. Old log rows can be removed with
`DELETE FROM user_access_log WHERE accessed_at < now() - interval '1 year'`.

### 3.6 Database access

New file `data_agent/infra/user_repository.py`, class `UserAccountRepository`, built on the
existing `PostgreSQLClient` and written like `SessionLockRepository`.

| Method | What it does |
|---|---|
| `initialize()` | Runs the three `CREATE ... IF NOT EXISTS` statements above |
| `record_access(identity, ip, user_agent)` | Creates or updates the account from SSO data, adds one log row, returns the account |
| `get(user_id)` | Returns the account or `None` |
| `list(is_active=None)` | Returns accounts, newest first, optionally filtered |
| `set_active(user_id, is_active, admin_id)` | Sets `is_active`. On activation also sets `activated_at` and `activated_by` |
| `list_access(user_id, limit)` | Returns the newest log rows for one person |

`record_access` is one statement, so the account and the log row are written together or not at
all:

```sql
WITH account AS (
    INSERT INTO user_accounts (
        user_id, email, full_name, department, company, unique_name, sid,
        roles, sso_claims, sso_updated_at, last_access_at, last_access_ip
    )
    VALUES (
        :uid, :email, :full_name, :department, :company, :unique_name, :sid,
        CAST(:roles AS JSONB), CAST(:claims AS JSONB), now(), now(), :ip
    )
    ON CONFLICT (user_id) DO UPDATE SET
        email          = EXCLUDED.email,
        full_name      = EXCLUDED.full_name,
        department     = EXCLUDED.department,
        company        = EXCLUDED.company,
        unique_name    = EXCLUDED.unique_name,
        sid            = EXCLUDED.sid,
        roles          = EXCLUDED.roles,
        sso_claims     = EXCLUDED.sso_claims,
        sso_updated_at = now(),
        last_access_at = now(),
        last_access_ip = EXCLUDED.last_access_ip
    RETURNING *
), logged AS (
    INSERT INTO user_access_log (user_id, ip_address, user_agent)
    SELECT user_id, :ip, :user_agent FROM account
)
SELECT * FROM account
```

Notes:

- A new row gets `is_active = false` from the column default. An existing row keeps its value,
  because `is_active` is not in the `DO UPDATE` list.
- Pass `roles` and `claims` as text made with `json.dumps(...)`. When reading, the two JSONB
  columns may come back as text. If so, turn them back with `json.loads(...)`. Check this once
  when writing the repository.

### 3.7 The checks as FastAPI dependencies

New file `data_agent/routers/dependencies.py`.

```python
def get_identity(request: Request, authorization: Annotated[str | None, Header()] = None) -> SsoIdentity:
    """Needs a valid pass. Raises 401 otherwise."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError(401, "invalid_token", "Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise AuthError(401, "invalid_token", "Missing or invalid Authorization header")
    return request.app.state.token_verifier.verify(token)


IdentityDep = Annotated[SsoIdentity, Depends(get_identity)]


def is_admin(user_id: str) -> bool:
    return user_id in SETTINGS.auth.admin_user_ids


async def require_active_account(request: Request, identity: IdentityDep) -> dict:
    """Needs a valid pass and an approved account. Raises 403 otherwise."""
    accounts = request.app.state.user_accounts
    account = await accounts.get(identity.user_id)
    if account is None:                    # first request ever from this person
        account = await accounts.record_access(identity, client_ip(request), user_agent(request))
    if not (account["is_active"] or is_admin(identity.user_id)):
        raise AuthError(403, "account_inactive", "This account is waiting for approval")
    return account


ActiveAccountDep = Annotated[dict, Depends(require_active_account)]


async def require_session_owner(user_id: str, account: ActiveAccountDep) -> None:
    """The user_id in the address must be the caller's own."""
    if user_id != account["user_id"]:
        raise AuthError(403, "user_mismatch", "This address belongs to another user")


async def require_admin(identity: IdentityDep) -> SsoIdentity:
    if not is_admin(identity.user_id):
        raise AuthError(403, "admin_required", "Administrator access is required")
    return identity
```

`client_ip(request)` reads the header found in check 7 and falls back to `request.client.host`.
Because a caller can set that header, treat the stored address as information, not as proof.
`user_agent(request)` returns the `User-Agent` header, cut to a reasonable length.

The account is read from the database on every request (one small `SELECT`). This makes a
deactivation take effect at the person's next request. The defect agent also reads the user on
every request.

### 3.8 Endpoints

| Address | Who may call | What it does |
|---|---|---|
| `GET /health` | Anyone | Unchanged. Monitoring needs it open |
| `GET /auth/me` | Anyone with a valid pass | Runs `record_access`, returns the account plus `is_admin`. Works for unapproved people too, so the page can show "waiting for approval" |
| Everything under `/apps/users/{user_id}/...` | Valid pass, approved, own `user_id` | Unchanged behaviour |
| `GET /admin/users` | Admin | Lists accounts. Optional filter `?is_active=false` |
| `PATCH /admin/users/{user_id}` | Admin | Body `{"is_active": true}` or `false` |
| `GET /admin/users/{user_id}/access-log` | Admin | Newest visits. Optional `?limit=` |
| `GET /logs` | Admin | Unchanged behaviour. Today it is open and returns every user's questions |

About `/auth/me`: in the browser its address is `/data-agent/api/auth/me`. It is not the same as
the login service's `/auth/...` addresses, which sit at the top of the DICE address. The name is
kept because the defect agent uses `/api/auth/me`.

Reply of `/auth/me`:

```json
{
  "user_id": "alenova",
  "is_active": false,
  "is_admin": false,
  "email": "alenova@samsung.com",
  "full_name": "alenova@samsung.com",
  "department": null,
  "company": null,
  "created_at": "2026-11-19T10:00:00+09:00"
}
```

For an admin, return `is_active: true` regardless of the column, so the page needs only one rule.

How the checks are attached:

- `data_agent/routers/agent.py`: `APIRouter(prefix="/apps", tags=["runner"], dependencies=[Depends(require_session_owner)])`.
  Every route under it has `{user_id}` in its address, so the dependency receives it.
- `data_agent/routers/logs.py` and the new `data_agent/routers/admin.py`:
  `dependencies=[Depends(require_admin)]`.
- New `data_agent/routers/auth.py` for `/auth/me`, using `get_identity`.
- Register the two new routers in `data_agent/routers/__init__.py`.

### 3.9 Error replies

One exception class and one handler, in a new file `data_agent/errors.py`:

```python
class AuthError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code, self.code, self.detail = status_code, code, detail


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _auth_error(_request: Request, error: AuthError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": error.detail, "code": error.code},
            headers=headers,
        )
```

| Status | `code` | When | What the page does |
|---|---|---|---|
| 401 | `invalid_token` | No pass, bad signature, expired, wrong issuer or audience, broken identity | Get a new pass once and retry. If it fails again, go to login |
| 403 | `account_inactive` | Valid pass, person not approved | Show "waiting for approval" |
| 403 | `user_mismatch` | The `user_id` in the address is not the caller's | Programming error in the page. Show a general error |
| 403 | `admin_required` | Not in the admin list | Hide or refuse the admin function |

The shape `{"detail": ..., "code": ...}` and the `WWW-Authenticate: Bearer` header on 401 follow
the defect agent's `handlers.py`.

### 3.10 Changes to existing files

| File | Change |
|---|---|
| `common/config.py` | `AuthConfig`, `cors_origins`, two `_ENV_MAP` entries (3.2) |
| `data_agent/app.py` | In `lifespan`: create `UserAccountRepository(db_client)`, call `initialize()`, store it as `app.state.user_accounts`; create `ServiceTokenVerifier` from `SETTINGS.auth`, store it as `app.state.token_verifier`. In `create_app`: call `register_error_handlers(app)` |
| `data_agent/infra/__init__.py` | Export the two new classes |
| `data_agent/routers/__init__.py` | Include the auth and admin routers |
| `data_agent/routers/agent.py` | Router-level dependency (3.8). No change to the endpoint functions |
| `data_agent/routers/logs.py` | Router-level admin dependency |
| `data_agent/middleware/__init__.py` | Replace `allow_origins=["*"]` with `SETTINGS.cors_origins`. Once the page and the backend share one address, no other website needs access. For local frontend work, list the local address in the setting |
| `data_agent/schemas/` | New `auth.py` with the reply and request models |
| `requirements_py313_prod.txt`, `requirements_py313_dev.txt` | PyJWT |
| `config.yaml` | Optional `auth:` block with `admin_user_ids`. No secret |
| `tests/conftest.py` | Set `SERVICE_JWT_SECRET` before imports (3.2) |

Two small things to be aware of:

- The automatic API pages (`/docs`) will not load correctly through the gateway, because they ask
  for `/openapi.json` at the top of the address. Either set FastAPI's `root_path` to
  `/data-agent/api` from a setting, or leave them for direct use only.
- The request log line in `data_agent/middleware/logging.py` prints the query string, which for
  `/run` is the person's question. It does not print headers, so the pass is not logged. Keep it
  that way.

### 3.11 Tests

Test folders have no `__init__.py`, so every test file name must be unique across `tests/`.

| File | What to cover |
|---|---|
| `tests/infra/test_service_token.py` | Valid pass accepted and fields mapped. Rejected: expired, wrong secret, wrong issuer, wrong audience, `type` not `service`, missing `sub`, missing `exp`, `username` different from `sub`, empty or `null` or `undefined` identity, identity with spaces, identity with `/`, a pass signed with algorithm `none` |
| `tests/infra/test_user_repository.py` | The SQL sent for each method, with a mocked `PostgreSQLClient`, in the style of `tests/infra/test_session_lock.py` |
| `tests/routers/test_dependencies.py` | No header gives 401. Wrong scheme gives 401. Unknown person is created and gets 403. Inactive gets 403. Active passes. Admin passes while inactive. Foreign `user_id` gets 403 |
| `tests/routers/test_auth.py` | `/auth/me` for a new person, a returning person, an admin |
| `tests/routers/test_admin.py` | Non-admin gets 403. List, activate, deactivate, access log |
| `tests/routers/test_agent.py` (existing) | Add `app.dependency_overrides[require_session_owner] = lambda: None` in the `client` fixture so the existing cases keep passing |
| `tests/routers/test_logs.py` (existing) | Override `require_admin` the same way, and add one case without it that expects 401 |
| `tests/test_app.py` (existing) | Already out of step with `data_agent/app.py` (Part 8). Repair it while adding the new `lifespan` objects |

### 3.12 Testing the backend without DICE

On your own machine you choose the secret, so you can make your own pass.

Start the backend with `SERVICE_JWT_SECRET=local-test-secret` and
`AUTH_ADMIN_USER_IDS=alenova`. Then:

```python
import time, jwt

now = int(time.time())
print(jwt.encode({
    "sub": "alenova", "username": "alenova",
    "email": "alenova@samsung.com", "full_name": "alenova@samsung.com",
    "department": "Test Dept", "company": "Test Co",
    "unique_name": None, "sid": None, "roles": [],
    "type": "service", "iss": "web-auth", "aud": "dice-backend",
    "iat": now, "exp": now + 3600,
}, "local-test-secret", algorithm="HS256"))
```

```
curl -H "Authorization: Bearer PASTE_THE_PASS" http://localhost:18080/auth/me
```

Change `sub` and `username` to another name to act as a second, non-admin person.

---

## Part 4: Frontend implementation

The frontend code was not reviewed, so this part describes what it must do, not which files to
change. The reference is the defect agent's page:
`defect-studio-train-service/web/frontend/src/features/auth/`.

### 4.1 Settings

| Setting | Value |
|---|---|
| Base path of the built page | `/data-agent/` |
| Backend address | `/data-agent/api` |
| Login service address | `/auth` |

All three are relative, so the same build works on stage and on production.

### 4.2 What the page must do

1. **At start,** before showing anything: ask `/auth/session` with `credentials: 'include'`.
2. **Not authenticated:** go to `/auth/login?callbackUrl=<current address>`, once per tab. Remember
   the attempt in `sessionStorage`. If the page comes back still not authenticated, show a "log
   in" button instead of redirecting again.
3. **Authenticated:** get the pass from `/auth/token`. Keep it in memory only. Never write it to
   `localStorage`.
4. **Ask the backend who this is:** `GET /data-agent/api/auth/me`.
   - `is_active` true: start the application. Use `user_id` from the reply in all request
     addresses.
   - `is_active` false: show a "waiting for approval" screen with a "check again" button.
5. **Every backend request** carries `Authorization: Bearer <pass>`.
6. **Renew the pass** when fewer than 60 seconds remain before `expiresAt`, by asking
   `/auth/token` again.
7. **On 401 from the backend:** get a new pass and retry once. On a second 401, or a 401 from
   `/auth/token`, forget everything and go back to step 1.
8. **On 403 `account_inactive`** at any time: show the "waiting for approval" screen. This
   happens when an admin deactivates someone who is using the page.
9. **Images and downloads:** fetch them with the pass and show them from memory. The defect
   agent does this in `shared/lib/useAuthedObjectURL.ts`: fetch the bytes, call
   `URL.createObjectURL(blob)`, use the result as the image source, and release it afterwards.
10. **Logout:** a link to `/auth/logout`. Set the "already tried" marker from step 2 first, so the
    page does not log straight back in.
11. **If a different person logs in** in the same browser, clear everything the page remembers
    about the previous person. The defect agent compares the `user_id` after each renewal.

### 4.3 Sketch

Plain TypeScript, no framework. It shows the logic only.

```ts
const AUTH = '/auth';
const API = '/data-agent/api';
const TRIED = 'data-agent-sso-redirect';

let pass: string | null = null;
let expiresAt = 0;                               // unix seconds

async function authGet(path: string) {
  const res = await fetch(AUTH + path, { credentials: 'include', cache: 'no-store' });
  if (!res.ok) throw new Error('auth ' + res.status);
  return res.json();
}

function goToLogin(): boolean {
  if (sessionStorage.getItem(TRIED)) return false;        // do not loop
  sessionStorage.setItem(TRIED, '1');
  location.replace(`${AUTH}/login?callbackUrl=${encodeURIComponent(location.href)}`);
  return true;
}

async function getPass(force = false): Promise<string> {
  if (!force && pass && expiresAt > Date.now() / 1000 + 60) return pass;
  const t = await authGet('/token');                      // throws when no longer logged in
  pass = t.accessToken;
  expiresAt = t.expiresAt;
  return pass!;
}

export async function api(path: string, init: RequestInit = {}): Promise<Response> {
  const send = async (force: boolean) =>
    fetch(API + path, {
      ...init,
      headers: { ...(init.headers as Record<string, string>), Authorization: `Bearer ${await getPass(force)}` },
    });
  let res = await send(false);
  if (res.status === 401) res = await send(true);         // pass expired: renew, retry once
  return res;
}

export async function start() {
  const session = await authGet('/session');
  if (!session.authenticated) return goToLogin() ? 'redirecting' : 'signed-out';
  const res = await api('/auth/me');
  if (!res.ok) return 'error';
  sessionStorage.removeItem(TRIED);
  const me = await res.json();
  return me.is_active ? { state: 'ready', me } : { state: 'pending', me };
}
```

The "renew and retry once" behaviour is my reading of how the defect agent's page works. The
package that does it there (`@defect-studio/api-client`) was not among the files reviewed
(Part 7).

### 4.4 Things to expect

- The login cookie lasts one hour. When it runs out, `/auth/token` answers 401 and the page goes
  through the login redirect again. This is normally invisible if the person is still logged in
  to Samsung SSO, but it is a full page reload. Keep the open session ID in the address or in
  storage so the page comes back to the same place. This is from reading the login service's
  code. Confirm the real timing on stage.
- A run started before the reload keeps running in the backend. The existing `run-state`
  endpoint tells the page whether it is still in progress.

### 4.5 Working on the frontend locally

A page on `localhost` has the same cookie problem as a page on the IP address. The defect agent
solves it in its development server: it forwards `/auth` to the stage login service and uses the
stage login simulator. See `web/frontend/vite.config.ts`, `dev/stagingAuthProxy.ts` and
`.env.development` in the defect agent's frontend. This needs the stage secret on the local
backend and a login ID on the stage simulator's allowlist.

---

## Part 5: Deploying and testing on stage

### Order

1. Forwarding rule applied and checks 1 to 6 passed.
2. Backend with the authorization code, started with two new settings:

   ```
   docker run ... -e SERVICE_JWT_SECRET=... -e AUTH_ADMIN_USER_IDS=your.loginid ...
   ```

   Better: put the two lines in a file outside the repo that only the service account can read,
   and pass it with `--env-file`. Use the stage secret (`dice-stage` / `dice-stage-runtime` /
   `service-jwt`).
3. Frontend built for `/data-agent/` with the login steps.

From step 2 on, the old frontend stops working, because it sends no pass. Deploy steps 2 and 3
close together.

### End-to-end test

| Step | Expected |
|---|---|
| Open `https://stage.gtrai.sec.samsung.net/data-agent/` in a fresh browser window | Redirect to Samsung SSO, then back to the page |
| As an admin | The application starts. `user_accounts` has your row with the SSO fields filled. `user_access_log` has one row with your IP |
| As a second, non-admin person | "Waiting for approval". A row exists with `is_active = false` |
| Admin calls `PATCH /admin/users/{that id}` with `{"is_active": true}` | Reply shows `is_active: true`, `activated_by` is the admin |
| The second person presses "check again" | The application starts |
| The second person changes the `user_id` in a request address to the admin's | 403 `user_mismatch` |
| Admin deactivates the second person | Their next request gets 403 `account_inactive` |
| Reload the page several times | One new `user_access_log` row per reload |
| Leave the page open for more than an hour, then use it | It keeps working, possibly after one automatic reload |
| Press logout | You land on a DICE page and are logged out. Opening the data agent again asks for login |
| Call the backend directly with no pass: `curl http://10.240.35.180:18080/apps/users/x/sessions` | 401 |

A second person is needed for several steps. Use a colleague, a second login ID on the stage
simulator, or remove yourself from the admin list for the duration.

---

## Part 6: Going to production later

Production is a separate step with its own values.

| Item | Stage | Production |
|---|---|---|
| Address | `stage.gtrai.sec.samsung.net` | `dice.gtrai.sec.samsung.net` |
| Namespace | `dice-stage` | `dice` |
| Rule that provides `/auth` | `defect-studio-stage` | `defect-studio-prod` |
| Secret for the backend | `dice-stage-runtime`, key `service-jwt` | `dice-runtime`, key `service-jwt` |
| Routing file | `deploy/stage/routing.yaml` | A copy with the namespace, address and object names changed |

One backend can accept passes from only one environment, because stage and production sign with
different secrets. With a single server at `10.240.35.180`, either that server moves from stage
to production, or production gets its own backend and database.

Settle these before production:

1. **The production signing secret.** See Part 8, first item. Until it is replaced, anyone who
   knows it can act as any approved user.
2. **Direct access to the server.** After the change, ports 13080 and 18080 are still reachable
   by IP. The backend is protected by the pass, but Postgres on 5432 accepts connections without a
   password in the current settings, and the two MCP servers have no login. Anyone who can reach
   those ports can read the data or change `is_active` directly, without going through the data
   agent at all. Restrict these ports to the hosts that need them.
3. **The unencrypted hop.** Between the gateway and `10.240.35.180` the request travels as plain
   HTTP and carries the pass. Running the backend inside the cluster, or adding TLS on the
   server, removes this.
4. **A permanent home for the routing rule.** Applied by Argo CD from a company repo, not by
   hand.
5. **Personal data.** How long access log rows are kept.

---

## Part 7: Missing reference files and configuration

The copies in this folder are partial. The following were not available. Items 1 and 2 matter
most.

### From the defect agent's frontend (`defect-studio-train-service`)

| # | Missing | Why it matters |
|---|---|---|
| 1 | The folder `packages/`, in particular `packages/api-client` (`ApiClient`, `ApiError`, `getMe`, `provisionSso`) | It contains how the pass is attached to requests and what happens on a 401. The auth store calls `apiClient.setTokenProvider(...)` and sets a handler on it, but the receiving code is not in the copy. Part 4 fills this gap with my own reading |
| 2 | Undamaged copies of the `.tsx` and `.ts` files | In the copies, event handler code has been cut out. For example `authStore.ts` contains the line `apiClient. => {` and the login screens have buttons with no action. About 15 such lines were counted across the frontend's auth files, its tab bar, and the login and error pages of the DICE login service copy |
| 3 | `src/test/authStoreTestUtils`, `src/test/fixtures`, `src/features/threads`, `src/features/agent-run` | Referenced by the auth store and its tests. Not needed to understand the flow |

### From the defect agent's backend (`defect-studio-backend-service`)

| # | Missing | Why it matters |
|---|---|---|
| 4 | The `tests/` folder | Its cases for the pass checker would be a ready list of things to test |
| 5 | The other parts of `src/` (`thread`, `run`, `plan`, `result`, `train_data`) | They would show how the defect agent stops one person from reading another's data. Part 3 uses the address check instead |

### From DICE (`mvp-vision-ai-platform`)

| # | Missing | Why it matters |
|---|---|---|
| 6 | `infrastructure/helm/vision-ai-platform` (the Helm chart) | It would show how the login service is configured per environment |
| 7 | The platform backend's pass checker, named in a code comment as `platform/backend/app/core/web_auth.py` | A second example of checking the same pass, in Python |
| 8 | The user service (`vision-user-service`) | It already keeps `is_active` and `system_role` for each SSO user. Useful to compare with `user_accounts` |

One oddity in the copy: `service-token.ts` sits at `web-auth/web-auth/app/`, while the other
files import it from `web-auth/app/`. The content is what matters and it is complete.

### Configuration not in `DEPLOYMENT_INFO.md`

| # | Missing | Why it matters | Where to get it |
|---|---|---|---|
| 9 | The stage settings of the login service: `NEXTAUTH_URL`, `AUTH_ALLOWED_CALLBACK_PREFIXES`, `AUTH_ALLOWED_CALLBACK_ORIGINS`, `DEV_LOGIN_ENABLED`, `DEV_LOGIN_ALLOWED_IDS` | The file has these for production only. They decide whether stage uses real SSO or the simulator, and who may log in. Checks 2 and 3 find this out by trying | The stage DICE application in Argo CD, parameters of `webAuth` |
| 10 | The main forwarding rules on both addresses: `dice-vs` in `istio-system` for production, and the rules on `stage.gtrai.sec.samsung.net` including one named `cosmo-stage-vs` | Needed to be sure `/data-agent` is free, and to see how `/api/auth`, `/login` and `/_next` reach the login service | The cluster web page: all objects of kind `VirtualService` |
| 11 | The gateway object `platform-gateway` in `istio-system` | Shows which addresses and ports it serves and which namespaces may attach rules | Same web page, kind `Gateway` |
| 12 | The Argo CD application definitions (`argocd-configuration-repository`) | Needed when the routing rule is moved to Argo CD | That repo |
| 13 | Who owns the namespaces `cosmo` and `cosmo-stage` | `DEPLOYMENT_INFO.md` mentions services there. If they belong to the data agent's team, that is the natural home for its cluster objects | Ask the team |

Nothing in this list blocks the backend work in Part 3.

---

## Part 8: Problems found during the review

1. **The production signing secret looks like a placeholder.** In `DEPLOYMENT_INFO.md` the
   production value of `service-jwt` is a short, readable string, not a random key, and the same
   value is used for another key in that secret. Anyone who knows it can create a pass for any
   person on every DICE backend. The approval gate does not help against this, because a forged
   pass can name an already approved person. Changing it affects every DICE service that checks
   passes and has to be coordinated.
2. **`DEPLOYMENT_INFO.md` holds live passwords and keys in plain text** and sits uncommitted in
   this folder. This repo's remote is on github.com. Add the file and the four reference folders
   to `.gitignore`, and never use `git add .` here.
3. **`config.yaml` is committed and contains live keys** (model access keys and object storage
   keys). This is older than the authorization work, but the same repo is on github.com.
4. **`GET /logs` is open** and returns the server logs, which include people's questions. Part 3
   closes it.
5. **CORS allows every website with credentials** (`data_agent/middleware/__init__.py`). Part 3
   narrows it.
6. **`tests/test_app.py` no longer matches the code.** It imports `log_requests_middleware` and
   patches `PostgresClient`, `postgres_dsn` and `reset_session_locks`, none of which exist in the
   source. This was found by reading. The test suite was not run, because the local test
   environment no longer exists.
7. **`GET /logs` turns its own "no log files" 404 into a 500.** The `HTTPException(404)` is
   raised inside the `try` block and caught by `except Exception`. Unrelated to authorization,
   noted because the file is being changed anyway.
8. **Old sessions become invisible.** Sessions created by the test accounts are stored under
   whatever `user_id` the page sent. After the change, people only see sessions stored under
   their SSO login ID. This was accepted on 2026-11-18. The old rows and stored artifacts can be
   deleted.

---

## Part 9: Where each fact comes from

All paths are relative to the root of this repo. The four reference folders and
`DEPLOYMENT_INFO.md` are local copies and are not committed.

| Topic | File |
|---|---|
| How the pass is built and what it contains | `mvp-vision-ai-platform/web-auth/web-auth/app/service-token.ts` |
| `/auth/token` and `/auth/session` replies | `mvp-vision-ai-platform/web-auth/app/token/route.ts`, `app/session/route.ts` |
| Login, cookie names and lifetime, return address rules | `mvp-vision-ai-platform/web-auth/app/api/auth/[...nextauth]/route.ts`, `app/login/page.tsx` |
| Logout | `mvp-vision-ai-platform/web-auth/app/logout/route.ts` |
| Login simulator | `mvp-vision-ai-platform/web-auth/app/dev-login/` |
| Checking the pass in a backend | `defect-studio-backend-service/src/auth/infrastructure/service_token_verifier.py` |
| Bearer header handling and user lookup | `defect-studio-backend-service/src/common/presentation/middleware/auth.py` |
| Error reply shapes | `defect-studio-backend-service/src/common/presentation/exception_handlers/handlers.py` |
| Secret handling at startup | `defect-studio-backend-service/src/container/settings.py` |
| Rollout notes, rule about SSO groups, short keys | `defect-studio-backend-service/SSO_ROLLOUT_107.md` |
| Page-side login logic | `defect-studio-train-service/web/frontend/src/features/auth/model/authStore.ts`, `centralAuth.ts`, `ssoRedirect.ts` |
| Images with a pass | `defect-studio-train-service/web/frontend/src/shared/lib/useAuthedObjectURL.ts` |
| Local frontend development against stage | `defect-studio-train-service/web/frontend/vite.config.ts`, `dev/stagingAuthProxy.ts`, `.env.development` |
| Forwarding rules of the defect agent | `argocd-application-repository/charts/defect-studio/templates/virtualservice.yaml`, `agent-proxy.yaml`, `environments/stage/defect-studio.yaml`, `environments/production/defect-studio.yaml` |
| Login service settings (production), secret names, Argo CD applications | `DEPLOYMENT_INFO.md` |
| Data agent backend as it is today | `data_agent/app.py`, `data_agent/routers/`, `data_agent/infra/session_lock.py`, `data_agent/infra/postgresql_client.py`, `common/config.py`, `Dockerfile` |
| The forwarding rule for the data agent | `deploy/stage/routing.yaml` |
