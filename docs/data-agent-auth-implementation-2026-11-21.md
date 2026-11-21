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
5. **The backend is implemented** (2026-11-22). Compared with the earlier design, admins moved
   from the configuration into the database ([Part 3](#part-3-backend-implementation)).

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
4. Backend: check the pass, create the tables, add the approval gate and the admin endpoints
   ([Part 3](#part-3-backend-implementation)). **Done on 2026-11-22, not deployed.**
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
| Admins | Rows in the database table `user_admins`, added and removed through admin endpoints while the backend runs. The first admin is put in with one SQL statement. An admin page comes later | 2026-11-22 |
| Tables | `user_accounts` (one row per person, with everything SSO sends), `user_access_log` (one row per visit) and `user_admins` | 2026-11-22 |
| The person's real IP address | Put aside. The columns exist and hold the frontend server's address for now | 2026-11-22 |
| The 30 minute idle logout in the page | Removed. The DICE login decides how long a person stays logged in | proposed 2026-11-21 |
| Where the forwarding rule is stored | This repo, `deploy/prod/routing.yaml` | 2026-11-21 |

The two rows marked "proposed" are new in this document. Say so if you disagree with either.

**Status on 2026-11-22.**

- The backend authorization code is written and tested (Part 3). It is not deployed: the backend
  running on the server is still the open one.
- The forwarding rule, as far as this document knows, is still the first one (namespace `dice`,
  objects `data-agent-stage` and `data-agent-server`). It has to be replaced (Part 1). While it
  is in place, the open backend is reachable at
  `https://dice.gtrai.sec.samsung.net/data-agent/api/...`.
- The frontend authorization code is written too (2026-11-22), in the frontend repo, from
  `data-agent-frontend-auth-brief-2026-11-22.md`. It is not deployed either.

---

## Words used in this document

| Word | Meaning |
|---|---|
| Samsung SSO (ADFS) | The company login page where people type their password. Its address is `sts.secsso.net` |
| DICE login service (`web-auth`) | A small website run by DICE. It is the only thing that talks to Samsung SSO. Source: `mvp-vision-ai-platform/web-auth` |
| Cookie | A small note a website stores in the browser. The browser sends it back only to the website that stored it. The login cookie is named `dice.session-token` |
| Pass (token, service JWT) | A short text the login service creates. It says who the person is and when it expires, and it is signed. The technical name is JWT |
| Secret (in the data agent: `auth.service_jwt_secret`) | The password used to sign the pass. The login service and every backend that checks passes hold the same value |
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
  data agent keeps its own admins, in the table `user_admins`.
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
| 6 | A long agent run survives the gateway | Not reported. Taken as passing on 2026-11-22 | If long questions are cut later, this is the first thing to look at |
| 7 | Where the real IP address arrives | Put aside on 2026-11-22. The IP columns exist and hold the frontend server's address | Pick it up when the real address is wanted |
| 8 | Questions about the frontend | Answered by reading the frontend. See Part 4 | Nothing |
| 9 | The JWT library in the backend environment | Done. PyJWT 2.15.1 is pinned in both requirements files | Nothing |
| 10 | The first admin | Answered: your login ID, exactly as shown in `sub` in check 4 | Put it in with the SQL statement in Part 3, section 3.8 |
| 11 | Fetch the missing references | Mostly done. See Part 7 | Nothing that blocks |

On 2026-11-22 the backend work went ahead on the assumption that checks 3, 5 and 6 pass. No
result has been reported for them, so the sections below stay as instructions.

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

Done. `PyJWT==2.15.1` is in `requirements_py313_prod.txt` and `requirements_py313_dev.txt`, and
it installs together with the other pinned packages. It is the version the pass was checked with
on 2026-11-21.

---

## Part 3: Backend implementation

**Implemented on 2026-11-22. Not deployed yet.** All paths in this part are in this repo.

This part describes what was built. It replaces the design sketches of the earlier versions.
Three things were decided on 2026-11-22 and differ from the earlier design:

- Admins are stored in the database (table `user_admins`), not in the configuration, and can be
  added and removed while the backend runs.
- The first admin is put in with one SQL statement (3.8).
- Request and identity models are pydantic classes in `data_agent/schemas/auth.py`.

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
- An admin is a row in `user_admins`. An admin is always allowed, whatever the `is_active` column
  of their account says.

Left out on purpose, compared with the defect agent:

- Local password login, token refresh, and account linking. They exist in the defect agent only
  to carry over its old password accounts. The data agent has none.
- A separate "create my account" call. The defect agent's page calls `/api/auth/me`, gets
  `sso_account_unlinked`, then calls `/api/auth/sso/provision`. The data agent creates the row
  inside `/auth/me`. The person sees the same behaviour.

### 3.2 Where the code is

| File | What it holds |
|---|---|
| `common/config.py` | `AuthConfig`, `Settings.auth`, `Settings.cors_origins`, three environment variable names |
| `common/constants.py` | `AuthErrorCode` and the length limits |
| `data_agent/schemas/auth.py` | `SsoIdentity`, `UserInfo`, and the request and reply models of the new endpoints |
| `data_agent/exceptions/` | `AuthError`, the handler that turns it into a reply, `register_exception_handlers` |
| `data_agent/utils/user.py` | `normalize_user_id`: the one place that says what a valid `user_id` is |
| `data_agent/services/token_verifier.py` | `TokenVerifier`: checks the pass (3.4) |
| `data_agent/services/user_manager.py` | `UserManager`: the approval gate, users, admins |
| `data_agent/infra/user_repository.py` | `UserRepository`: the three tables and every SQL statement (3.5) |
| `data_agent/routers/dependencies.py` | `get_identity`, `require_active_user`, `require_session_owner`, `require_admin` |
| `data_agent/routers/auth.py`, `admin.py` | The new endpoints (3.6) |
| `data_agent/routers/agent.py`, `logs.py` | One line each: the check is attached to the whole router |
| `data_agent/app.py` | Creates the repository, the verifier and the manager at start, registers the error handler |
| `data_agent/middleware/__init__.py` | CORS reads `cors_origins` instead of allowing every website |

### 3.3 Configuration

A new section in `config.yaml`:

```yaml
auth:
  service_jwt_secret: "<plain value of the signing secret>"
  service_jwt_issuer: web-auth
  service_jwt_audience: dice-backend
```

| Setting | Environment variable | Default |
|---|---|---|
| `auth.service_jwt_secret` | `AUTH_SERVICE_JWT_SECRET` | None. The backend refuses to start when it is missing or empty |
| `auth.service_jwt_issuer` | `AUTH_SERVICE_JWT_ISSUER` | `web-auth` |
| `auth.service_jwt_audience` | `AUTH_SERVICE_JWT_AUDIENCE` | `dice-backend` |
| `cors_origins` | none | Empty list |

Like every other setting, a value in the environment wins over the file.

Rules:

- The value is the production secret (`dice` / `dice-runtime` / `service-jwt`) in its plain
  form. The base64 spelling that Kubernetes displays does not work. Check 5 in Part 2 shows how
  to get the plain form.
- The `config.yaml` in this repo has an empty secret on purpose, because the repo is on
  github.com. Put the real value in the `config.yaml` that lies beside the repo on the server,
  or in the environment variable. Never commit it.
- There are no admin IDs in the configuration.
- `cors_origins` stays empty. No browser calls the backend directly: the frontend server makes
  the calls, and CORS does not apply to it.

### 3.4 Checking the pass

`TokenVerifier.verify` accepts a pass only if all of this holds:

1. The signature is right for the secret, and the algorithm is HS256. Nothing else is accepted.
2. It has not expired, and it has `exp` and `sub`.
3. `iss` is `web-auth` and `aud` is `dice-backend`.
4. `type` is `service`.
5. `sub` and `username` are text and equal, ignoring case.
6. `sub`, lower-cased, is a valid `user_id`: not empty, at most 255 characters, no spaces or
   control characters, no `/` or `\`, and not the words `null`, `undefined` or `none`.

Anything else is a 401. Points 1 to 5 are the defect agent's checks. The slashes in point 6 are
an addition, because the `user_id` becomes part of storage keys.

The library is PyJWT 2.15.1, pinned in both requirements files. The defect agent uses
`python-jose`, which is less well maintained and does the same job. PyJWT prints
`InsecureKeyLengthWarning` once when the secret is shorter than 32 bytes. The production secret
is 22 bytes, so this warning appears. The pass is still checked correctly. The warning is right
about the secret, though: see Part 6 item 1.

Do not relax any of these checks. The same secret also signs other tokens inside DICE that are
not logins: the platform backend creates short tokens for its calls to the labeler (`iss` is
`platform`, `aud` is `labeler`) and tokens for calls between services (no `iss`, no `aud`). The
DICE platform's own checker skips the audience check. Here both kinds are refused, and a test
covers each.

### 3.5 Tables

Created at start with `CREATE TABLE IF NOT EXISTS`, the same way `session_run_locks` is. The
repo has no migration tool.

```sql
CREATE TABLE IF NOT EXISTS user_accounts (
    user_id        TEXT PRIMARY KEY,                 -- pass "sub", lower case
    is_active      BOOLEAN NOT NULL DEFAULT false,   -- the approval
    activated_at   TIMESTAMPTZ,
    activated_by   TEXT,                             -- admin's user_id
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_access_at TIMESTAMPTZ,
    last_access_ip TEXT,
    email          TEXT,                             -- from here on: copied from SSO at every /auth/me
    full_name      TEXT,
    department     TEXT,
    company        TEXT,
    unique_name    TEXT,
    sid            TEXT,
    roles          JSONB NOT NULL DEFAULT '[]'::jsonb,
    sso_claims     JSONB NOT NULL DEFAULT '{}'::jsonb,   -- the whole pass, as received
    sso_updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_access_log (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES user_accounts(user_id) ON DELETE CASCADE,
    accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address  TEXT,
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS ix_user_access_log_user_time
    ON user_access_log (user_id, accessed_at DESC);

CREATE TABLE IF NOT EXISTS user_admins (
    user_id  TEXT PRIMARY KEY,
    added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    added_by TEXT                                     -- admin's user_id, or 'bootstrap'
);
```

Why it is shaped this way:

- **A login never changes `is_active`.** The statement that records a visit updates only the
  columns copied from SSO and the two `last_access` columns.
- **`user_admins` does not point at `user_accounts`.** An admin can therefore be named before
  that person has ever opened the data agent.
- **`roles` is information only.** It comes from SSO groups and is never used to decide who is
  approved or who is an admin.
- **The IP columns exist but are not meaningful yet.** They hold the address of whoever called
  the backend directly, which is the frontend server. Getting the person's real address was
  put aside on 2026-11-22 (check 7 in Part 2).
- **Table names.** The database also holds the agent framework's own tables (`sessions`,
  `events` and others), so a plain name like `users` is avoided.

This stores personal data. Old log rows can be removed with
`DELETE FROM user_access_log WHERE accessed_at < now() - interval '1 year'`.

### 3.6 Endpoints

| Address | Who may call | What it does |
|---|---|---|
| `GET /health` | Anyone | Unchanged |
| `GET /auth/me` | Anyone with a valid pass | Creates or updates the account, adds one access log row, returns the account |
| Everything under `/apps/users/{user_id}/...` | Valid pass, approved or admin, own `user_id` | Unchanged behaviour |
| `GET /logs` | Admin | Unchanged behaviour. It used to be open |
| `GET /admin/users` | Admin | Lists accounts, newest first. Optional `?is_active=true` or `?is_active=false` |
| `PATCH /admin/users/{user_id}?is_active=true` | Admin | Approves a person. `?is_active=false` takes the approval away |
| `GET /admin/users/{user_id}/access-log` | Admin | Newest visits first. Optional `?limit=`, 1 to 1000, default 100 |
| `GET /admin/admins` | Admin | Lists admins |
| `PUT /admin/admins/{user_id}` | Admin | Makes that login ID an admin. Calling it again changes nothing |
| `DELETE /admin/admins/{user_id}` | Admin | Removes an admin. Refused for the last one |

The values of the admin endpoints travel in the address (`?is_active=true`), not in a request
body. This follows the existing endpoints of this backend, such as renaming a session.

In the browser all of these start with `/data-agent/backend`, because the page reaches the
backend through the frontend server. `/data-agent/backend/auth/me` is not the same as the login
service's `/auth/...` addresses, which sit at the top of the DICE address.

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
  "created_at": "2026-11-22T10:00:00+09:00"
}
```

For an admin, `/auth/me` answers `is_active: true` whatever the column says, so the page needs
only one rule: `is_active` means "may use the data agent". The admin endpoints show the real
column.

### 3.7 Error replies

Every refusal has the shape `{"detail": "...", "code": "..."}`. A 401 also carries the header
`WWW-Authenticate: Bearer`. Both follow the defect agent.

| Status | `code` | When | What the page does |
|---|---|---|---|
| 401 | `invalid_token` | No pass, bad signature, expired, wrong issuer or audience, broken identity | Get a new pass once and retry. If it fails again, go to login |
| 403 | `account_inactive` | Valid pass, person not approved and not an admin | Show "waiting for approval" |
| 403 | `user_mismatch` | The `user_id` in the address is not the caller's | Reload the page. A different person has logged in to DICE in this browser |
| 403 | `admin_required` | Not an admin | Hide or refuse the admin function |
| 404 | `user_not_found` | Admin endpoint: no account with that `user_id` | Show the message |
| 404 | `admin_not_found` | Removing an admin who is not one | Show the message |
| 409 | `last_admin` | Removing the only admin | Show the message |

A `user_id` in an admin address that is not a valid login ID gives a 400 with only `detail`,
like the other 400 replies of this backend.

### 3.8 The first admin

The admin table starts empty, and only an admin can add another admin. So the first one is put
in by hand, once, after the backend has started for the first time (the start creates the
table). In the data agent's Postgres database:

```sql
INSERT INTO user_admins (user_id, added_by) VALUES ('your.loginid', 'bootstrap');
```

- Use your login ID exactly as `sub` shows it in a pass, in lower case.
- It works before or after your first visit to the page.
- This is also the way back in if the admins are ever lost.

### 3.9 Behaviour worth knowing

- **Being an admin is separate from being approved.** An admin who was never approved loses all
  access the moment they are removed from the admins. Approve the account as well if the person
  should keep using the data agent.
- **Taking the approval away works at the next request.** The account is read from the database
  on every request (one small `SELECT`). Nothing is cached.
- **Deactivating keeps `activated_at` and `activated_by`.** They show the last approval.
- **One access log row per call of `/auth/me`,** which the page makes once per page load. A new
  person's very first request also adds a row, whichever endpoint it hits.
- **A new person exists in `user_accounts` after their first request,** with `is_active` false.
  That is how an admin finds them: `GET /admin/users?is_active=false`.
- **The automatic API pages (`/docs`)** are for direct use on port 18080 only.
- **The request log** (`data_agent/middleware/logging.py`) prints the query string, which for
  `/run` is the person's question. It does not print headers, so the pass is not logged.

### 3.10 Tests, and how this was checked

Unit tests, with the database mocked, as the other tests of this repo do:

| File | What it covers |
|---|---|
| `tests/services/test_token_verifier.py` | A valid pass and its fields. Rejected: expired, wrong secret, wrong algorithm, algorithm `none`, wrong or missing issuer and audience, wrong `type`, missing `sub` or `exp`, `username` different from `sub`, every kind of bad identity |
| `tests/infra/test_user_repository.py` | The SQL and parameters sent for each method |
| `tests/services/test_user_manager.py` | The approval gate, the admin override, not found, last admin |
| `tests/routers/test_dependencies.py` | No header, wrong scheme, bad pass, inactive, foreign `user_id`, not admin |
| `tests/routers/test_auth.py`, `test_admin.py` | The new endpoints |
| `tests/routers/test_agent.py`, `test_logs.py` | The existing endpoints now need a pass, an owner, or an admin |
| `tests/common/test_config.py`, `tests/exceptions/`, `tests/utils/test_user.py` | Settings, error replies, `user_id` rules |
| `tests/test_app.py` | Repaired. It had not matched `data_agent/app.py` for some time and could not even be loaded |

Result on 2026-11-22: 174 tests pass and 1 fails. The failing one is
`tests/services/test_agent_runner.py::TestAgentRunner::test_run`. It fails in the same way on
the code as it was before this work, and it has nothing to do with authorization.

Two checks went beyond the unit tests, both on a throwaway Postgres 16 on the development PC:

- Every SQL statement of `UserRepository` was run for real, including Korean text in the SSO
  fields and the statement from 3.8.
- The whole flow was run with the real routers, the real `TokenVerifier` and `UserManager`:
  no pass, a pass with a wrong secret, an expired pass, a DICE labeler token, a new person,
  approval, a foreign `user_id`, deactivation, adding and removing admins, the last admin.

Not checked: the backend has not run against the real database on `10.240.35.180`, and it has
not been given a live pass from DICE. The decoding of a real (expired) pass with the production
secret was checked on 2026-11-21.

### 3.11 Testing the backend without DICE

On your own machine you choose the secret, so you can make your own pass.

Start the backend with the environment variable `AUTH_SERVICE_JWT_SECRET` set to
`local-test-secret-of-at-least-32-bytes`, and run the statement from 3.8 with `alenova`. Then:

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
}, "local-test-secret-of-at-least-32-bytes", algorithm="HS256"))
```

```
curl -H "Authorization: Bearer PASTE_THE_PASS" http://localhost:18080/auth/me
curl -H "Authorization: Bearer PASTE_THE_PASS" "http://localhost:18080/admin/users?is_active=false"
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
  table `user_admins`.
- **Old test sessions.** A session stored under a typed Knox ID stays visible only if that ID,
  in lower case, equals the person's SSO login ID.

### 4.8 Working on the frontend locally

A page on `localhost` has no DICE cookie, so the real login cannot finish there. Two ways exist,
and neither is needed to finish Part 3:

- Backend only: run it with your own secret and make your own pass (Part 3, section 3.11).
- Page and backend together: the defect agent forwards `/auth` from its development server to
  the stage login service and uses the stage login simulator
  (`web/frontend/vite.config.ts`, `dev/stagingAuthProxy.ts`, `.env.development`). The data
  agent can do the same later. It needs the stage secret on the local backend and your login ID
  on the stage simulator's allowlist.

---

## Part 5: Deploying and testing

> **The step-by-step version of this part is `data-agent-auth-deploy-and-test-2026-11-22.md`.**
> It was written after the frontend was implemented and is the one to follow. The text
> below is the earlier outline.

There is one data agent, and it now sits on the production DICE address. There is no separate
test copy. The approval gate is what keeps other people out while you test.

### Order

1. Check 6, then the new forwarding rule (Parts 1 and 2).
2. Backend with the authorization code:
   1. On the server, add this section to the `config.yaml` that lies beside the repo (the one
      that already holds the storage and model keys):

      ```yaml
      auth:
        service_jwt_secret: "<plain value of dice-runtime / service-jwt>"
      ```

   2. Build and start the backend the usual way. If the section is missing or the value is
      empty, the backend stops at start with a message that names `auth`.
   3. Put yourself in as the first admin, once (Part 3, section 3.8):

      ```sql
      INSERT INTO user_admins (user_id, added_by) VALUES ('your.loginid', 'bootstrap');
      ```

   From the start in step 2 the old page stops working, because it sends no pass.
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
| Admin calls `PATCH /data-agent/backend/admin/users/{that id}?is_active=true` | Reply shows `is_active: true`, `activated_by` is the admin |
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
   - the data agent's `auth.service_jwt_secret`

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
5. **`GET /logs` is open on the running backend** and returns the server logs, which include
   people's questions. Until Part 1 is done it is also open on the production DICE address. The
   new code makes it admin-only. That takes effect when the new backend is deployed.
6. **CORS allowed every website with credentials** (`data_agent/middleware/__init__.py`). Fixed
   in the new code: the list of allowed websites is a setting and is empty.
7. **`tests/test_app.py` did not match the code** and stopped the whole test suite from
   loading. Repaired on 2026-11-22.
8. **One test fails for a reason unrelated to authorization:**
   `tests/services/test_agent_runner.py::TestAgentRunner::test_run`. It expects the run error to
   be recorded once and finds it recorded twice. It fails the same way on the code before the
   authorization work. Not touched.
9. **`GET /logs` turns its own "no log files" 404 into a 500.** The `HTTPException(404)` is
   raised inside the `try` block and caught by `except Exception`. Unrelated to authorization,
   and an existing test expects the 500, so it was left alone.
10. **Old sessions become invisible** unless the typed Knox ID equals the SSO login ID. Accepted
   on 2026-11-18.
11. **The frontend's `Dockerfile` and `DEPLOY.md` name `10.240.35.173`,** everything else names
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
| Data agent backend, the authorization code | The files listed in Part 3, section 3.2 |
| The forwarding rule for the data agent | `deploy/prod/routing.yaml` |
