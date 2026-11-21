# Brief: add DICE single sign-on to the data agent frontend

You are working in the repository `cosmo-data-agent-frontend` (Next.js 16, React 19, TypeScript).
This brief is the whole task. It was written by the person who built the backend half, after
reading this frontend, the backend, and the source of the DICE login service. Nobody from that
work is in your session, so everything you need is meant to be here.

Where this brief and the code disagree about the code (a file moved, a line changed), trust the
code and say so in your final report. Where they disagree about the contract (addresses, reply
shapes, error codes), trust this brief: it was written from the source of the services you
cannot see.

## 1. The task

Today the app has no real login. A form asks for a "knox ID", keeps it in `localStorage`, and
sends it as the `user_id` in every backend address. Anyone can type anyone's ID.

Replace this with the company single sign-on that the DICE platform already runs. After your
change:

- A person opens the app, is sent to Samsung SSO if they are not logged in, and comes back logged
  in, on the same address they started from.
- The app gets a short-lived signed pass from the DICE login service and sends it with every
  request to the backend.
- The backend tells the app who the person is and whether an admin has approved them. A person
  who is not approved sees a "waiting for approval" screen and nothing else.
- The app is served under the path `/data-agent` instead of the top of the site.

The backend already checks the pass. Without your change the app cannot talk to it at all.

## 2. Before you start

- **Branch.** Work on `develop-261116`. This brief describes that branch at commit `fe881c9`
  ("[feat] apply fixes 261117"). Line numbers below refer to that commit. Run
  `git branch --show-current` and `git status` first. If you are on another branch, or the tree
  has uncommitted changes you did not make, stop and ask the user. Do not switch branches or
  stash on your own.
- **Do not commit or push** unless the user asks.
- **Scope.** Only this repository. Do not change the backend, the gateway, or anything about
  the login service. Section 8 lists what is deliberately left out.
- **Decisions already made.** These were settled with the user. Build on them, do not reopen them:
  1. The browser never calls the backend directly. It keeps calling this app's own server
     (`/backend/...` and `/api/chat`), which passes the call on. This is how the app works today.
  2. The pass is checked only in the backend. This app's server passes it on untouched. No
     secret, no token library and no token checking in this repository.
  3. The 30 minute idle logout is removed. The DICE login decides how long a person stays
     logged in.
  4. The login behaviour copies another DICE product (the "defect agent"), whose page-side
     logic is the model for sections 6.3 and 6.4.

## 3. What exists today

| File | What it does now |
|---|---|
| `next.config.mjs` | `output: "standalone"`, a redirect from `/` to `/chat/new`. No base path |
| `Dockerfile` | Build args `NEXT_PUBLIC_APP_TITLE`, `NEXT_PUBLIC_MAX_INPUT_LENGTH` (lines 18 to 22). Runs on port 13080 |
| `src/app/backend/[...path]/route.ts` | Server route. Passes any `/backend/<path>` call on to `BACKEND_ORIGIN/<path>`. Line 34 copies only the `accept` and `content-type` request headers |
| `src/app/api/chat/route.ts` | Server route for sending a question. Reads a form (`userId`, `sessionId`, `message`, `file`), calls the backend's `/run` (lines 68 and 73), returns `{response, timestamp}`. On a backend error it returns the backend's status and body text (line 93) |
| `src/lib/session-api.ts` | All other backend calls, as `fetch(API_BASE + ...)` with `API_BASE = "/backend"` (line 8). Eight calls: lines 324, 357, 390, 414, 441, 461, 482, 500 |
| `src/providers/user-provider.tsx` | The stand-in login: `userId` in `localStorage` under `mock_user_id`, a 30 minute idle timer, `keepAlive`, activity listeners, cross-tab sync. The top half of the file is an older version, commented out |
| `src/components/user-gate.tsx` | Shows the "Enter your knox ID" form when there is no `userId`. Also pushes the router to `/chat/new` when logged out (line 17) |
| `src/app/layout.tsx` | Wraps the app in `<UserProvider><UserGate>` (lines 45 to 47) |
| `src/components/chat/chat-view.tsx` | The chat. Uses `useUser().userId` (line 81). Sends a question with `fetch("/api/chat")` (line 517) and reads the reply without looking at the status (line 522) |
| `src/components/chat/session-sidebar.tsx` | Session list, reloaded every 5 seconds (line 128). Account menu with "Log out", which calls `clearUserId()` (lines 271 to 274) |
| `src/components/chat/message-item.tsx` | Shows a stored image by fetching it through `SessionStorage.loadArtifact` and making an object URL. It does not use a plain `<img src>` for backend files, so it needs no redesign |
| `src/lib/draft-storage.ts` | Unsent text per chat in `localStorage`, keys `chat_draft:<session id>` and `chat_draft:new` |

