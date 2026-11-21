# Data agent authorization: implementation guide

Written 2026-11-21. It replaces `data-agent-auth-implementation-2026-11-19.md`.

This document describes everything needed to put login and access control in front of the data
agent, in the order the work should be done. It assumes no background in authorization.

No secret values are written here on purpose. Where a secret is needed, the document says where
to find it.

Nothing in this document has been implemented yet. It is the direction to implement from.

## Contents

- [What changed since 2026-11-19](#what-changed-since-2026-11-19)
- [Summary and status](#summary-and-status)
- [Words used in this document](#words-used-in-this-document)
- [How the login works](#how-the-login-works)
- [Part 1: Change the forwarding rule on DICE](#part-1-change-the-forwarding-rule-on-dice)
- [Part 2: Check results and remaining checks](#part-2-check-results-and-remaining-checks)
- [Part 3: Backend implementation](#part-3-backend-implementation)
- [Part 4: Frontend implementation](#part-4-frontend-implementation)
- [Part 5: Deploying and testing](#part-5-deploying-and-testing)
- [Part 6: Risks to settle](#part-6-risks-to-settle)
- [Part 7: Reference files, what is still missing](#part-7-reference-files-what-is-still-missing)
- [Part 8: Problems found during the review](#part-8-problems-found-during-the-review)
- [Part 9: Where each fact comes from](#part-9-where-each-fact-comes-from)

---

## What changed since 2026-11-19

1. **Production DICE instead of stage.** Stage DICE has no Samsung SSO, only a login simulator.
   Real SSO exists only on `dice.gtrai.sec.samsung.net`. The forwarding rule was therefore added
   there, in the namespace `dice`.
2. **The checks were run.** Checks 1, 2 and 4 passed. Checks 3 and 5 did not give the expected
   result, and both are explained by how they were run, not by a fault in the setup
   ([Part 2](#part-2-check-results-and-remaining-checks)).
3. **The frontend was reviewed.** `cosmo-data-agent-frontend` is a Next.js application with its
   own server. The browser never calls the backend. It calls the frontend server, and the
   frontend server passes the call on. This is kept, and it changes the forwarding rule and
   Part 4.
4. **The forwarding rule has to be changed.** The rule now in the cluster conflicts with the
   frontend in two ways and publishes the unprotected backend on the production address
   ([Part 1](#part-1-change-the-forwarding-rule-on-dice)).
5. **The backend design is unchanged**, apart from a few small points listed at the start of
   [Part 3](#part-3-backend-implementation).

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

1. Run check 6 ([Part 2](#part-2-check-results-and-remaining-checks)). It needs the forwarding
   rule as it is now, so it comes first.
2. Replace the forwarding rule with `deploy/prod/routing.yaml`
   ([Part 1](#part-1-change-the-forwarding-rule-on-dice)).
3. Repeat checks 3 and 5 with the corrections in Part 2. Ten minutes, any time before deploying.
4. Backend: check the pass, create the two tables, add the approval gate and the admin
   endpoints ([Part 3](#part-3-backend-implementation)). This can start now. Nothing blocks it.
5. Frontend: build it to live under `/data-agent`, add the login steps, send the pass with every
   request ([Part 4](#part-4-frontend-implementation)).
6. Deploy both and test end to end ([Part 5](#part-5-deploying-and-testing)).
7. Settle the risks in [Part 6](#part-6-risks-to-settle). The first one should not wait.

**Decisions.**

| Decision | Value | Since |
|---|---|---|
| Login flow | Same as the defect agent: DICE `web-auth` signs a pass, the backend only checks it | 2026-11-17 |
| Environment | Production DICE, because it is the only one with real SSO | 2026-11-21 |
| Address of the page | `https://dice.gtrai.sec.samsung.net/data-agent` | 2026-11-21 |
| How the backend is reached | Only through the frontend server: `/data-agent/backend/...` and `/data-agent/api/chat`. The gateway does not forward to the backend | proposed 2026-11-21 |
| Where the servers run | Unchanged: `10.240.35.180` (frontend 13080, backend 18080, MCP 10420 and 10422, Postgres 5432) | 2026-11-18 |
| Existing users | None that matter (test accounts only), so no data migration | 2026-11-18 |
| Admins | A list of login IDs in the backend configuration. An admin page comes later | 2026-11-18 |
| Tables | `user_accounts` (one row per person, with everything SSO sends) and `user_access_log` (one row per visit) | 2026-11-18 |
| The 30 minute idle logout in the page | Removed. The DICE login decides how long a person stays logged in | proposed 2026-11-21 |
| Where the forwarding rule is stored | This repo, `deploy/prod/routing.yaml` | 2026-11-21 |

The two rows marked "proposed" are new in this document. Say so if you disagree with either.

**Status on 2026-11-21.**

- A forwarding rule is in the cluster (namespace `dice`, objects `data-agent-stage` and
  `data-agent-server`). It works, and it has to be replaced (Part 1).
- No authorization code exists in the backend. Every endpoint is open, and because of the rule
  above the backend is at the moment also open at
  `https://dice.gtrai.sec.samsung.net/data-agent/api/...`.
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
| Base64 | A way of writing any text using only letters and digits. Kubernetes shows secrets written this way. It is a spelling, not a protection: anyone can turn it back. The backend needs the plain value, not the base64 spelling |
| Bearer | The way the pass is sent to the backend: a request header `Authorization: Bearer <pass>` |
| Authentication | Finding out who someone is. Done by Samsung SSO and the login service |
| Authorization | Deciding what that person may do. Done by the data agent backend |
| Gateway | The entry server that receives every request for a DICE address and decides where to send it by looking at the path |
| Forwarding rule | One entry in the gateway's list: "paths starting with X go to server Y". In the cluster it is an object of kind `VirtualService` |
| `ServiceEntry` | A cluster object that gives a name to a server outside the cluster, so a forwarding rule can point at it |
| Namespace | A named area inside the cluster. Production things live in `dice`, stage things in `dice-stage` |
| Frontend server | The data agent frontend is not only a page. It is a program (Next.js) running on port 13080 that sends the page to the browser and also passes the browser's requests on to the backend |
| Base path | The first part of the page's address, here `/data-agent`. The frontend has to be built knowing it, otherwise it looks for its own files at the top of the DICE address and the page appears broken |
| Argo CD | The tool that copies configuration from Git repos onto the cluster |
| 401 / 403 | Reply codes. 401: the pass is missing or not valid, log in again. 403: the pass is valid but this person is not allowed |

---

## How the login works

### Who is involved

| Who | Address | Role |
|---|---|---|
| Browser | the person's PC | Holds the cookie and the pass |
| Gateway | `dice.gtrai.sec.samsung.net` | Forwards each request by its path |
| DICE login service | reached as `/auth/...` on the same address | Talks to Samsung SSO, stores the cookie, creates the pass |
| Samsung SSO | `sts.secsso.net` | Checks the password |
| Data agent frontend server | `10.240.35.180:13080`, reached as `/data-agent/...` | Sends the page. Passes backend requests on, unchanged, including the pass |
| Data agent backend | port 18080, reached only by the frontend server | Checks the pass, decides access |

### The steps

1. The person opens `https://dice.gtrai.sec.samsung.net/data-agent`. The gateway forwards the
   request to the frontend server, which sends the page.
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
7. The page calls `GET /data-agent/backend/auth/me` with the header
   `Authorization: Bearer <pass>`. The frontend server passes this on to the backend as
   `GET /auth/me` with the same header.
8. The backend checks the pass. It creates or updates the person's row in `user_accounts`, adds a
   row to `user_access_log`, and answers with the account, including `is_active`.
9. If `is_active` is false, the page shows "waiting for approval". Otherwise the page starts
   normally. Every later request carries the same header, and the page uses the `user_id` from
   step 8 in the existing `/apps/users/{user_id}/...` addresses.
10. About a minute before `expiresAt` the page asks `/auth/token` again for a new pass. If the
    backend ever answers 401, the page forgets the pass and starts again at step 2. The logout
    link goes to `/auth/logout`.

Two things differ from the defect agent, and neither is visible to the person:

- In step 7 the defect agent's page calls its backend directly through the gateway
  (`/defect/api/...`). The data agent's page calls its own frontend server, which passes the call
  on. The pass, the header and the check in the backend are the same.
- In step 8 the defect agent creates the account and lets the person in immediately. The data
  agent waits for an admin's approval.

Nothing has to be registered with Samsung SSO for the data agent. Samsung SSO only ever sends the
browser back to the login service.

### Why the address matters

The cookie from step 4 belongs to the address `dice.gtrai.sec.samsung.net`. The browser shows it
only to pages opened under that address. A page opened as `http://10.240.35.180:13080` never gets
it, so step 2 always answers "not authenticated" and login cannot finish. This is the only reason
the forwarding rule in Part 1 is needed. The servers themselves do not move.

The return address in step 3 must also be on `dice.gtrai.sec.samsung.net`. The production login
service accepts a return address on its own website, or on a website listed in its setting
`AUTH_ALLOWED_CALLBACK_ORIGINS`, which holds only that same address. Anything else is replaced by
the DICE home page. No setting of the login service has to be changed for the data agent.

### What the pass contains

The login service builds the pass in `web-auth/app/service-token.ts`. It is signed with the
algorithm HS256.

| Field | Content | Seen in the real pass (check 4) |
|---|---|---|
| `sub` | Login ID. This is the data agent's `user_id` | The login ID, with a dot in it (`firstinitial.lastname`) |
| `username` | Same login ID. The backend requires it to equal `sub` | Equal to `sub` |
| `email` | SSO `upn` (the email), or null | `<login id>@samsung.com` |
| `full_name` | `upn`, else `unique_name`, else the login ID | The email again. SSO sends no real display name |
| `department` | SSO `deptname`, or null | Filled, Korean text |
| `company` | SSO `busname`, or null | Filled, Korean text |
| `unique_name` | SSO `unique_name`, or null | `CORP\<login id>` |
| `sid` | SSO `sid`, or null | Starts with `S-1-5-21-`. This is the permanent Windows account identifier, so it stays the same for a person across logins |
| `roles` | List built from SSO `groups` and `role` | Empty list |
| `type` | Always `service` | `service` |
| `iss` | Always `web-auth`. Who issued the pass | `web-auth` |
| `aud` | Always `dice-backend`. Who the pass is for | `dice-backend` |
| `iat`, `exp` | Issue time and expiry time, in unix seconds | One hour apart |

What this confirms for the design:

- `roles` is empty for a normal person, so SSO cannot tell the data agent who is an admin. The
  admin list in the backend configuration is needed.
- `sub` contains a dot and nothing else unusual. It is safe in addresses and in storage keys.
- The `id` shown by `/auth/session` is not the login ID. It is an internal value of Samsung SSO.
  Do not use it. The data agent's `user_id` is `sub` from the pass.

---

## Part 1: Change the forwarding rule on DICE

### What is in the cluster now

Added by hand in namespace `dice`:

| Object | Name | What it does |
|---|---|---|
| `ServiceEntry` | `data-agent-server` | Registers `10.240.35.180` under the name `data-agent.external.local`, with ports 13080 and 18080 |
| `VirtualService` | `data-agent-stage` | On `dice.gtrai.sec.samsung.net`: redirects `/data-agent` to `/data-agent/`, sends `/data-agent/api/...` to port 18080 with `/data-agent/api` removed, and sends `/data-agent/...` to port 13080 |

Check 1 proved that it works: the gateway reaches the server, and nothing else on the production
address uses paths starting with `/data-agent`.

### Why it has to change

1. **It takes the frontend's own address away.** The frontend has a server address `/api/chat`,
   which is where every question is sent. Built for `/data-agent`, that becomes
   `/data-agent/api/chat`. The current rule sends everything under `/data-agent/api/` to the
   backend instead, where `/chat` does not exist. Sending a question would always fail.
2. **It loops.** The current rule redirects `/data-agent` to `/data-agent/`. A Next.js frontend
   redirects `/data-agent/` back to `/data-agent`, both today and after it is built for
   `/data-agent`. The browser bounces between the two until it gives up with a message about
   too many redirects. If that message is what you saw when the page "looked broken", this is
   the cause.
3. **It publishes the unprotected backend.** Until Part 3 is deployed,
   `https://dice.gtrai.sec.samsung.net/data-agent/api/...` lets anyone on the company network
   read, run and delete any session, and download the server logs (`/logs`). The backend was
   already reachable by IP address before, but now it also sits on the production DICE address.
4. **It is not needed.** The browser only talks to the frontend server. The frontend server
   reaches the backend inside the server machine. The gateway has no reason to know the backend.

One more change is included: the new rule removes cookies from requests before forwarding them.
The data agent does not use cookies, and without this the DICE login cookie of every visitor
would travel unencrypted from the cluster to `10.240.35.180` with every request.

### The new rule

`deploy/prod/routing.yaml`. Two objects in namespace `dice`:

| Object | Name | What it does |
|---|---|---|
| `ServiceEntry` | `data-agent-server` | Registers `10.240.35.180` with port 13080 only |
| `VirtualService` | `data-agent` | On `dice.gtrai.sec.samsung.net`: sends `/data-agent` and `/data-agent/...` to port 13080, unchanged and without cookies. Also redirects http to https |

The login paths (`/auth/...`) are not in the file. They are already forwarded on this address by
the defect agent's rule `defect-studio-prod`. This means data agent login depends on that rule
staying in place.

### How to change it through the cluster web page

Do check 6 in Part 2 first. It uses the old rule.

1. Open the Kubernetes web page you used before and set the namespace selector to `dice`.
2. Delete the `VirtualService` named `data-agent-stage`.
3. Delete the `ServiceEntry` named `data-agent-server`.
4. Create the new objects the same way as last time: open `deploy/prod/routing.yaml`, copy the
   whole content, paste it into the "create from YAML" box, and confirm. If the page refuses two
   objects at once, paste the part above the `---` line first, then the part below it.

Deleting first matters. If the old `data-agent-stage` rule stays next to the new one, both apply
and the loop from point 2 above can still happen.

Between step 2 and step 4 the address `/data-agent` does not answer. Nobody uses it yet.

### The same thing with commands

On a computer where `kubectl` is installed and connected to the cluster:

```
kubectl delete virtualservice data-agent-stage -n dice
kubectl delete serviceentry data-agent-server -n dice
kubectl apply -f deploy/prod/routing.yaml --dry-run=server     # checks the file, changes nothing
kubectl apply -f deploy/prod/routing.yaml
```

### Check that it works

Open `https://dice.gtrai.sec.samsung.net/data-agent/` in a browser.

- Before the frontend is rebuilt (Part 4): the address bar changes to `/data-agent` and the page
  is blank or broken. That is expected, because the current frontend does not yet know it lives
  under `/data-agent` and looks for its files in the wrong place. What matters at this point is
  what you do not see: no error 503 and no message about too many redirects.
- After the frontend is rebuilt: the address bar changes to `/data-agent/chat/new` and the data
  agent appears. This is the real check.

`https://dice.gtrai.sec.samsung.net/data-agent/api/health` no longer shows the backend's health
reply after this change. That is intended.

### If the check fails

| What you see | Likely cause | What to do |
|---|---|---|
| The web page refuses the file and names `headers` | This cluster does not accept the cookie removal | Delete the four lines from `headers:` to `- cookie` in the file and create it again. Forwarding works without them. Then tell me, because Part 6 item 3 changes |
| Error 503 | The cluster cannot reach `10.240.35.180:13080` | Check that the frontend container is running on the server |
| The browser reports too many redirects | The old `data-agent-stage` rule still exists | Delete it (step 2) |
| Another product's page | An older rule on the same address catches `/data-agent` first | Did not happen with the old rule, so it should not happen now. List all `VirtualService` objects for `dice.gtrai.sec.samsung.net` |

### Undo

Delete the two objects `data-agent` (kind `VirtualService`) and `data-agent-server` (kind
`ServiceEntry`) in namespace `dice`. With commands: `kubectl delete -f deploy/prod/routing.yaml`.

### Why this is safe

- The rule only handles paths that start with `/data-agent`. Check 1 showed that no other product
  on the production address uses such paths.
- Argo CD only manages objects it created. It will not remove objects added by hand.

### Not verified

- The cookie removal lines have not been tried on this cluster. The table above says what to do
  if they are refused.
- That a Next.js frontend built for `/data-agent` redirects `/data-agent/` to `/data-agent` was
  read from the Next.js version installed in the frontend repo (16.3.3). It has not been watched
  happening through the gateway.

### Making it permanent later

An object added by hand is not recorded anywhere except the cluster. Once everything works, the
rule should be applied by Argo CD from a Git repo, the way the defect agent's rule is. Argo CD
has to be able to read that repo. This repo's remote is on github.com, which the cluster's Argo
CD very likely cannot read, so the file would have to live in a repo on the company's GitHub.

`deploy/stage/routing.yaml` was never applied anywhere and is marked as not in use.

---

## Part 2: Check results and remaining checks

### Overview

| # | Check | Result | What is left to do |
|---|---|---|---|
| 1 | The forwarding rule works | Passed | Nothing |
| 2 | The login service answers on the address | Passed | Nothing |
| 3 | Logging in returns you to the data agent address | Not answered yet. The test used a return address on the stage website | Repeat with the corrected address below |
| 4 | Look inside a real pass | Passed. Contents are in "What the pass contains" above | Nothing |
| 5 | The secret verifies the pass | Failed, because the secret was pasted in its base64 spelling. With the plain value it verifies. I checked this on 2026-11-21 with your pass and the values in `DEPLOY_CONFIG_261121.md` | Repeat once with the script below, so you have seen it work |
| 6 | A long agent run survives the gateway | Not run | Run it now, before Part 1 |
| 7 | Where the real IP address arrives | Open | During backend and frontend work |
| 8 | Questions about the frontend | Answered by reading the frontend. See Part 4 | Nothing |
| 9 | The JWT library in the backend environment | Open | One command, below |
| 10 | The admin list | Answered: your login ID, exactly as shown in `sub` in check 4 | Add other admins when you know them |
| 11 | Fetch the missing references | Mostly done. See Part 7 | Nothing that blocks |

### Check 3 again: logging in returns you to the data agent address

What happened: the address you opened was on `dice.gtrai.sec.samsung.net`, but the `callbackUrl`
inside it still said `stage.gtrai.sec.samsung.net`. The login service does not send people to
another website after login, so it sent you to the DICE home page. The login itself worked,
which your second look at `/auth/session` showed.

Open a private browser window (so you start logged out) and open this address (one line):

```
https://dice.gtrai.sec.samsung.net/auth/login?callbackUrl=https%3A%2F%2Fdice.gtrai.sec.samsung.net%2Fdata-agent
```

- Expected: Samsung SSO appears, or you are logged in silently. Afterwards the address bar shows
  `https://dice.gtrai.sec.samsung.net/data-agent`, with or without a `/` at the end. The page
  itself may be blank, broken, or a message about too many redirects (see Part 1). What matters
  is that the address is the data agent's and not the DICE home page.
- If you land on the DICE home page again: send me the exact address you opened. From reading
  the login service code this should not happen for an address on the same website.

### Check 5 again: the secret verifies the pass

Why it failed: a Kubernetes secret is displayed in its base64 spelling. The value you pasted,
ending in `==`, is that spelling. The login service signs with the plain value behind it.

Get a fresh pass from `https://dice.gtrai.sec.samsung.net/auth/token` (the old one has expired),
then run:

```python
import base64, jwt

token = "PASTE THE accessToken HERE"
shown = "PASTE THE SECRET AS THE KUBERNETES PAGE SHOWS IT"

secret = base64.b64decode(shown).decode()      # turn the base64 spelling back into the plain value
print(jwt.decode(token, secret, algorithms=["HS256"], issuer="web-auth",
                 audience="dice-backend", options={"require": ["exp", "sub"]}))
```

- Expected: the fields from check 4 are printed, with one warning line that mentions
  `InsecureKeyLengthWarning`. The warning means the production secret is shorter than
  recommended. It does not stop the check. See Part 6 item 1.
- Where the secret is: namespace `dice`, secret `dice-runtime`, key `service-jwt`. The secret
  `defect-studio-prod-secrets`, key `service-jwt-secret`, holds the same value.
- The value to give the backend later is the plain one, which is what `secret` holds in this
  script. If your Kubernetes page has an eye icon that reveals the plain value, that is the same
  thing.
- Do not save the script with the secret in it. Do not paste secrets or passes into chats,
  tickets or websites. A pass works as your login for an hour.

### Check 6: a long agent run survives the gateway

The `/run` endpoint keeps one request open until the agent has finished. Some gateways cut a
request on which nothing is sent for several minutes. Whether this one does is not known.

Run this now, while the old forwarding rule and the open backend still exist:

```
curl -X POST "https://dice.gtrai.sec.samsung.net/data-agent/api/apps/users/routing-test/sessions"
curl -X POST "https://dice.gtrai.sec.samsung.net/data-agent/api/apps/users/routing-test/sessions/SESSION_ID/run?query=YOUR%20LONGEST%20REALISTIC%20QUESTION"
```

The first command prints a `session_id`. Put it in place of `SESSION_ID` in the second one.

- Expected: the answer arrives, however long the run takes.
- If the request is cut with a 504 or a reset after a fixed time: this is not an authorization
  problem, but it limits how long a question may run through the gateway. Tell me the time at
  which it was cut. The fix depends on that time.

After Part 1 these two addresses no longer exist. The same test can then only be done from the
page.

Separate from the gateway, and already true today: as far as I know the frontend server waits at
most about five minutes for the backend's answer (a default of Node.js, not confirmed for this
frontend). A cut at five minutes that also happens without the gateway points there.

### Check 7: where the real IP address arrives

The backend will see every request as coming from the frontend server, not from the person's PC.
The real address arrives at the frontend server in the request header `X-Forwarded-For` or
`X-Envoy-External-Address`, and the frontend server has to pass that header on (Part 4).

How: during the work, temporarily log both headers on one backend endpoint, open the page from a
PC whose IP you know, and compare. Then fix which header and which position `client_ip` reads.

### Check 9: the JWT library in the backend environment

In the environment the backend runs in, run `pip show pyjwt`.

- If it is listed: note the version and pin exactly that version in both requirements files. It
  is very likely already installed, because the `mcp` package depends on it.
- If it is not listed: add the current PyJWT 2.x release to both requirements files.

The check on 2026-11-21 used PyJWT 2.15.1.

---

## Part 3: Backend implementation

All paths in this part are in this repo.

This part is the 2026-11-19 design. The new files and check results confirmed it. These points
changed:

| Section | Change |
|---|---|
| 3.2 | The secret is the production one, in its plain form, not the base64 spelling |
| 3.3 | The key length warning is confirmed for the production secret |
| 3.4 | A note on why none of the checks may be relaxed |
| 3.7 | The real IP address reaches the backend only if the frontend server passes it on |
| 3.8 | The address of `/auth/me` as the browser sees it |
| 3.9 | What the page does on `user_mismatch` |
| 3.10 | CORS becomes an empty list. The remark about `/docs` |

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
- The value is the production secret (`dice` / `dice-runtime` / `service-jwt`) in its plain
  form. The base64 spelling that Kubernetes displays does not work. Check 5 in Part 2 shows how
  to get the plain form and how to prove it is the right one.
- Because `auth` has no default, the backend refuses to start when the secret is missing. This
  matches the defect agent, where a missing or placeholder secret fails startup.
- `SETTINGS` is built when `common.config` is imported. The tests therefore need the variable set
  before that import. Put `os.environ.setdefault("SERVICE_JWT_SECRET", "test-secret-for-unit-tests")`
  at the very top of `tests/conftest.py`, above the other imports.

### 3.3 Library

Add PyJWT to `requirements_py313_prod.txt` and `requirements_py313_dev.txt` (see check 9).

The defect agent uses `python-jose==3.3.0`. PyJWT is the better maintained of the two and does the
same job. PyJWT prints `InsecureKeyLengthWarning` when the secret is shorter than 32 bytes. The
production secret is 22 bytes, so this warning appears (seen with PyJWT 2.15.1 on 2026-11-21).
The pass is still checked correctly. Do not turn on any strict key-length option, or every
login fails. The warning is right about the secret, though: see Part 6 item 1.

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

Keep every check above, including issuer, audience and `type`. The same secret also signs other
tokens inside DICE that are not logins: the platform backend creates short tokens for its calls
to the labeler (`iss` is `platform`, `aud` is `labeler`) and tokens for calls between services
(no `iss`, no `aud`). The DICE platform's own checker skips the audience check. With the checks
above, both kinds are refused. This was tried on 2026-11-21 with PyJWT 2.15.1: passing `issuer=`
and `audience=` makes both fields required.

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
The backend's direct caller is always the frontend server, so the header only exists if the
frontend server passes it on (Part 4, section 4.5).
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

About `/auth/me`: in the browser its address is `/data-agent/backend/auth/me`, because the page
reaches the backend through the frontend server. It is not the same as the login service's
`/auth/...` addresses, which sit at the top of the DICE address. The name is kept because the
defect agent uses `/api/auth/me`.

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
| 403 | `user_mismatch` | The `user_id` in the address is not the caller's | Reload the page. A different person has logged in to DICE in this browser and the page still holds the previous `user_id` |
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
| `data_agent/middleware/__init__.py` | Replace `allow_origins=["*"]` with `SETTINGS.cors_origins`, which stays an empty list. No browser calls the backend directly, on the server or in local work: the frontend server makes the calls, and CORS does not apply to it |
| `data_agent/schemas/` | New `auth.py` with the reply and request models |
| `requirements_py313_prod.txt`, `requirements_py313_dev.txt` | PyJWT |
| `config.yaml` | Optional `auth:` block with `admin_user_ids`. No secret |
| `tests/conftest.py` | Set `SERVICE_JWT_SECRET` before imports (3.2) |

Two small things to be aware of:

- The automatic API pages (`/docs`) are for direct use on port 18080 only. They are not meant to
  be opened through the DICE address.
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

The frontend is the repo `cosmo-data-agent-frontend`. All paths in this part are in that repo.
The reference is the defect agent's page (`defect-studio-train-service/web/frontend/src/features/auth/`)
and its request code (`defect-studio-train-service/packages/api-client/src/utils/api-client.ts`).

### 4.1 What the frontend is today

- A Next.js application (version 16) with its own server on port 13080.
- The browser never calls the backend. It calls two addresses on the frontend server, and the
  frontend server passes the call on to the backend at `BACKEND_ORIGIN`:
  - `/backend/...` for everything except sending a question (`src/app/backend/[...path]/route.ts`)
  - `/api/chat` for sending a question (`src/app/api/chat/route.ts`)
- There is no login. A form asks for a Knox ID, keeps it in the browser's storage under
  `mock_user_id`, and forgets it after 30 minutes without activity
  (`src/providers/user-provider.tsx`, `src/components/user-gate.tsx`). Whatever is typed becomes
  the `user_id`.
- Uploaded images are already fetched by code and shown from memory
  (`SessionStorage.loadArtifact`), not by a plain `<img src>`. Nothing has to be redesigned for
  images. They only need the pass like every other request.
- It is built to live at the top of an address, not under `/data-agent`.

This design is kept. Passing calls through the frontend server means one forwarding rule, no
backend on the gateway, and the fewest changes to the page.

### 4.2 Settings

| Setting | Value | Where |
|---|---|---|
| Base path | `/data-agent` | New build setting `NEXT_PUBLIC_BASE_PATH`, used as `basePath` in `next.config.mjs` and as a `--build-arg` in the `Dockerfile` |
| Backend address | Unchanged: `BACKEND_ORIGIN`, read by the frontend server only | `run_da_frontend.sh` |
| Login service address | `/auth` | A constant in the page. It is at the top of the DICE address, not under the base path |

Making the base path a setting keeps local work possible at `http://localhost:3000/` with the
setting left empty.

### 4.3 Addresses that need the base path added by hand

Next.js adds the base path by itself to page links, `router.push`, `router.replace`, the redirect
in `next.config.mjs`, its own script and font files, and the icon. `usePathname()` keeps
returning the path without the base path, so the comparison in `user-gate.tsx` keeps working.

Next.js does not touch addresses the code writes itself. These need the base path in front:

| File and line | Now |
|---|---|
| `src/components/chat/chat-view.tsx:517` | `fetch("/api/chat", ...)` |
| `src/lib/session-api.ts`, eight calls | `fetch(API_BASE + ...)` with `API_BASE = "/backend"` |
| `src/components/chat/chat-view.tsx:183` | `fetch("/suggested-questions.json")` |
| `src/components/chat/chat-view.tsx:369` and `:468` | `window.history.replaceState(null, "", "/chat/...")` |
| `src/components/chat/session-sidebar.tsx:215` | `window.location.pathname === "/chat/..."` |

The first two rows are covered by sending those calls through one helper (`apiFetch` in 4.6)
that adds both the base path and the pass.

### 4.4 What the page must do

1. **At start,** before showing anything: ask `/auth/session` with `credentials: 'include'`.
2. **Not authenticated:** go to `/auth/login?callbackUrl=<current address>`, once per tab. Remember
   the attempt in `sessionStorage`. If the page comes back still not authenticated, show a "log
   in" button instead of redirecting again.
3. **Authenticated:** get the pass from `/auth/token`. Keep it in memory only. Never write it to
   `localStorage`.
4. **Ask the backend who this is:** `GET /data-agent/backend/auth/me`.
   - `is_active` true: start the application. Use `user_id` from the reply wherever the typed
     Knox ID is used today.
   - `is_active` false: show a "waiting for approval" screen with a "check again" button.
5. **Every request to the frontend server** (`/backend/...` and `/api/chat`) carries
   `Authorization: Bearer <pass>`.
6. **Renew the pass** when fewer than 60 seconds remain before `expiresAt`, by asking
   `/auth/token` again. Because the pass is fetched before a request is sent, an ended login is
   noticed before a question leaves the page.
7. **On 401 from the backend:** get a new pass. Send the request again once if it was a read
   (GET). The defect agent's request code does exactly this. On a second 401, or a 401 from
   `/auth/token`, forget everything and go back to step 1.
8. **On 403 `account_inactive`** at any time: show the "waiting for approval" screen. This
   happens when an admin deactivates someone who is using the page.
9. **On 403 `user_mismatch`:** reload the page. It means a different person logged in to DICE in
   this browser, and the page still holds the previous person's `user_id`.
10. **Logout:** go to `/auth/logout`. Set the "already tried" marker from step 2 first, so the
    page does not log straight back in. This logs the person out of all of DICE, not only the
    data agent, which is also what the defect agent does.

The frontend server does only one thing for all of this: it passes the `Authorization` header on
to the backend. It does not check the pass and it does not hold the secret. The backend stays
the only place that decides.

### 4.5 Files to change

| File | Change |
|---|---|
| `next.config.mjs` | `basePath` from `NEXT_PUBLIC_BASE_PATH` |
| `Dockerfile`, `.env.example` | The new build setting, with `/data-agent` as the value for the server build |
| `src/lib/auth-client.ts` (new) | Session, pass, login and logout addresses, the "already tried" marker, and `apiFetch` (4.6) |
| `src/providers/user-provider.tsx` | Replace the stored Knox ID by the state from `start()` in 4.6: `loading`, `redirecting`, `signed-out`, `pending`, `ready`, `error`. `userId` becomes `user_id` from `/auth/me`. Remove the idle timer, `keepAlive` and `mock_user_id` |
| `src/components/user-gate.tsx` | Replace the Knox ID form by one screen per state: nothing while loading, a "log in" button when signed out, "waiting for approval" with "check again" when pending, a retry when error |
| `src/lib/session-api.ts` | All eight `fetch` calls go through `apiFetch` |
| `src/components/chat/chat-view.tsx` | `/api/chat` goes through `apiFetch` (line 517). Look at `response.ok` before reading the reply (line 522): today a 401 or 403 would be shown as the general error line. Base path for the three addresses in 4.3 |
| `src/components/chat/session-sidebar.tsx` | The logout button (`handleLogout`, line 271) does step 10. Base path in the comparison on line 215 |
| `src/app/backend/[...path]/route.ts` | Line 34 passes on only `accept` and `content-type`. Add `authorization`, and for the access log `x-forwarded-for`, `x-envoy-external-address` and `user-agent` |
| `src/app/api/chat/route.ts` | Read `authorization` from the incoming request and add it to both backend calls (lines 68 and 73), together with the same three headers. Keep returning the backend's status code and body unchanged, so the page can read `code` |

### 4.6 Sketch

It shows the logic only.

```ts
// src/lib/auth-client.ts
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
const AUTH = "/auth";                          // top of the DICE address, not under BASE_PATH
const TRIED = "data-agent-sso-redirect";

let pass: string | null = null;
let expiresAt = 0;                             // unix seconds
let renewing: Promise<string> | null = null;   // one renewal at a time

export class LoginEnded extends Error {}

async function authGet(path: string) {
  const res = await fetch(AUTH + path, { credentials: "include", cache: "no-store" });
  if (res.status === 401) throw new LoginEnded();
  if (!res.ok) throw new Error("auth " + res.status);
  return res.json();
}

export function goToLogin(): boolean {
  if (sessionStorage.getItem(TRIED)) return false;          // do not loop
  sessionStorage.setItem(TRIED, "1");
  location.replace(`${AUTH}/login?callbackUrl=${encodeURIComponent(location.href)}`);
  return true;
}

function getPass(force = false): Promise<string> {
  if (!force && pass && expiresAt > Date.now() / 1000 + 60) return Promise.resolve(pass);
  renewing ??= authGet("/token")
    .then((t) => { pass = t.accessToken; expiresAt = t.expiresAt; return pass!; })
    .finally(() => { renewing = null; });
  return renewing;
}

// path is "/backend/..." or "/api/chat"
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const send = async (force: boolean) => {
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${await getPass(force)}`);
    return fetch(BASE_PATH + path, { ...init, headers });
  };
  let res = await send(false);
  const isRead = ["GET", "HEAD"].includes((init.method ?? "GET").toUpperCase());
  if (res.status === 401 && isRead) res = await send(true);  // pass expired: renew, retry once
  return res;
}

export async function start() {
  const session = await authGet("/session");
  if (!session.authenticated) return { state: goToLogin() ? "redirecting" : "signed-out" };
  const res = await apiFetch("/backend/auth/me");
  if (res.status === 401) return { state: goToLogin() ? "redirecting" : "signed-out" };
  if (!res.ok) return { state: "error" };
  sessionStorage.removeItem(TRIED);
  const me = await res.json();
  return { state: me.is_active ? "ready" : "pending", me };
}
```

```ts
// src/app/backend/[...path]/route.ts, the list of headers that are passed on
for (const name of ["accept", "content-type", "authorization",
                    "x-forwarded-for", "x-envoy-external-address", "user-agent"]) {
```

### 4.7 Things to expect

- **A reload about once an hour.** The DICE login cookie lasts one hour, and asking for a pass
  does not extend it. When it runs out, `/auth/token` answers 401 and the page goes through the
  login redirect again. This is normally invisible if the person is still logged in to Samsung
  SSO, but it is a full page reload. The page already survives reloads: the open session is in
  the address, an unsent draft is kept in the browser's storage, and a run that is still going
  is picked up through `run-state`. This is from reading the login service's code. Confirm the
  real timing on the page.
- **The idle logout goes away.** With real login, a timer in the page cannot end the DICE login.
  It could only hide the page.
- **Everyone starts as "waiting for approval",** including you, unless your login ID is in the
  admin list when the backend starts.
- **Old test sessions.** A session stored under a typed Knox ID stays visible only if that ID,
  in lower case, equals the person's SSO login ID.

### 4.8 Working on the frontend locally

A page on `localhost` has no DICE cookie, so the real login cannot finish there. Two ways exist,
and neither is needed to finish Part 3:

- Backend only: run it with your own secret and make your own pass (Part 3, section 3.12).
- Page and backend together: the defect agent forwards `/auth` from its development server to
  the stage login service and uses the stage login simulator
  (`web/frontend/vite.config.ts`, `dev/stagingAuthProxy.ts`, `.env.development`). The data
  agent can do the same later. It needs the stage secret on the local backend and your login ID
  on the stage simulator's allowlist.

---

## Part 5: Deploying and testing

There is one data agent, and it now sits on the production DICE address. There is no separate
test copy. The approval gate is what keeps other people out while you test.

### Order

1. Check 6, then the new forwarding rule (Parts 1 and 2).
2. Backend with the authorization code, started with two new settings:

   ```
   docker run ... --env-file /path/outside/the/repo/da-backend.env ...
   ```

   The file holds two lines and should be readable only by the account that runs the container:

   ```
   SERVICE_JWT_SECRET=<plain value of dice-runtime / service-jwt>
   AUTH_ADMIN_USER_IDS=<your login id>
   ```

   From this moment the old page stops working, because it sends no pass.
3. Frontend with the changes of Part 4, built with `--build-arg NEXT_PUBLIC_BASE_PATH=/data-agent`.

Never do step 3 before step 2. The new frontend makes the backend reachable from the production
address (`/data-agent/backend/...`), so the backend must already be checking passes.

Deploy steps 2 and 3 close together. After step 3 the page works only through
`https://dice.gtrai.sec.samsung.net/data-agent`. Opened by IP address it cannot log in, because
the login service and its cookie do not exist on that address.

### End-to-end test

| Step | Expected |
|---|---|
| Open `https://dice.gtrai.sec.samsung.net/data-agent` in a private browser window | Redirect to Samsung SSO, then back to `/data-agent/chat/new` |
| As an admin | The application starts. `user_accounts` has your row with the SSO fields filled. `user_access_log` has one row with your IP |
| Send a question, with and without an image | The answer arrives. The image shows again after a reload |
| As a second, non-admin person | "Waiting for approval". A row exists with `is_active = false` |
| Admin calls `PATCH /data-agent/backend/admin/users/{that id}` with `{"is_active": true}` | Reply shows `is_active: true`, `activated_by` is the admin |
| The second person presses "check again" | The application starts |
| The second person changes the `user_id` in a request address to the admin's | 403 `user_mismatch` |
| Admin deactivates the second person | Their next request gets 403 `account_inactive` and the page shows "waiting for approval" |
| Reload the page several times | One new `user_access_log` row per reload |
| Leave the page open for more than an hour, then use it | It keeps working after one automatic reload |
| Press logout | You land on a DICE page and are logged out. Opening the data agent again asks for login |
| Call the backend directly with no pass: `curl http://10.240.35.180:18080/apps/users/x/sessions` | 401 |
| Open `https://dice.gtrai.sec.samsung.net/data-agent/api/health` | Not the backend's health reply |

A second person is needed for several steps. Use a colleague, or remove yourself from the admin
list for the duration. The admin endpoints have no page yet. Call them with a pass in the
`Authorization` header, for example from the browser's developer tools on the data agent page.

---

## Part 6: Risks to settle

The data agent now trusts production passes and sits on the production address. These points
were "later" in the previous version. The first one is not "later" any more.

1. **The production signing secret is a guessable placeholder.** Its plain value is a short
   English phrase of 22 characters, and the same phrase is also stored under another key of the
   same secret. Anyone who knows or guesses it can create a pass for any person, including a
   data agent admin, without logging in. The approval gate does not help, because a forged pass
   can name an approved person. The data agent's own ports are reachable by IP address (item 2),
   so such a pass does not even have to go through DICE.

   Replacing the secret is a DICE-wide change. All of these have to change at the same moment:
   - `dice-runtime`, key `service-jwt` (the login service and the DICE backends)
   - `defect-studio-prod-secrets`, key `service-jwt-secret` (the defect agent backend)
   - the data agent's `SERVICE_JWT_SECRET`

   One obstacle: the defect agent backend also reads its message queue password
   (`RABBITMQ_PASSWORD`) from that same key. Changing the key changes that password too, so the
   two have to be separated first.

   You are a DICE admin, so this is yours to raise. A random value of 32 bytes or more is what
   is needed, for example the output of `openssl rand -hex 32`.
2. **Direct access to the server.** Ports 13080 and 18080 on `10.240.35.180` stay reachable by
   IP address. After Part 3 both are protected by the pass. Postgres on 5432 accepts connections
   without a password in the current settings, and the two MCP servers have no login. Anyone who
   can reach those ports can read the data or change `is_active` directly. Restrict 5432, 10420
   and 10422 to the server itself, and 13080 to the cluster. Port 18080 does not need to be
   published at all, because the frontend container reaches the backend over the Docker network.
3. **The unencrypted hop.** Between the gateway and `10.240.35.180` requests travel as plain
   HTTP and carry the pass. A pass works on every DICE backend for up to an hour. The new
   forwarding rule at least keeps the DICE login cookie off that hop. Running the data agent
   inside the cluster, or adding TLS on the server, removes the problem.
4. **Login depends on another product's rule.** `/auth` on the production address is forwarded
   by the defect agent's rule `defect-studio-prod`. If that rule is removed or its `/auth` part
   changes, data agent login stops.
5. **No test environment.** Every change is tested on the production address. Keep the admin
   list short and approve people deliberately.
6. **A permanent home for the forwarding rule.** Applied by Argo CD from a company repo, not by
   hand (Part 1).
7. **Personal data.** `user_accounts` and `user_access_log` hold email, department, company and
   IP addresses. Check whether company rules require a retention limit.

---

## Part 7: Reference files, what is still missing

### Provided on 2026-11-21, and what they settled

| Provided | What it settled |
|---|---|
| `defect-studio-train-service/packages/api-client` | How the defect agent's page attaches the pass and reacts to a 401: it renews the pass, sends the request again once if it was a read, and otherwise ends the session. Part 4 follows it |
| `defect-studio-backend-service/src/thread`, `src/plan` | How the defect agent stops one person from reading another's data: every query is limited to the user taken from the pass. The data agent keeps `user_id` in its addresses and refuses a foreign one, which has the same effect |
| `mvp-vision-ai-platform/platform/backend/app/core` | A second pass checker (`web_auth.py`). It also showed that the same secret signs other kinds of DICE tokens. See the note in Part 3, section 3.4 |
| `mvp-vision-ai-platform/infrastructure/helm/vision-ai-platform` | The login service's settings per environment. Its forwarding rules are not in the chart |
| `DEPLOY_CONFIG_261121.md` | The production settings of the login service, which explain check 3, and the secrets as Kubernetes stores them, which explain check 5 |

### Still damaged

In the copies of `.tsx` and `.ts` files, event handler code is still cut out. Examples:
`authStore.ts` line 195 reads `apiClient. => {`, and the login pages have buttons with no
action. The cut text always starts with `on` (`onClick=`, `onChange=`, `onUnauthorized =`), so
something on the way removes it. The missing words can be worked out from the surrounding code
(line 195 is `apiClient.onUnauthorized = () => {`). This does not block anything.

### Still missing, none of it blocking

| Missing | Why it would help | Where to get it |
|---|---|---|
| The main forwarding rule `dice-vs` and the gateway object `platform-gateway`, both in `istio-system` | To see every path on the production address in one place | The cluster web page, kinds `VirtualService` and `Gateway` |
| The user service (`vision-user-service`) | It keeps `is_active` and `system_role` for each SSO user of DICE. Useful to compare when the admin page is designed | The DICE repo |
| The defect agent backend's `tests/` | A ready list of cases for the pass checker | The defect agent repo |
| The Argo CD application definitions (`argocd-configuration-repository`) | Needed when the forwarding rule is moved to Argo CD | That repo |

---

## Part 8: Problems found during the review

1. **The production signing secret is a placeholder.** Part 6 item 1.
2. **Secrets in this folder.** `DEPLOY.md` and `DEPLOY_CONFIG_261121.md` hold live passwords and
   keys. Both are now in `.gitignore`. A base64 value is not hidden: it is the same secret in
   another spelling. Never add these files with `git add -f`.
3. **Company source code is on github.com.** The four reference folders were committed and
   pushed on 2026-11-19. They contain the defect agent, the DICE login service and the DICE
   Helm chart with internal addresses. Check whether that repo is allowed to hold them.
4. **`config.yaml` is committed and contains live keys** (model access keys and object storage
   keys). Older than the authorization work, same repo.
5. **`GET /logs` is open** and returns the server logs, which include people's questions. Until
   Part 1 is done it is also open on the production DICE address. Part 3 closes it.
6. **CORS allows every website with credentials** (`data_agent/middleware/__init__.py`). Part 3
   narrows it.
7. **`tests/test_app.py` no longer matches the code.** It imports `log_requests_middleware` and
   patches `PostgresClient`, `postgres_dsn` and `reset_session_locks`, none of which exist in the
   source. Found by reading on 2026-11-19. The test suite was not run.
8. **`GET /logs` turns its own "no log files" 404 into a 500.** The `HTTPException(404)` is
   raised inside the `try` block and caught by `except Exception`. Unrelated to authorization.
9. **Old sessions become invisible** unless the typed Knox ID equals the SSO login ID. Accepted
   on 2026-11-18.
10. **The frontend's `Dockerfile` and `DEPLOY.md` name `10.240.35.173`,** everything else names
    `10.240.35.180`. The run script overrides the value, so nothing breaks. Correct it when the
    files are changed for Part 4.

---

## Part 9: Where each fact comes from

Paths without a repo name are relative to the root of this repo. The reference folders are
copies.

| Topic | File |
|---|---|
| How the pass is built and what it contains | `mvp-vision-ai-platform/web-auth/web-auth/app/service-token.ts` |
| `/auth/token` and `/auth/session` replies | `mvp-vision-ai-platform/web-auth/app/token/route.ts`, `app/session/route.ts` |
| Return address rules (check 3), cookie names and lifetime | `mvp-vision-ai-platform/web-auth/app/api/auth/[...nextauth]/route.ts` lines 89 to 107 and 119 to 226, `app/login/page.tsx`, `app/auth-origin.ts` |
| Logout | `mvp-vision-ai-platform/web-auth/app/logout/route.ts` |
| Production settings of the login service, secrets as stored | `DEPLOY_CONFIG_261121.md`, `DEPLOY.md` |
| Checking the pass in a backend | `defect-studio-backend-service/src/auth/infrastructure/service_token_verifier.py`, `mvp-vision-ai-platform/platform/backend/app/core/web_auth.py` |
| Other tokens signed with the same secret | `mvp-vision-ai-platform/platform/backend/app/core/security.py`, `service_jwt.py` |
| Bearer header handling and user lookup | `defect-studio-backend-service/src/common/presentation/middleware/auth.py` |
| One person cannot read another's data | `defect-studio-backend-service/src/thread/presentation/controllers/thread_controller.py` |
| Error reply shapes | `defect-studio-backend-service/src/common/presentation/exception_handlers/handlers.py` |
| Secret handling at startup | `defect-studio-backend-service/src/container/settings.py` |
| Rollout notes, rule about SSO groups, short keys | `defect-studio-backend-service/SSO_ROLLOUT_107.md` |
| Page-side login logic | `defect-studio-train-service/web/frontend/src/features/auth/model/authStore.ts`, `centralAuth.ts`, `ssoRedirect.ts`, `ui/ProductionLoginScreen.tsx` |
| Attaching the pass, behaviour on 401 | `defect-studio-train-service/packages/api-client/src/utils/api-client.ts` |
| Forwarding rules of the defect agent, including `/auth` | `argocd-application-repository/charts/defect-studio/templates/virtualservice.yaml`, `environments/production/defect-studio.yaml` |
| Data agent frontend as it is today | `cosmo-data-agent-frontend`: `next.config.mjs`, `Dockerfile`, `src/app/backend/[...path]/route.ts`, `src/app/api/chat/route.ts`, `src/lib/session-api.ts`, `src/providers/user-provider.tsx`, `src/components/user-gate.tsx`, `src/components/chat/` |
| How Next.js treats `/data-agent/` | `cosmo-data-agent-frontend/node_modules/next/dist/lib/load-custom-routes.js` lines 529 to 582 |
| Data agent backend as it is today | `data_agent/app.py`, `data_agent/routers/`, `data_agent/infra/session_lock.py`, `data_agent/infra/postgresql_client.py`, `common/config.py`, `Dockerfile` |
| The forwarding rule for the data agent | `deploy/prod/routing.yaml` |