Consumers of the user context: `chat-view.tsx` (`userId`), `session-sidebar.tsx` (`userId`,
`clearUserId`), `user-gate.tsx` (`userId`, `setUserId`, `isReady`). Nothing calls `keepAlive`.

## 4. How login works in production

```
browser ── https://dice.gtrai.sec.samsung.net ──► gateway
    /auth/...          ──► DICE login service            (not this app)
    /data-agent        ──► this app's server, port 13080 (path passed on unchanged)
    /data-agent/...    ──► this app's server, port 13080 (path passed on unchanged)

this app's server ── BACKEND_ORIGIN ──► data agent backend
```

1. The person opens `https://dice.gtrai.sec.samsung.net/data-agent`. The gateway sends the
   request to this app's server, which serves the page.
2. The page asks the login service `GET /auth/session`. The browser attaches the login cookie by
   itself if there is one.
3. Not logged in: the page navigates to `/auth/login?callbackUrl=<the current address>`. The login
   service takes the person through Samsung SSO, sets its cookie, and navigates back to that
   address.
4. The page loads again, step 2 now says logged in.
5. The page asks `GET /auth/token` and receives the pass.
6. The page calls `GET /data-agent/backend/auth/me` with `Authorization: Bearer <pass>`. This
   app's server passes it on to the backend's `/auth/me`. The backend checks the pass, records
   the visit, and answers who this is and whether they are approved.
7. Approved: the app starts and uses the `user_id` from step 6 wherever it uses the typed knox
   ID today. Not approved: the waiting screen.
8. Every later call to `/backend/...` and `/api/chat` carries the same header.

Things that follow from this picture:

- **The gateway does not remove `/data-agent`.** This app receives the full path, so it must be
  built with that base path (6.1).
- **`/auth/...` is not part of this app.** It lives at the top of the site, outside the base path,
  and is answered by the login service. In the browser it is the same origin as the page, which
  is why the cookie works.
- **The login cookie is `HttpOnly` and belongs to the login service.** The page cannot read it
  and never needs to. The gateway is being set up to remove cookies from requests before they
  reach this app's server, so nothing on the server side of this app may depend on a cookie.
- **The backend is not reachable from the browser.** Only this app's server reaches it.
- **Opened by IP address or on localhost, real login cannot work,** because the login service
  and its cookie exist only on the DICE address. Section 6.7 covers local development.

## 5. The contracts

### 5.1 The login service (addresses at the top of the site)

Call these with `fetch(..., { credentials: "include", cache: "no-store" })`.

**`GET /auth/session`** always answers 200 with JSON.

```json
{ "authenticated": false, "user": null, "roles": [], "error": null }
```

```json
{ "authenticated": true,
  "user": { "id": "Vyv2k7hO...=", "name": "gildong.hong@samsung.com", "email": "gildong.hong@samsung.com" },
  "roles": [], "expiresAt": 1795066027 }
```

Use only `authenticated`. `user.id` is an internal value of Samsung SSO. It is not the login ID
and must not be used as `user_id`.

**`GET /auth/token`**

| Status | Body | Meaning |
|---|---|---|
| 200 | `{ "accessToken": "<pass>", "tokenType": "Bearer", "expiresAt": 1795066027 }` | `expiresAt` is unix seconds |
| 401 | `{ "error": "unauthorized" }` | There is no login (any more) |
| 500 | `{ "error": "service_token_error" }` | The login service failed |

Facts about the pass:

- It is an opaque string to this app. Do not decode it and do not make decisions from its
  contents.
- It lasts at most one hour. Asking again before it expires returns the same pass.
- The DICE login itself lasts about one hour, and asking for a pass does not extend it. So
  roughly once an hour `/auth/token` answers 401 and the person has to pass through the login
  redirect again. If they are still logged in to Samsung SSO this is silent, but it is a full
  page navigation. Section 7 says what that means for the page.

**`GET /auth/login?callbackUrl=<address>`** is a page. Navigate to it, do not fetch it. The
`callbackUrl` must be an address on the same origin; use `window.location.href`. An address on
another origin is replaced by the DICE home page.

**`GET /auth/logout`** is a navigation too. It logs the person out of all of DICE and of Samsung
SSO, and lands on a DICE page, not on this app. Use it exactly like this, without query
parameters.

Do not call anything under `/api/auth/`. That belongs to the login service's inner workings.

### 5.2 The backend (reached as `<base path>/backend/...`)

Every backend address except `/health` now requires `Authorization: Bearer <pass>`.

**New: `GET /auth/me`** (from the browser: `<base path>/backend/auth/me`). Note that this is a
different thing from the login service's `/auth/...` in 5.1, despite the similar name.

```json
{
  "user_id": "gildong.hong",
  "is_active": true,
  "is_admin": false,
  "email": "gildong.hong@samsung.com",
  "full_name": "gildong.hong@samsung.com",
  "department": "Some Department",
  "company": "Some Site",
  "created_at": "2026-11-22T10:00:00+09:00"
}
```

- `user_id` is the person's login ID in lower case. It is the value for `{user_id}` in every
  existing address (`/apps/users/{user_id}/...`).
- `is_active` means "may use the data agent". It is already `true` for admins.
- `email`, `full_name`, `department` and `company` may be `null`.
- Each call is recorded as one visit. Call it once per page load, and again only when the
  person presses "check again". Never call it on a timer or on every pass renewal.
- A person the backend has never seen gets an account with `is_active: false` on this call.
  That is how admins find new people.

**Existing addresses** behave as before, with one new rule: the `{user_id}` in the address must
be the caller's own. The reply and request shapes are the ones `src/lib/session-api.ts` and
`src/app/api/chat/route.ts` already handle.

**Refusals** from the authorization layer always look like `{"detail": "...", "code": "..."}`.

| Status | `code` | When | What the page does |
|---|---|---|---|
| 401 | `invalid_token` | No pass, or the pass is expired or otherwise not accepted | Get a new pass. Details in 6.3 |
| 403 | `account_inactive` | The pass is fine, the person is not approved | Show the waiting screen |
| 403 | `user_mismatch` | The `{user_id}` in the address is not the caller's | A different person is now logged in to DICE in this browser. Reload once |
| 403 | `admin_required` | Only on admin addresses | The page calls none of them yet |

Other errors are unchanged: `{"detail": "..."}` without `code`, with status 400 or 500. This
app's own server routes can also answer in plain text (`502 Backend unreachable`,
`500 BACKEND_ORIGIN is not configured`), so never assume an error body is JSON.

Through `/api/chat` a backend refusal arrives with the backend's status and the same JSON text
as the body.

## 6. What to build

How you structure the code is yours to decide. The behaviour below is the requirement. File
names in this section are suggestions unless they name an existing file.

### 6.1 Serve the app under a base path

- Add a build-time setting `NEXT_PUBLIC_BASE_PATH`. Empty means "top of the site" (local
  development). In the Docker build it is `/data-agent`.
- `next.config.mjs`: set `basePath` from it. Treat an empty value or `/` as "no base path", and
  make sure the value has a leading slash and no trailing slash. Keep everything else in that
  file.
- `Dockerfile`: add `ARG NEXT_PUBLIC_BASE_PATH="/data-agent"` and the matching `ENV` next to the
  two existing build args (lines 18 to 22), so a plain `docker build` produces the production
  build.
- `.env.example`: document the setting.
- Give client code one constant for it (for example `src/lib/base-path.ts`), with the same
  normalisation.

Next.js adds the base path by itself to `router.push`, `router.replace`, `<Link>`, the redirect
in `next.config.mjs`, its own script, font and image files (including the imported
`dice_icon.png` and `src/app/icon.svg`). `usePathname()` keeps returning the path without the
base path. Do not add the base path a second time in those places.

Next.js does not touch addresses the code writes itself. These need the base path in front:

| Where | Now |
|---|---|
| `src/components/chat/chat-view.tsx:517` | `fetch("/api/chat", ...)` |
| `src/lib/session-api.ts`, the eight calls | `fetch(API_BASE + ...)`, and `artifactUrl()` (line 107) which builds an address from `API_BASE` |
| `src/components/chat/chat-view.tsx:183` | `fetch("/suggested-questions.json")` (a file in `public/`) |
| `src/components/chat/chat-view.tsx:369` and `:468` | `window.history.replaceState(null, "", "/chat/...")` |
| `src/components/chat/session-sidebar.tsx:215` | `window.location.pathname === "/chat/..."` |

The login service addresses (`/auth/...`) never get the base path.

Do not set `trailingSlash`, and do not add a redirect between `/data-agent` and `/data-agent/`.
Next.js already redirects `/data-agent/` to `/data-agent`, and the gateway is configured around
that. A redirect in the other direction would loop.

### 6.2 Pass the pass on, on the server

- `src/app/backend/[...path]/route.ts`, line 34: add `authorization` to the request headers that
  are passed on. Also pass on `user-agent` and `x-forwarded-for`: the backend records the
  browser with each visit, and without this it records Node's own client.
- `src/app/api/chat/route.ts`: read `authorization` from the incoming request and send it with
  both backend calls (lines 68 and 73), together with the same two extra headers. Keep
  returning the backend's status and body unchanged on an error (line 93), and pass on the
  backend's `content-type` there so the page can tell it is JSON.
- Neither route checks the pass, and neither needs to refuse a request without one: it passes
  the request on and the backend answers 401.
- Never log the `Authorization` header. The existing development logging in `/api/chat` prints
  only the question and file name, which is fine.

### 6.3 A small login client for the browser

One module that owns everything about the login service and the pass. Its duties:

1. **Ask the login service** (`/auth/session`, `/auth/token`) as described in 5.1.
2. **Keep the pass in memory only.** Never in `localStorage`, `sessionStorage`, a cookie, React
   state that gets serialised, or a log line.
3. **Hand out a valid pass.** If fewer than 60 seconds remain before `expiresAt`, ask
   `/auth/token` first. Ask at most once per request, and use what comes back even if it is
   the same pass again. Several callers at once must share one `/auth/token` request.
4. **One wrapper for every call to this app's server** (`/backend/...` and `/api/chat`). It adds
   the base path and the `Authorization` header and leaves everything else about the request
   alone. In particular it must not set `Content-Type` for a `FormData` body.
5. **React to a 401 the way the defect agent's client does:**
   - Get a new pass from `/auth/token`.
   - If the request was a read (`GET` or `HEAD`), send it once more with the new pass. If that
     also answers 401, the login is treated as ended.
   - If the request was a write, do not send it again. Return the 401 to the caller, which
     shows its normal error. The next request uses the new pass.
   - If `/auth/token` itself answers 401 at any point, the login has ended.
6. **React to a 403** by reading `code` from a copy of the body, without assuming it is JSON:
   `account_inactive` and `user_mismatch` are reported to the provider (6.4). The response is
   still returned to the caller.
7. **Build the login address** (`/auth/login?callbackUrl=` plus the encoded current address) and
   the logout address (`/auth/logout`).
8. **Remember that a login redirect was already tried in this tab,** in `sessionStorage`. This is
   what prevents a redirect loop when login fails (6.4).

A reference for the subtle part, to show the intended behaviour. Adapt it freely:

```ts
const AUTH = "/auth";                              // top of the site, never under BASE_PATH
const RENEW_MARGIN_SECONDS = 60;

let pass: string | null = null;
let expiresAt = 0;                                 // unix seconds
let renewing: Promise<string> | null = null;       // one /auth/token request at a time

export class LoginEndedError extends Error {}

async function authGet<T>(path: string): Promise<T> {
  const res = await fetch(AUTH + path, { credentials: "include", cache: "no-store" });
  if (res.status === 401) throw new LoginEndedError();
  if (!res.ok) throw new Error(`login service answered ${res.status}`);
  return (await res.json()) as T;
}

export function getPass(force = false): Promise<string> {
  const fresh = pass !== null && expiresAt > Date.now() / 1000 + RENEW_MARGIN_SECONDS;
  if (fresh && !force) return Promise.resolve(pass as string);

  renewing ??= authGet<{ accessToken: string; expiresAt: number }>("/token")
    .then((token) => {
      pass = token.accessToken;
      expiresAt = token.expiresAt;
      return token.accessToken;
    })
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

  try {
    let res = await send(false);

    if (res.status === 401) {
      const isRead = ["GET", "HEAD"].includes((init.method ?? "GET").toUpperCase());
      if (isRead) {
        res = await send(true);
        if (res.status === 401) report("login-ended");
      } else {
        await getPass(true);                       // for the next call; a write is not resent
      }
    }

    if (res.status === 403) {
      const code = await res.clone().json().then((body) => body?.code, () => undefined);
      if (code === "account_inactive") report("account-inactive");
      if (code === "user_mismatch") report("user-mismatch");
    }

    return res;
  } catch (error) {
    if (error instanceof LoginEndedError) report("login-ended");
    throw error;
  }
}
```

`report` stands for whatever you use to tell the provider: a listener, a small store, anything.

### 6.4 The provider and the gate

Replace the contents of `src/providers/user-provider.tsx` and `src/components/user-gate.tsx`.
Keep the two components and the `useUser()` hook so `layout.tsx` and the consumers stay simple.
`useUser().userId` must keep returning the ID the chat uses, now taken from `/auth/me`.

**States**

| State | Meaning | What the gate shows |
|---|---|---|
| `loading` | The first check is running | Nothing, or a quiet spinner. No flash of the app |
| `redirecting` | The browser is on its way to the login page | A short "going to Samsung SSO" line |
| `signed-out` | Not logged in, and a redirect was already tried in this tab | A "Log in" link to the login address, and "Check again" |
| `pending` | Logged in, `is_active` is false | "Waiting for approval", the person's `user_id`, "Check again", "Log out" |
| `ready` | Logged in and approved | The app (`children`) |
| `error` | The login service or `/auth/me` could not be asked | A short message and "Try again" |

Render `children` only in `ready`. In every other state the chat must be unmounted, so that its
polling stops and no stale error banner shows.

**The start sequence** (on mount, on "Check again", on "Try again", and after the login ended):

1. `GET /auth/session`. A network failure or a non-200 answer gives `error`. Do not redirect on
   an error.
2. Not authenticated:
   - If the "already tried" mark is set in `sessionStorage`: state `signed-out`.
   - Otherwise set the mark, state `redirecting`, and `window.location.replace(<login address>)`.
3. Authenticated: get the pass. A 401 from `/auth/token` here is handled like step 2.
4. `GET <base path>/backend/auth/me` with the pass.
   - 401 even after one new pass: handle like step 2.
   - Any other failure: `error`.
   - Success: remove the "already tried" mark, keep the reply, and go to `ready` or `pending`
     by `is_active`.

Removing the mark on success is what lets the hourly re-login redirect by itself again, while a
login that keeps failing stops after one attempt and shows the button.

Run this sequence as one shared operation. React runs effects twice in development, and two
copies would race on the mark and call `/auth/me` twice.

**While the app is running**

| Event from 6.3 | Reaction |
|---|---|
| Login ended | Forget the pass and run the start sequence again. Because the mark was removed on the last success, this redirects to login by itself, and login returns to the same address |
| `account_inactive` | State `pending`. An admin took the approval away while the person was using the app |
| `user_mismatch` | `window.location.reload()`, once. Guard it with a flag in `sessionStorage` that the next successful start removes. If it happens again while the flag is set, show `error` instead of reloading again |

Several requests can fail at the same moment (the sidebar polls every 5 seconds, the chat polls
every 3 seconds while it waits for a reply). The reaction must happen once.

**Remove**

- The knox ID form and `setUserId`.
- `mock_user_id`. Delete that key from `localStorage` once at start, so it does not linger.
- The idle timer, `keepAlive`, the activity listeners and the cross-tab `storage` listener.
- The commented-out old provider at the top of the file.
- The `router.replace("/chat/new")` in the gate. The address must stay what it is, because it
  becomes the `callbackUrl`.

**When a different person uses the same browser**

Keep the last `user_id` in `localStorage` as a plain marker (it is an ID, not a credential).
When `/auth/me` returns a different one, remove the saved drafts (every `localStorage` key that
starts with `chat_draft:`) before showing the app, then store the new ID. Otherwise the next
person finds the previous person's unsent text in the new-chat box.

### 6.5 The call sites

- `src/lib/session-api.ts`: all eight calls go through the wrapper. Their own error handling
  (`throw new Error(...)` on a non-OK answer) stays.
- `src/components/chat/chat-view.tsx`:
  - The `/api/chat` call (line 517) goes through the wrapper.
  - Look at `response.ok` before `response.json()` (line 522). Today a refusal would be parsed
    as if it were a reply. A non-OK answer should end in the existing error line.
  - `handleSend` (line 436) clears the box (line 445) and may create a session before the first
    request is sent. Make sure the login is still alive before that point, by getting a valid
    pass first. If the login has ended, do not clear the box and do not create a session: let
    the provider take over. The text is already saved as a draft, so it is back in the box after
    the login round trip.
  - The base path for the three addresses in 6.1.
- `src/components/chat/session-sidebar.tsx`: the logout (6.6) and the base path in the comparison
  on line 215. The account row keeps showing `userId`.
- `src/components/chat/message-item.tsx`: nothing to change. It loads images through
  `SessionStorage.loadArtifact`, which now goes through the wrapper.

### 6.6 Logout

`handleLogout` in the sidebar (line 271): set the "already tried" mark, forget the pass, then
navigate to `/auth/logout`. The mark is what stops the app from logging straight back in if the
person returns to it in the same tab. They then see `signed-out` with the "Log in" link.

### 6.7 Local development must keep working

After this change the app cannot get past the gate on `localhost`, because no login service
exists there. Provide a stand-in so the app can still be run and tried locally:

- A small, dependency-free Node script outside `src/`, for example `dev/mock-login-service.mjs`.
  It is a development tool. It must never be imported by the app and never run in the image.
- It answers the four addresses of 5.1 the way the real service does: `/auth/session`,
  `/auth/token`, `/auth/login?callbackUrl=` (mark the person as logged in, then redirect to the
  callback address) and `/auth/logout`.
- It creates a real signed pass, so that a backend running locally with the same secret accepts
  it. The pass is a JWT signed with HS256 (`node:crypto`, HMAC-SHA256 over
  `base64url(header) + "." + base64url(payload)`, key is the secret as UTF-8 text). The backend
  accepts a pass only if all of this holds:
  - `iss` is `web-auth`, `aud` is `dice-backend`, `type` is `service`
  - `exp` is in the future and `sub` is present
  - `sub` and `username` are the same login ID (no spaces, no `/` or `\`)

  ```json
  { "sub": "gildong.hong", "username": "gildong.hong",
    "email": "gildong.hong@samsung.com", "full_name": "gildong.hong@samsung.com",
    "department": null, "company": null, "unique_name": null, "sid": null, "roles": [],
    "type": "service", "iss": "web-auth", "aud": "dice-backend",
    "iat": 1795062427, "exp": 1795066027 }
  ```

- Settings through environment variables: the secret (it must equal the local backend's
  `AUTH_SERVICE_JWT_SECRET`, and must never be the production secret), the login ID to hand out,
  the port. Make the pass lifetime settable too, so expiry can be tried in a minute instead of
  an hour.
- Connect it to `next dev` with a rewrite that exists only when a development variable is set,
  for example:

  ```js
  // next.config.mjs, only when process.env.AUTH_DEV_PROXY_TARGET is set
  { source: "/auth/:path*", destination: `${target}/auth/:path*`, basePath: false }
  ```

  `basePath: false` is what makes the rewrite apply at the top of the site. With the variable
  unset, which is the case in the Docker build, the rewrite must not exist.

For a person to get past "waiting for approval" against a local backend, their login ID has to
be an admin or be approved there. The backend's own notes cover that; mention in the docs that
the simplest way is one row in the backend's `user_admins` table:
`INSERT INTO user_admins (user_id, added_by) VALUES ('<login id>', 'bootstrap');`

### 6.8 Documentation

Update what describes behaviour you changed: `.env.example`, `DEPLOY.md` (the base path build
arg, and that the app now works only behind the DICE address), and the parts of `STRUCTURE.md`
that describe the stand-in login. Leave the dated note files in the repository root
(`update_*.md`, `WAITING_STATE.md` and similar) as they are.

`DEPLOY.md` should also say: deploy this version only after the backend with authorization is
running. This version makes the backend reachable from the DICE address through `/backend/...`,
so the backend must already be checking passes.

## 7. Things that are easy to get wrong

- **`/auth/me` versus `/auth/...`.** `<base path>/backend/auth/me` is the backend. `/auth/session`,
  `/auth/token`, `/auth/login` and `/auth/logout` are the login service at the top of the site.
  Mixing up the prefixes is the most likely bug.
- **Redirect loops.** A failing login must end on the `signed-out` screen after one redirect
  attempt per tab. Check this case on purpose.
- **Losing the address.** The person must return from login to the chat they were on. Do not
  navigate to `/chat/new` while logged out.
- **Losing a typed question.** The hourly login round trip is a full page navigation. Unsent
  text survives because every keystroke is saved as a draft. A question that was already sent
  keeps running in the backend, and the page already knows how to wait for it after a reload
  (the `run_state` polling in `chat-view.tsx`). What must not happen is that the box is cleared
  and the request then fails on a dead login (6.5).
- **Polling with a dead login.** The sidebar and the chat poll all the time. When the login
  ends, the next poll notices. That must lead to one clean reaction, not an error banner and
  not repeated redirects.
- **`/auth/token` in the last minute.** Close to expiry the login service keeps returning the
  same pass. A loop that asks again until the pass looks fresh would never end.
- **`FormData`.** The wrapper must not set `Content-Type` on the `/api/chat` request.
- **Double base path.** `router.push("/chat/new")` already gets the base path. Hand-written
  addresses do not.
- **Hydration.** The provider starts in `loading` on the server and in the browser alike, and
  only then asks the login service.
- **The back button after logout.** A page restored from the browser's history must not still
  hold a pass. Forgetting the pass before navigating to `/auth/logout` covers it.

## 8. Not part of this task

- An admin page. The backend has admin addresses (`/admin/users`, `/admin/admins`). Nothing in
  the app calls them yet. Keep `is_admin` from `/auth/me` available in the context for later,
  and build nothing on it now.
- Any auth library (NextAuth and similar), Next.js middleware that checks login, or server-side
  session handling. The page shell is public and holds no data. All protection is in the
  backend.
- Changes to the backend, the gateway rule, or the login service.
- Showing the person's real name or department in the UI. The account row keeps showing the ID.
- Deployment. You prepare the image settings. The user deploys.

## 9. Checking your work

Static checks, all of which should pass:

```
npm run lint
npx tsc --noEmit
npm run build                                  # no base path
NEXT_PUBLIC_BASE_PATH=/data-agent npm run build
```

On Windows, Git Bash can rewrite a value that starts with `/` into a Windows folder path before
Node sees it. If the base path comes out as something like `C:/Program Files/Git/data-agent`,
that is what happened. Set the variable in PowerShell, or in a local `.env.local` file, for
that build.

Then run the app against the stand-in from 6.7. If you have no backend to run against, write a
throwaway fake of the backend addresses the page calls (`/auth/me` and the ones in
`session-api.ts` and `/api/chat`) and point `BACKEND_ORIGIN` at it. A fake that logs the
`Authorization` header of each call lets you confirm the pass arrives everywhere. Whether you
keep that fake under `dev/` is your call. If you keep it, document it.

Try each of these, with and without the base path where it matters:

1. Not logged in: one redirect to login, back to the same address, the app starts.
2. Login does not succeed: no loop, the `signed-out` screen appears, "Log in" works.
3. Approved person: the session list loads, a question can be sent with and without an image,
   a stored image shows after reopening the chat, rename and delete work. Every request to the
   backend carries the pass.
4. Not approved (`is_active: false`): the waiting screen, and no call to `/apps/...` is made.
   "Check again" lets the person in once they are approved.
5. Approval taken away while the app is open (a 403 `account_inactive` on a poll): the waiting
   screen.
6. The pass expires while the login is alive (short pass lifetime): requests keep working, no
   reload.
7. The login ends while the app is open: one redirect to login, back on the same chat, unsent
   text still in the box.
8. "Send" pressed after the login ended: the text stays in the box.
9. Another person logs in in the same browser: one reload, the new person's data, no reload
   loop, the previous person's draft is gone.
10. Logout: the browser goes to `/auth/logout`. Coming back to the app in that tab shows
    `signed-out`, not an automatic login.
11. With the base path: `/data-agent` leads to `/data-agent/chat/new`, styles and scripts load,
    the suggested questions load, the address bar is right after "new chat" and after the first
    message, and a reload on `/data-agent/chat/<id>` opens that chat.
12. Two tabs open at once behave sensibly through cases 7 and 10.

Verify as far as your tools allow. If you cannot drive a browser, check what you can (the server
routes with `curl`, the build, the logic by reading it again) and say plainly which of the
twelve you could not try.

What cannot be checked on a development machine at all, and has to wait for the deployment
behind `https://dice.gtrai.sec.samsung.net/data-agent`: the real Samsung SSO round trip, the
cookie on the real address, and the gateway's handling of `/data-agent`.

## 10. Your final report to the user

The user develops both repositories and is fluent in Python and TypeScript, but new to
authentication. Write the report in plain words, define a term the first time you use it, and
give one clear statement of where things stand instead of a list of options.

Include:

- What now happens when a person opens the app, in a few sentences.
- The files you changed or added, each with one line on why.
- Which of the twelve checks you ran, how, and what you saw. Which you could not run.
- Anything in this brief that did not match the code, and what you did about it.
- What the user has to do next: build the image (the base path is the default build arg), deploy
  it only after the backend with authorization is running, and open the app through the DICE
  address. List the few things they should click through there, taken from section 9.
- That nothing was committed, unless they asked you to.
