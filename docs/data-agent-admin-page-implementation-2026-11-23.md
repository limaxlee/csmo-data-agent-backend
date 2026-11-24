# Data agent admin page: implementation guide

Written 2026-11-23. It continues `data-agent-auth-implementation-2026-11-21.md`, which built the
login, the approval gate and the first admin addresses in the backend.

This document describes everything needed to give admins a page inside the data agent, in the
order the work should be done. It assumes no background in authorization or in web frontends.

No secret values are written here.

The backend part is implemented since 2026-11-24 and not deployed. The frontend part is not
implemented yet. For the frontend this document is the direction to implement from.

## Contents

- [What changed since 2026-11-23](#what-changed-since-2026-11-23)
- [Summary and status](#summary-and-status)
- [Words used in this document](#words-used-in-this-document)
- [What you asked for, and where it lands](#what-you-asked-for-and-where-it-lands)
- [How the admin page works](#how-the-admin-page-works)
- [Part 1: Checks before starting](#part-1-checks-before-starting)
- [Part 2: Backend changes](#part-2-backend-changes)
- [Part 3: Frontend implementation](#part-3-frontend-implementation)
- [Part 4: Deploying and testing](#part-4-deploying-and-testing)
- [Part 5: Risks to settle](#part-5-risks-to-settle)
- [Part 6: Left out on purpose](#part-6-left-out-on-purpose)
- [Part 7: Where each fact comes from](#part-7-where-each-fact-comes-from)

---

## What changed since 2026-11-23

Added on 2026-11-24, after the two checks were run and both repos were looked at once more.

1. **Both checks passed.** The chat table has the expected columns, and its times are UTC
   ([Part 1](#part-1-checks-before-starting)). Nothing in Part 2 has to change because of them.
2. **Three additions to the backend part,** found while checking the plan against the code
   ([2.9](#29-where-the-code-goes)): `status` must not become a required field, the framework's
   tables should be created at start, and one test imports a function that the plan moves.
3. **The frontend cannot be built on the development PC.** The file `src/app/dice_icon.png` is
   imported by the chat sidebar and exists neither in git nor on that PC. This has to be solved
   before the frontend work starts ([3.12](#312-working-on-it-locally-and-checking-the-work)).
4. **The frontend's style check already reports 5 errors,** all in the chat code. The rule for
   this work is therefore "no new problems", not "no problems" (3.12).
5. **A name on the server differs from the repo.** The backend container is called
   `data_agent_backend` there. The run scripts in both repos say `da_backend`. The commands in
   Part 1 are corrected. The deploy steps in Part 4 and in the two earlier documents still need
   the real names ([Part 4](#part-4-deploying-and-testing)).

6. **The backend part is implemented** (2026-11-24, later that day). The addresses, parameters
   and replies are exactly the ones of [Part 2](#part-2-backend-changes). Sections 2.9 and 2.11
   now describe what was built. It is not committed and not deployed.

State of the repos on 2026-11-24, before the backend work: both on `develop-261123`, nothing
uncommitted, both pushed (backend `017a07a`, frontend `3a1edad`). The backend's tests stood at
174 passing, with the one known, unrelated failure.

---

## Summary and status

**Goal.** An admin opens "Admin" from the account menu of the data agent. There they see who is
waiting for approval and approve them, look through all accounts, take an approval away, make
another person an admin, and look through the visits and the chats of every person, with
filters. Nobody who is not an admin gets any of this data.

**How.** The page is a new part of the existing frontend. It gets its data from the backend's
`/admin/...` addresses, through the frontend server, with the same pass as every other request.
The backend already decides who is an admin. Three of the seven features only need a page. The
other four also need the backend to filter and to offer two new lists.

**The work, in order.**

1. Run the two checks in [Part 1](#part-1-checks-before-starting). **Done on 2026-11-24.**
2. Backend: filters and pages for the account list, a visit list for all people, a chat list for
   all people ([Part 2](#part-2-backend-changes)). **Done on 2026-11-24, not deployed.**
3. Frontend: first put the icon file in place (3.12). Then the admin area with five tabs
   ([Part 3](#part-3-frontend-implementation)).
4. Deploy the backend, then the frontend, and test ([Part 4](#part-4-deploying-and-testing)).

**Decisions.** All of these are my proposals, made from your list of seven features. The rows
marked "choice" are the ones where a real alternative exists. Say so if you disagree with any.

| Decision | Value | Note |
|---|---|---|
| Who is protected by what | The backend refuses everyone who is not an admin. The page only hides the menu entry | as built on 2026-11-22 |
| Address of the admin area | `https://dice.gtrai.sec.samsung.net/data-agent/admin/...` | |
| Where filtering happens | In the backend, in the database. Every list comes in pages, and the page asks for 50 rows at a time | choice |
| How to search | One search box per list, plus fixed filters (status, admin, dates). Not one box per column | choice |
| "Waiting" | Never approved, and not an admin | choice |
| "Deactivated" | Was approved once, and the approval was taken away. Shown apart from "waiting" | choice |
| Visits of all people | A new address `GET /admin/access-log`. The existing one per person stays | |
| Chats of all people | A new address `GET /admin/sessions`. It reads the agent framework's own table, read-only | choice |
| What an admin sees of a chat | Owner, title, ID, created, last activity, running or not. Not the conversation | choice |
| Your own row | The page offers no "Deactivate" and no "Remove admin" on your own row | choice |
| An "Admins" tab | Added, although it is not in your list. "Make admin" needs a way back, and an admin can exist without an account | choice |
| New packages in the frontend | None | |

**Status on 2026-11-23.**

- Login and approval are deployed and work on the DICE address.
- The backend has six admin addresses ([2.1](#21-what-existed-before-this-work)). Until now they
  are used from the browser's developer tools only.
- The frontend knows whether the person is an admin (`isAdmin` in `useUser()`), and builds
  nothing on it yet.
- Both repos are on the branch `develop-261123`. On 2026-11-23 the frontend had uncommitted
  changes in `chat-view.tsx` and `session-sidebar.tsx`. They are committed since (`3a1edad`).

---

## Words used in this document

| Word | Meaning |
|---|---|
| Account | One row in the table `user_accounts`. It appears the first time a person opens the data agent |
| Admin | A person whose login ID is in the table `user_admins`. An admin can always use the data agent, approved or not |
| Approved, active | The account's `is_active` is true. Set by an admin |
| Waiting | The account was never approved |
| Deactivated | The account was approved, and an admin took the approval away |
| Visit, access log | One row in `user_access_log`: who, when, from which address, with which browser. Written each time the page is opened |
| Chat, session | One conversation. The backend and the code call it a session |
| Agent framework | Google ADK, the library the backend uses to run the agent. It stores chats in tables of its own (`sessions`, `events`) |
| Filter | A condition that narrows a list, for example "only waiting" or "from 1 November" |
| Page (of a list) | A list is delivered in parts. `limit` is how many rows one part has, `offset` is how many rows are skipped before it, `total` is how many rows match altogether |
| Tab | One of the five views of the admin area. Each has its own address |
| UTC | The world's reference time, without a time zone. Korea is 9 hours ahead of it |
| Frontend server | The Next.js program on port 13080. It sends the page and passes the page's requests on to the backend |
| Pass | The signed text from the DICE login service that the page sends with every request |

---

## What you asked for, and where it lands

| # | You asked for | Tab | Backend address | Backend today |
|---|---|---|---|---|
| 1 | See the accounts and their information, filtered by user ID and other fields | Users | `GET /admin/users` | Exists. Filters, pages and `status` are added |
| 2 | See who is waiting for activation | Waiting | `GET /admin/users?status=waiting&is_admin=false` | `status` is added |
| 3 | Activate a waiting account | Waiting, Users | `PATCH /admin/users/{user_id}?is_active=true` | Exists |
| 4 | Make an account admin | Users, Admins | `PUT /admin/admins/{user_id}` | Exists |
| 5 | Deactivate an account | Users | `PATCH /admin/users/{user_id}?is_active=false` | Exists |
| 6 | See the access log, filtered by date and user | Access log | `GET /admin/access-log` | New |
| 7 | See the chats per user, filtered by user and creation date | Sessions | `GET /admin/sessions` | New |

Added by me: removing an admin (`DELETE /admin/admins/{user_id}`, exists) and the list of admins
(`GET /admin/admins`, exists).

---

## How the admin page works

### Who is involved

Nothing new. The same four as for every other request of the data agent.

| Who | Role for the admin page |
|---|---|
| Browser | Shows the admin area. Holds the pass |
| Gateway | Forwards `/data-agent/...` to the frontend server. The rule does not change |
| Frontend server | Sends the page. Passes `/data-agent/backend/admin/...` on to the backend as `/admin/...`, unchanged, with the pass. This already works for every address |
| Backend | Checks the pass, looks the caller up in `user_admins`, answers or refuses |

### The steps

1. The person opens the data agent and is logged in and approved as before.
2. The page asked the backend "who am I" at the start (`/auth/me`). The answer says `is_admin`.
   If it is true, the account menu shows an entry "Admin".
3. The entry leads to `/data-agent/admin`. The admin area appears, with the tab "Users".
4. Every tab asks the backend for its list, for example
   `GET /data-agent/backend/admin/users?status=waiting&limit=50`, with the pass.
5. The backend checks the pass and reads `user_admins`. An admin gets the list. Anyone else gets
   403 with the code `admin_required`.
6. A button, for example "Activate", sends one request and then asks for the list again.

### Hiding is not protecting

The code of the admin area is part of the frontend, and anyone who can open the data agent can
download it. It contains no data. Every row on the admin area comes from the backend, and the
backend reads `user_admins` on every single request. So:

- A person who types the admin address by hand sees an empty frame and a refusal.
- An admin who is removed loses the data at their next request, without a new login.

### Two things that look alike

| Address in the browser | What it is |
|---|---|
| `/data-agent/admin/users` | A view of the frontend. A page |
| `/data-agent/backend/admin/users` | The backend's list of accounts. Data |

Mixing them up is the most likely mistake in Part 3.

---

## Part 1: Checks before starting

The chat list for admins reads a table that belongs to the agent framework. Both checks look at
that table on the real database. They use the backend's own database settings, like the admin
commands in `data-agent-auth-deploy-and-test-2026-11-22.md`.

### Results

Both were run on the server on 2026-11-24.

| # | Check | Result |
|---|---|---|
| 1 | The chat table has the expected columns | Passed. Exactly the six columns, with the expected types |
| 2 | Chat times are stored in UTC | Passed: they are UTC. See below for how this is known |

About check 2. The newest chat in the reply was 19 hours old, so the comparison "within a
minute of `utc_now`" could not be made. The answer is still certain, for two reasons:

- `db_zone` is `Etc/UTC`. With the database itself on UTC, both ways the framework has of
  filling in the time give UTC: writing it itself, which version 2.4.0 does, and letting the
  database fill it in, which older versions did.
- The newest chat is stored with `04:42:06.020`. The backend's own log from 2026-11-23 has the
  line "Created session for user m.alenova" at `04:42:06,025`. That was early afternoon in
  Korea, so both clocks show UTC.

Because `db_zone` is `Etc/UTC`, the note about old chats being off by some hours does not apply
either.

The container is called `data_agent_backend` on the server. The commands below are corrected to
that name.

### Check 1: the chat table has the expected columns

On the server:

```bash
sudo docker exec data_agent_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; print(asyncio.run(PostgreSQLClient().fetch_all(\"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'sessions' ORDER BY ordinal_position\")))"
```

- Expected: six columns. `app_name`, `user_id` and `id` are `character varying`. `state` is
  `jsonb`. `create_time` and `update_time` are `timestamp without time zone`.
- If a column is missing or has another type: tell me the output. Section 2.6 depends on it.

### Check 2: chat times are stored in UTC

Open the data agent, start a new chat and send one short question. Within a minute, on the
server:

```bash
sudo docker exec data_agent_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; print(asyncio.run(PostgreSQLClient().fetch_all(\"SELECT user_id, create_time, now() AT TIME ZONE 'UTC' AS utc_now, current_setting('TimeZone') AS db_zone FROM sessions ORDER BY create_time DESC LIMIT 3\")))"
```

- Expected: the first row is your new chat, and its `create_time` is within a minute of
  `utc_now`. That means the framework stores UTC, which is what section 2.6 assumes.
- If `create_time` is 9 hours ahead of `utc_now`: the times are stored in Korean time. Tell me.
  One expression in the query of section 2.6 changes.
- Note `db_zone`. If it is not `UTC`, chats created by an older version of the framework may show
  a time that is off by the difference. That would only concern old test chats.

---

## Part 2: Backend changes

**Implemented on 2026-11-24. Not deployed yet.** All paths in this part are in this repo.

Sections 2.1 to 2.8 are the contract: what the page can rely on. They were written before the
work and the code follows them. Sections 2.9 and 2.11 describe what was built.

### 2.1 What existed before this work

Built on 2026-11-22. Every address is for admins only.

| Address | What it does |
|---|---|
| `GET /admin/users` | All accounts, newest first. Optional `?is_active=true` or `false`. No pages: it returns everything |
| `PATCH /admin/users/{user_id}?is_active=true` | Approves. With `false`: takes the approval away |
| `GET /admin/users/{user_id}/access-log` | The visits of one person, newest first. Optional `?limit=`, 1 to 1000 |
| `GET /admin/admins` | All admins |
| `PUT /admin/admins/{user_id}` | Makes that login ID an admin |
| `DELETE /admin/admins/{user_id}` | Removes an admin. Refused for the last one |

What is missing for the page:

- The account list cannot be searched, cannot tell "waiting" from "deactivated", cannot be
  limited to admins, and has no pages.
- Visits can only be read for one person at a time, and not by date.
- There is no way for an admin to see another person's chats. The existing chat addresses
  (`/apps/users/{user_id}/...`) refuse everyone except the owner, admins included. That stays.

### 2.2 What is added, in short

| Address | Change |
|---|---|
| `GET /admin/users` | New filters `search`, `status`, `is_admin`. Pages. Each account says its `status`. The reply says `total` |
| `GET /admin/access-log` | New. Visits of all people, with filters and pages |
| `GET /admin/sessions` | New. Chats of all people, with filters and pages |

One more index on `user_access_log`. No new table, no new column, no new setting.

### 2.3 Rules that hold for all three lists

**Pages.**

| Parameter | Meaning | Users, sessions | Access log |
|---|---|---|---|
| `limit` | Rows in one page | 1 to 200, default 50 | 1 to 1000, default 100 |
| `offset` | Rows skipped before the page | 0 or more, default 0 | the same |

The reply carries `total`: how many rows match the filters, whatever `limit` and `offset` are.

**Search.** `search` is a piece of text. A row matches when the text appears anywhere in one of
the fields that the list searches. Upper and lower case do not matter. `%` and `_` have no
special meaning. An empty `search` is the same as none.

**One person exactly.** `user_id` on the access log and on the sessions means "this person and
nobody else". Upper and lower case do not matter. It exists next to `search` because login IDs
contain each other: a search for `j.kim` also finds `hj.kim`.

**Dates.** A date filter is a moment, written with a time zone, for example
`2026-11-23T00:00:00.000Z` or `2026-11-23T09:00:00+09:00`. `..._from` includes that moment.
`..._to` excludes it. A value without a time zone is refused, because the backend could only
guess which zone was meant.

**Several filters at once** all have to hold.

**Order.** Newest first. Not selectable.

**A bad value** (unknown `status`, `limit=0`, a date without a time zone) is refused with 422,
in FastAPI's standard shape. In that shape `detail` is a list, not a text.

**Times in replies** carry a time zone. The page turns them into the admin's local time.

### 2.4 `GET /admin/users`

| Parameter | Value | Keeps accounts where |
|---|---|---|
| `search` | text, up to 255 characters | the text appears in `user_id`, `email`, `full_name`, `department` or `company` |
| `status` | `waiting`, `active` or `deactivated` | see below |
| `is_admin` | `true` or `false` | the person is, or is not, in `user_admins` |
| `is_active` | `true` or `false` | unchanged from today |
| `limit`, `offset` | see 2.3 | |

What `status` means:

| `status` | Rule | In words |
|---|---|---|
| `waiting` | `is_active` is false and `activated_at` is empty | Never approved |
| `active` | `is_active` is true | Approved |
| `deactivated` | `is_active` is false and `activated_at` is filled | Approved once, then taken away |

This works without a new column, because taking an approval away keeps `activated_at` and
`activated_by`.

`status` is about the approval only. Being an admin is separate. An admin who was never approved
has the status `waiting` and still has full access. This is why the "Waiting" tab asks for
`status=waiting&is_admin=false`.

Reply:

```json
{
  "users": [
    {
      "user_id": "gildong.hong",
      "is_active": false,
      "is_admin": false,
      "status": "waiting",
      "email": "gildong.hong@samsung.com",
      "full_name": "gildong.hong@samsung.com",
      "department": "Some Department",
      "company": "Some Site",
      "unique_name": "CORP\\gildong.hong",
      "sid": "S-1-5-21-...",
      "roles": [],
      "created_at": "2026-11-23T01:00:00Z",
      "activated_at": null,
      "activated_by": null,
      "last_access_at": "2026-11-23T01:00:00Z",
      "last_access_ip": "10.254.163.69"
    }
  ],
  "total": 1
}
```

Compared with today: `status` in each account and `total` are new. The reply of
`PATCH /admin/users/{user_id}` is one account in the same shape, so it gains `status` too.

One thing changes for an existing caller: without `limit`, the list now stops at 50 accounts.
The only caller today is the helper typed into the browser's developer tools.

### 2.5 `GET /admin/access-log`

| Parameter | Value | Keeps visits where |
|---|---|---|
| `user_id` | a login ID | the visit is this person's |
| `search` | text | the text appears in the `user_id` or in the `ip_address` |
| `accessed_from` | a moment | the visit is at or after it |
| `accessed_to` | a moment | the visit is before it |
| `limit`, `offset` | see 2.3 | |

Reply:

```json
{
  "access_logs": [
    {
      "user_id": "gildong.hong",
      "accessed_at": "2026-11-23T01:00:00Z",
      "ip_address": "10.254.163.69",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
    }
  ],
  "total": 1
}
```

The existing `GET /admin/users/{user_id}/access-log` stays exactly as it is.

A new index, created at start like the existing one, so that a date range does not have to read
the whole table:

```sql
CREATE INDEX IF NOT EXISTS ix_user_access_log_time ON user_access_log (accessed_at DESC);
```

Until the setting from `data-agent-access-log-ip-2026-11-23.md` is deployed, `ip_address` holds
the frontend container's address for every visit through the page.

### 2.6 `GET /admin/sessions`

| Parameter | Value | Keeps chats where |
|---|---|---|
| `user_id` | a login ID | the chat is this person's |
| `search` | text | the text appears in the owner's `user_id`, in the title or in the session ID |
| `created_from`, `created_to` | moments | the chat was created in that range |
| `updated_from`, `updated_to` | moments | the last activity in the chat is in that range |
| `limit`, `offset` | see 2.3 | |

Reply, newest created first:

```json
{
  "sessions": [
    {
      "user_id": "gildong.hong",
      "session_id": "b48825a2961b4d8b8a01edf4199b1fbb",
      "session_title": "Defect images from line 3",
      "created_at": "2026-11-23T01:00:00Z",
      "last_update_time": "2026-11-23T01:04:10Z",
      "run_state": "idle"
    }
  ],
  "total": 1
}
```

- `session_title` is `null` for a chat that has no title yet. The page then shows the session
  ID, as the chat sidebar does.
- `run_state` is `running` while the agent is answering in that chat, otherwise `idle`.
- The messages are not in the reply, and there is no admin address that returns them.

**Why this reads the framework's table directly.** The framework offers one way to list chats:
all chats of one person, or all chats of everybody, with no filter, no pages and no creation
time. Its `sessions` table has what is needed: `user_id`, `id`, `state` (which holds the title
under `session_title`), `create_time` and `update_time`. So this one list is read with a
statement of our own, read-only, limited to the app name `data_agent`. Everything else about
chats keeps going through the framework.

What this costs: the table's layout belongs to the framework. The framework version is pinned
(`google-adk[extensions]==2.4.0`), so the layout can only change when that line changes. Part 5
item 4 says what to do then.

**The times.** The framework stores `create_time` and `update_time` without a time zone, and
fills them with UTC, whatever zone the database is set to. The statement therefore says
"this is UTC" when it reads them. Check 2 in Part 1 confirms it on the real database.

### 2.7 Addresses that do not change

`PATCH /admin/users/{user_id}`, `GET /admin/admins`, `PUT /admin/admins/{user_id}`,
`DELETE /admin/admins/{user_id}`, `GET /auth/me`, and everything under `/apps/users/...`.

Behaviour of those that the page builds on, from `data-agent-auth-implementation-2026-11-21.md`,
section 3.9:

- Approving again after a deactivation sets `activated_at` and `activated_by` anew.
- Making someone an admin gives them access at once, approved or not.
- Removing an admin who was never approved takes all their access away at once.
- The last admin cannot be removed.
- A login ID can be made admin before that person has ever opened the data agent. Such an admin
  has no account, so they are in the list of admins and not in the list of accounts.

### 2.8 Error replies

Unchanged. Every refusal of the authorization layer has the shape
`{"detail": "...", "code": "..."}`.

| Status | `code` | When, on admin addresses |
|---|---|---|
| 401 | `invalid_token` | No pass, or the pass is not accepted |
| 403 | `admin_required` | The caller is not an admin (any more) |
| 404 | `user_not_found` | No account with that `user_id` |
| 404 | `admin_not_found` | Removing an admin who is not one |
| 409 | `last_admin` | Removing the only admin |
| 400 | none | The `user_id` in the address is not a valid login ID |
| 422 | none | A filter value is not valid. `detail` is a list |

### 2.9 Where the code goes

As built on 2026-11-24.

| File | What it holds now |
|---|---|
| `common/constants.py` | `UserStatus` (`waiting`, `active`, `deactivated`). The page limits `DEFAULT_USER_LIMIT`, `MAX_USER_LIMIT`, `DEFAULT_SESSION_LIMIT`, `MAX_SESSION_LIMIT`. `MAX_SEARCH_LENGTH` |
| `data_agent/schemas/auth.py` | `UserInfo.status`, worked out inside the model. `search`, `status`, `is_admin`, `limit`, `offset` in `ListUsersRequest`. `total` in `ListUsersResponse`. New: `ListAllAccessLogsRequest`, `ListAllAccessLogsResponse` |
| `data_agent/schemas/agent.py` | New: `SessionSummaryInfo` (one row), `ListAllSessionsRequest`, `ListAllSessionsResponse` |
| `data_agent/utils/text.py` (new) | `normalize_text_filter`: removes the spaces around a filter text, and turns an empty one into "no filter" |
| `data_agent/infra/user_repository.py` | `list_users` with the filters and pages. New: `count_users`, `list_all_access_logs`, `count_all_access_logs`. The new index in `initialize` |
| `data_agent/infra/session_repository.py` (new) | `SessionRepository` with `list_sessions` and `count_sessions`: the only statements that read the framework's `sessions` table |
| `data_agent/services/user_manager.py` | `list_users` passes the filters on and returns `total`. New: `list_all_access_logs` |
| `data_agent/services/agent_runner.py` | New: `list_all_sessions`. The runner now also receives the session repository |
| `data_agent/routers/admin.py` | New: `GET /admin/access-log` (`list_all_access_logs`) and `GET /admin/sessions` (`list_all_sessions`). The models are declared with `Depends()`, like the existing ones, so the values travel in the address |
| `data_agent/routers/dependencies.py` | `get_agent_runner` and `AgentRunnerDep` moved here from `routers/agent.py`, so that both routers use the same one |
| `data_agent/app.py` | Creates the session repository, hands it to the runner, and calls `prepare_tables()` on the session service |

Two details of how it was built:

- The status filter is three plain conditions in the `WHERE`, one per status, with the status
  words passed as parameters. They are the same rules as `UserInfo.status`.
- On the access log, `user_id` is compared as `user_id = lower(<the value>)`. Login IDs are
  stored in lower case there, so this ignores case and still uses the existing index. On the
  sessions both sides are lower-cased, because old chats can belong to IDs typed with capitals.

The two habits of `user_repository.py` that the new statements follow:

- A filter that may be absent is written as
  `(CAST(:value AS TEXT) IS NULL OR <condition>)`, as `list_users` already does for `is_active`.
- Values always travel as parameters. Nothing a caller sends is put into the SQL text.

The date parameters are declared as pydantic `AwareDatetime`. This is what refuses a value
without a time zone. The database would accept one silently.

Three things were found on 2026-11-24, before the work. All three are settled in the code: the
status is worked out inside the model, the framework's tables are created at start, and the
test for `get_agent_runner` moved to `tests/routers/test_dependencies.py` together with the
function. The reasons, for whoever changes this code later:

- **`status` must not be a required field that only the list fills.** `UserInfo` is also built
  for every ordinary request, in `UserManager.authorize`, from a statement that does not return
  a status. A required field would make every request of every person fail. Either work the
  status out inside the model from `is_active` and `activated_at`, or return it from every
  statement that returns an account. The filter in the `WHERE` uses the same three rules, and
  one test should hold the two together.
- **Create the framework's tables at start.** The framework creates its tables the first time
  one of its methods is used, not when the backend starts. On the real database they exist. On
  a new, empty one, the statement of 2.10 would fail with "relation sessions does not exist"
  until somebody opens the chat. `DatabaseSessionService.prepare_tables()` is the framework's
  own method for creating them early. Call it once in `data_agent/app.py`, where the service
  is created.
- **Moving `get_agent_runner` touches a test.** `tests/routers/test_agent.py` imports it from
  `data_agent.routers.agent` and uses it to put a fake in its place. After the move, either
  keep the name importable from there or change the import in the test. The test must replace
  the same function object that the router uses.

### 2.10 Sketch

It shows the logic of the one statement that is not obvious. The count uses the same `WHERE`.

```sql
SELECT s.user_id,
       s.id                              AS session_id,
       s.state ->> 'session_title'       AS session_title,
       s.create_time AT TIME ZONE 'UTC'  AS created_at,        -- stored as UTC without a zone
       s.update_time AT TIME ZONE 'UTC'  AS last_update_time,
       COALESCE(l.run_state, 'idle')     AS run_state
FROM sessions s
LEFT JOIN session_run_locks l
       ON l.app_name = s.app_name AND l.user_id = s.user_id AND l.session_id = s.id
WHERE s.app_name = :app
  AND (CAST(:user_id AS TEXT) IS NULL OR lower(s.user_id) = lower(CAST(:user_id AS TEXT)))
  AND (CAST(:search AS TEXT) IS NULL
       OR strpos(lower(concat_ws(' ', s.user_id, s.state ->> 'session_title', s.id)),
                 lower(CAST(:search AS TEXT))) > 0)
  AND (CAST(:created_from AS TIMESTAMPTZ) IS NULL
       OR s.create_time AT TIME ZONE 'UTC' >= CAST(:created_from AS TIMESTAMPTZ))
  AND (CAST(:created_to AS TIMESTAMPTZ) IS NULL
       OR s.create_time AT TIME ZONE 'UTC' <  CAST(:created_to AS TIMESTAMPTZ))
  -- updated_from and updated_to: the same two lines with update_time
ORDER BY s.create_time DESC, s.id
LIMIT :limit OFFSET :offset
```

`strpos` is used instead of `LIKE` because it has no wildcard characters, so nothing a person
types has to be escaped.

The statement as built is in `data_agent/infra/session_repository.py`. It differs from the
sketch only in passing the title key and the word `idle` as parameters.

### 2.11 Tests, and how this was checked

Unit tests, with the database mocked, as the other tests of this repo do. One test function per
function, named after it:

| File | What it covers |
|---|---|
| `tests/schemas/test_schemas.py` (new) | `UserInfo.status`: the three statuses, an admin who was never approved, and that a status sent along with the data cannot overrule the approval columns |
| `tests/utils/test_text.py` (new) | `normalize_text_filter` |
| `tests/infra/test_user_repository.py` | The SQL and parameters of `list_users`, `count_users`, `list_all_access_logs`, `count_all_access_logs`. The new index |
| `tests/infra/test_session_repository.py` (new) | The SQL and parameters of `list_sessions` and `count_sessions`. The app name is always part of the condition, and the framework's table is only read |
| `tests/services/test_user_manager.py` | Filters are passed on, `total` is returned, an empty filter becomes "no filter", a failing count is not swallowed |
| `tests/services/test_agent_runner.py` | `list_all_sessions` |
| `tests/routers/test_admin.py` | The two new addresses in the "admins only" test. Filters arrive in the request model. 422 for an unknown `status`, a `limit` out of range, a date without a time zone |
| `tests/routers/test_dependencies.py`, `test_agent.py` | `get_agent_runner` at its new place |
| `tests/test_app.py` | The new addresses exist. The session repository is created, and `prepare_tables()` is awaited at start |

Result on 2026-11-24: 185 tests pass and 1 fails. The failing one is the same as before,
`tests/services/test_agent_runner.py::TestAgentRunner::test_run`, and has nothing to do with
this work. Before the work the count was 174 passing.

One check went beyond the unit tests, on a throwaway Postgres 16 on the development PC, with the
framework's real tables and the database clock set 9 hours ahead of UTC. The real routers, the
real services and repositories, and the real pass check were called over HTTP with a signed
pass, 72 checks in all:

- No pass gives 401. A person who is not an admin gets 403 `admin_required` on all three lists.
- Accounts: every filter of 2.4 alone and combined, pages, `total`, and 422 for bad values.
  Activating and deactivating change the status as described. For every account, the status
  filter and the status in the reply agree.
- Access log: `user_id` for `j.kim` does not bring `hj.kim`, while `search` does. Search by IP
  address. Date limits, also written with `+09:00`. The list of one person still works.
- Sessions: only chats of this app, title or `null`, running or idle, and `created_at` is the
  real moment although the database clock is 9 hours ahead. All filters of 2.6.
- On a new, empty database the session list fails without `prepare_tables()` and works with it.
- The rest is unchanged: a person's own chat list, the refusal of a waiting person, the refusal
  of an admin who asks for another person's chats, and `/auth/me` without a `status` field.

Not checked: the new code has not run against the database on `10.240.35.180`. The two facts
that could differ there, the columns of the chat table and the time zone of its times, were
confirmed on that database on 2026-11-24 (Part 1).

### 2.12 Trying the backend without the page

On the data agent page, as an admin, press F12, open "Console", and paste the helper from
`data-agent-auth-deploy-and-test-2026-11-22.md`, section "Approving people". Then:

```js
await api("/admin/users?status=waiting&is_admin=false")
await api("/admin/users?search=hong&limit=5")
await api("/admin/access-log?user_id=gildong.hong&accessed_from=2026-11-01T00:00:00Z")
await api("/admin/sessions?search=defect&limit=5")
```

---

## Part 3: Frontend implementation

The frontend is the repo `cosmo-data-agent-frontend`. All paths in this part are in that repo.

### 3.1 What exists today

- A Next.js application (version 16, React 19, Tailwind, components in the style of shadcn/ui).
- Two views, `/chat/new` and `/chat/<session id>`, both showing `ChatView`.
- `src/app/layout.tsx` wraps everything in `UserProvider` and `UserGate`. A view is shown only
  to a person who is logged in and approved.
- `useUser()` (`src/providers/user-provider.tsx`) gives `userId`, `user` and `isAdmin`, taken
  from the backend's `/auth/me` once per page load.
- `apiFetch()` (`src/lib/auth-client.ts`) is the one way the page calls its own server. It adds
  the base path and the pass, renews the pass on a 401, and tells the provider about an ended
  login, `account_inactive` and `user_mismatch`.
- `src/app/backend/[...path]/route.ts` passes any `/backend/<path>` on to the backend, for GET,
  POST, PUT, PATCH and DELETE, with the query string. Nothing has to change there.
- The account menu at the bottom of the chat sidebar
  (`src/components/chat/session-sidebar.tsx`) has one entry, "Log out".
- Ready-made pieces in `src/components/ui/`: button, card, dropdown menu, input, scroll area,
  sheet, switch, tooltip. There is no table, badge or dialog yet.

### 3.2 Addresses of the admin area

Written without the base path. On DICE each one starts with `/data-agent`.

| Address | Tab | Shows |
|---|---|---|
| `/admin` | none | Goes to `/admin/users` |
| `/admin/waiting` | Waiting | Accounts with `status=waiting&is_admin=false` |
| `/admin/users` | Users | All accounts, with filters |
| `/admin/access-log` | Access log | Visits, with filters |
| `/admin/sessions` | Sessions | Chats, with filters |
| `/admin/admins` | Admins | The admins |

The filters of a tab live in its address, for example
`/admin/access-log?user_id=gildong.hong&from=2026-11-01&to=2026-11-23`. Three things depend on
this: a reload keeps the list, the login round trip about once an hour returns to the same
list, and one tab can link to another with a filter already set.

### 3.3 The frame

One layout for all admin addresses (`src/app/admin/layout.tsx`):

- **The guard.** If `useUser().isAdmin` is false, show a short screen "This area is for
  administrators" with a link back to the chat, and nothing else. Do not redirect. The guard is
  for tidiness. The backend is what protects the data.
- **A header** with the title, the five tabs, the theme switch, and "Back to chat" leading to
  `/chat/new`.
- **The count on the "Waiting" tab,** from `total` of
  `GET /admin/users?status=waiting&is_admin=false&limit=1`. Asked when the admin area opens and
  after every action. Not on a timer.

The entry: in the account menu of the chat sidebar, add "Admin" above "Log out", leading to
`/admin`. Show it only when `isAdmin` is true.

### 3.4 The five tabs

**Waiting.** The people who cannot get in and need a decision.

| Column | From |
|---|---|
| Login ID | `user_id` |
| Email | `email` |
| Department, company | `department`, `company` |
| First opened | `created_at` |
| Last visit | `last_access_at`, `last_access_ip` |
| Action | A button "Activate" |

No filters. An empty list says "Nobody is waiting".

**Users.**

| Filter | Control | Sent as |
|---|---|---|
| Search | Text box: "Login ID, email, department, company" | `search` |
| Status | All, Waiting, Active, Deactivated | `status` |
| Role | All, Admins, Not admins | `is_admin` |

| Column | From |
|---|---|
| Login ID | `user_id` |
| Email | `email`. `full_name` is not shown: the login service sends the email there too |
| Department, company | `department`, `company` |
| Status | `status`, as a coloured label |
| Role | "Admin" when `is_admin` |
| First opened | `created_at` |
| Last visit | `last_access_at`, `last_access_ip` |
| Approved | `activated_by` and `activated_at`, for example on hover or in a line below |
| Actions | A menu, see 3.5 |

An admin whose status is not `active` gets a small note beside the role, "has access as admin",
so that nobody wonders why a waiting person can use the data agent.

**Access log.**

| Filter | Control | Sent as |
|---|---|---|
| Person | A label "Only gildong.hong" with a cross to remove it. It appears when the tab was opened from a person's row | `user_id` |
| Search | Text box: "Login ID or IP address" | `search` |
| From, to | Two date fields | `accessed_from`, `accessed_to`, see 3.6 |

Columns: time (`accessed_at`), login ID, IP address, browser (`user_agent`, shortened, with the
full text on hover).

**Sessions.**

| Filter | Control | Sent as |
|---|---|---|
| Person | The same label as on the access log | `user_id` |
| Search | Text box: "Login ID, title or session ID" | `search` |
| Created from, to | Two date fields | `created_from`, `created_to` |
| Last activity from, to | Two date fields | `updated_from`, `updated_to` |

Columns: login ID, title (the session ID when `session_title` is `null`), session ID, created
(`created_at`), last activity (`last_update_time`), and "Running" when `run_state` is `running`.

A row is not a link. An admin cannot open another person's chat.

**Admins.** From `GET /admin/admins`: login ID, added (`added_at`), added by (`added_by`, where
`bootstrap` means "put in by hand in the database"), and a button "Remove admin". Above the
list, one text box and a button "Make admin" for a login ID. This is the place for a person who
has not opened the data agent yet. No pages: the list is short.

### 3.5 Actions and their questions

Every action asks before it is sent, the same way deleting a chat asks today.

| Action | Offered when | Request | The question says |
|---|---|---|---|
| Activate | Status is `waiting` or `deactivated` | `PATCH /admin/users/{id}?is_active=true` | "gildong.hong will be able to use the data agent." |
| Deactivate | Status is `active`, and it is not your own row | `PATCH /admin/users/{id}?is_active=false` | "gildong.hong will be shut out at their next click." For an admin, add: "As an admin they keep their access." |
| Make admin | Not an admin | `PUT /admin/admins/{id}` | "gildong.hong will be able to use the data agent and this admin area, and to approve and remove people, including you." |
| Remove admin | Is an admin, and it is not your own row | `DELETE /admin/admins/{id}` | "gildong.hong will lose this admin area." If their status is not `active`, add: "They are not approved, so they will also lose the data agent." |
| Access log | Always | none: goes to `/admin/access-log?user_id={id}` | no question |
| Sessions | Always | none: goes to `/admin/sessions?user_id={id}` | no question |

After an action that sends a request: ask for the current list again, and for the count on the
"Waiting" tab. Do not change the row by hand and hope it matches.

"Your own row" is the one whose `user_id` equals `useUser().userId`. Another admin can still
deactivate you or remove you. The page only stops you from doing it to yourself by a slip.

### 3.6 Rules for every tab

- **Pages.** 50 rows. Below the table: "1 to 50 of 132", "Previous", "Next". The page number is
  in the address. Changing a filter goes back to the first page.
- **Typing.** Wait about 300 milliseconds after the last key before asking the backend.
- **Late answers.** Answers can arrive in another order than the questions were sent. Only the
  answer to the newest question may be shown.
- **Empty filters** are left out of the request.
- **Dates.** The admin picks days. "From 1 November to 23 November" means both days in full, in
  the admin's own time zone. The page sends the start of the first day as `..._from` and the
  start of the day after the last day as `..._to`, both as moments with a time zone.
- **Times in the table** are shown in the admin's own time zone, as `2026-11-23 10:15`.
- **Three states besides the table:** loading, "nothing found", and "could not load" with a
  "Try again" button.
- **A "Refresh" button** on each tab. Nothing reloads by itself.
- **Long values** (a browser name, a Korean department) must not stretch the table. Cut them and
  show the full text on hover.
- **A narrow window** scrolls the table sideways. The admin area is made for a desktop screen.

### 3.7 What the page does with each refusal

| Answer | What the page does |
|---|---|
| 403 `admin_required` | Replace the whole admin area by "You are no longer an administrator", with a link back to the chat |
| 403 `account_inactive`, `user_mismatch`, an ended login | Nothing. `apiFetch()` tells the provider, which already handles them |
| 404 `user_not_found`, `admin_not_found` | Show the message, then ask for the list again. Somebody else changed it in the meantime |
| 409 `last_admin` | "The last administrator cannot be removed." |
| 401 on a button | "Could not save. Please try again." `apiFetch()` has fetched a new pass and deliberately does not send a change twice |
| 422 | "This filter is not valid." Do not try to print `detail`: it is a list here |
| No answer, or 500 | "Could not load", with "Try again" |

### 3.8 Files to change

| File | Change |
|---|---|
| `src/app/admin/layout.tsx` (new) | The frame of 3.3 |
| `src/app/admin/page.tsx` (new) | Goes to `/admin/users` |
| `src/app/admin/waiting/page.tsx`, `users/page.tsx`, `access-log/page.tsx`, `sessions/page.tsx`, `admins/page.tsx` (new) | One tab each |
| `src/components/admin/` (new) | What the tabs share: filter bar, table states, page buttons, status label, the question before an action |
| `src/components/ui/table.tsx`, `badge.tsx` (new) | In the style of the existing pieces. Neither needs a package |
| `src/lib/admin-api.ts` (new) | Every call to `/backend/admin/...`, with the types of the replies, through `apiFetch()` |
| `src/components/chat/session-sidebar.tsx` | The "Admin" entry in the account menu |
| `STRUCTURE.md` | The new addresses, and a short section on the admin area |

No new package. A question before an action can be the browser's own `confirm()`, as deleting a
chat does today, or a dialog built on `@radix-ui/react-dialog`, which is already installed.
Status, role and the date fields work with plain `<select>` and `<input type="date">`.

### 3.9 Sketch

It shows the logic only.

```ts
// src/lib/admin-api.ts
import { apiFetch } from "./auth-client";

export type UserStatus = "waiting" | "active" | "deactivated";

export interface AdminUser {
  user_id: string;
  is_active: boolean;
  is_admin: boolean;
  status: UserStatus;
  email: string | null;
  department: string | null;
  company: string | null;
  created_at: string;
  activated_at: string | null;
  activated_by: string | null;
  last_access_at: string | null;
  last_access_ip: string | null;
}

export class AdminApiError extends Error {
  constructor(readonly status: number, readonly code?: string) {
    super(`Admin request failed: ${status}`);
  }
}

// path is "/users?..." and so on. apiFetch() adds the base path and the pass.
async function call<T>(path: string, method = "GET"): Promise<T> {
  const res = await apiFetch(`/backend/admin${path}`, {
    method,
    headers: { Accept: "application/json" },
  });

  if (res.ok) return (await res.json()) as T;

  // An error body is not always JSON, and `detail` is a list on a 422.
  const body = await res.json().catch(() => null);

  throw new AdminApiError(res.status, typeof body?.code === "string" ? body.code : undefined);
}

export function listUsers(filters: {
  search?: string;
  status?: UserStatus;
  isAdmin?: boolean;
  page: number;                                   // 1, 2, 3, ...
}) {
  const params = new URLSearchParams({ limit: "50", offset: String((filters.page - 1) * 50) });

  if (filters.search?.trim()) params.set("search", filters.search.trim());
  if (filters.status) params.set("status", filters.status);
  if (filters.isAdmin !== undefined) params.set("is_admin", String(filters.isAdmin));

  return call<{ users: AdminUser[]; total: number }>(`/users?${params}`);
}

export const setActive = (userId: string, isActive: boolean) =>
  call<AdminUser>(`/users/${encodeURIComponent(userId)}?is_active=${isActive}`, "PATCH");

export const makeAdmin = (userId: string) =>
  call(`/admins/${encodeURIComponent(userId)}`, "PUT");

export const removeAdmin = (userId: string) =>
  call(`/admins/${encodeURIComponent(userId)}`, "DELETE");
```

```ts
// A day picked by the admin ("2026-11-23") to the moments the backend wants.
// Without a zone in the text, JavaScript reads it in the admin's own time zone.
const startOfDay = (day: string) => new Date(`${day}T00:00:00`).toISOString();

const startOfNextDay = (day: string) => {
  const date = new Date(`${day}T00:00:00`);
  date.setDate(date.getDate() + 1);
  return date.toISOString();
};

// "from 2026-11-01 to 2026-11-23", both days in full:
//   accessed_from = startOfDay("2026-11-01"), accessed_to = startOfNextDay("2026-11-23")
```

### 3.10 Things that are easy to get wrong

- **Page address and data address.** `/admin/users` is a view. `/backend/admin/users` is the
  data. The same pair exists already as the login service's `/auth/...` and the backend's
  `/backend/auth/me`.
- **Never ask for another person's chat.** A call to `/backend/apps/users/<someone else>/...` is
  answered with 403 `user_mismatch`. `apiFetch()` reads that as "a different person has logged
  in" and reloads the page. The admin area uses `/backend/admin/...` only.
- **`useSearchParams()` needs `<Suspense>` around the component that calls it.** In development
  everything seems to work without it. The production build is where it shows. Run the build.
- **The base path.** `<Link>`, `router.push()` and a redirect get it by themselves, and
  `apiFetch()` adds it to requests. The admin area should need no hand-written address at all.
- **Do not refresh `isAdmin` by calling `/auth/me` again.** Each call is recorded as a visit.
  The value from the page load is good enough for showing the menu entry. The backend's answer
  is what counts.
- **`isAdmin` can be out of date.** An admin can be removed while their admin area is open.
  Every request can therefore answer 403 `admin_required`, and every tab has to handle it.
- **Dates are days in the admin's time zone, not in UTC.** A visit at 08:30 Korean time on
  23 November is 22 November in UTC. With the two helpers in 3.9 it lands on the right day.
- **The last day is included.** The request excludes `..._to`, so the page sends the start of
  the following day.
- **`+` in a time zone.** In an address, a bare `+` means a space. `toISOString()` ends in `Z`
  and avoids it. Build query strings with `URLSearchParams` in any case.
- **A change is not sent twice.** After a 401 on PATCH, PUT or DELETE the admin presses the
  button again. Do not add a retry of your own.
- **Encode the login ID** in an address with `encodeURIComponent`.

### 3.11 Things to expect

- **The first admin shows as "Waiting" in the Users tab,** with the note "has access as admin".
  The first admin was put into `user_admins` by hand and never approved. Activate your own
  account once, so that you keep the data agent if you are ever removed from the admins.
- **A bookmarked admin address, opened while logged out, ends on the DICE home page once.** This
  is the return-address fault of the DICE login service found on 2026-11-23 (check 3). Opening
  the address a second time works. It is the same for every address of the data agent.
- **Old test chats** of login IDs that were typed in before the real login show up in the
  Sessions tab under IDs that have no account.
- **New people are only noticed when an admin looks.** Nothing notifies anyone (Part 5 item 5).

### 3.12 Working on it locally, and checking the work

Locally the admin area needs what the app already needs (`STRUCTURE.md`, "Running locally"): the
stand-in login service `dev/mock-login-service.mjs` and a local backend that shares its secret.
In addition:

- Make the stand-in's login ID an admin in the local backend:
  `INSERT INTO user_admins (user_id, added_by) VALUES ('gildong.hong', 'bootstrap');`
- To get a second person, restart the stand-in with another `MOCK_LOGIN_ID` and open the app
  once. That person is then waiting.

**Before starting: the icon file.** `src/components/chat/session-sidebar.tsx` imports
`@/app/dice_icon.png`. That file was never added to git, and it is not on the development PC.
On 2026-11-24 `npm run build` stops there with "Module not found", and `npm run dev` cannot show
the chat either. The real file is on the server, where the image was built. Copy it into
`src/app/` on the development PC and commit it. Do not commit a stand-in picture: the next
build on the server would then show the stand-in.

Static checks:

```
npm run lint
npx tsc --noEmit
npm run build
NEXT_PUBLIC_BASE_PATH=/data-agent npm run build
```

Where they stand before this work, on 2026-11-24:

| Check | Before this work | Rule for this work |
|---|---|---|
| `npm run lint` | 5 errors and 8 warnings, in `chat-view.tsx`, `message-item.tsx`, `session-sidebar.tsx` and `theme-provider.tsx` | No new problem. The existing ones are in the chat code and are not part of this work |
| `npx tsc --noEmit` | Passes | Passes |
| `npm run build`, both ways | Fails on the missing icon file | Passes, once the icon is in place |

Then try, with and without the base path where it matters:

1. As a person who is not an admin: no "Admin" entry. `/admin/users` typed by hand shows the
   "for administrators" screen, and no list.
2. As an admin: the entry is there, and each of the five tabs loads.
3. Waiting: a new person appears, "Activate" lets them in, the count goes down.
4. Users: search, status and role narrow the list, alone and together. The address changes with
   them, and a reload keeps them.
5. Deactivate an active person. Their open page shows "Waiting for approval" within seconds.
   Their status is "Deactivated", not "Waiting".
6. Make a person admin, and remove them again. Your own row offers neither "Deactivate" nor
   "Remove admin".
7. "Access log" in a person's menu opens that tab with the label "Only ...". The dates narrow
   it, and both end days are included.
8. Sessions: the same with a person, with a search for a title, and with the creation dates.
9. More than 50 rows: "Next" and "Previous" work, and a new filter returns to the first page.
10. Type quickly in a search box: the list ends on the result for the full text.
11. Remove your admin right from another browser while your admin area is open: the next click
    shows "You are no longer an administrator".
12. The chat still works after "Back to chat", and nothing in the chat changed.

---

## Part 4: Deploying and testing

### Order

1. **Backend first.** What it adds does not disturb the frontend that is running. At its start
   it creates the new index.
2. **Frontend second.** With the old backend, the tabs "Access log" and "Sessions" would answer
   "could not load", because their addresses do not exist there.

Build and start both the same way as for the login work
(`data-agent-auth-deploy-and-test-2026-11-22.md`, steps A4, B1 and B4). What differs:

- No setting, no secret and no forwarding rule changes.
- **Use the names that are real on the server.** That document, and the run scripts in both
  repos, call the backend container `da_backend`. On the server it is `data_agent_backend`
  (seen on 2026-11-24). The other names (frontend container, images, Docker network) were not
  checked. `sudo docker ps --format '{{.Names}}  {{.Image}}  {{.Networks}}'` shows them all.
- If the backend run script has the option `-e FORWARDED_ALLOW_IPS=...`, it stays.
- The two `docker tag` lines of step A4 would overwrite the images saved before the login work.
  Use a new name, for example `da-backend:before-admin` and `da-frontend:before-admin`.

Each restart interrupts for a few seconds. A question that is being answered while the backend
restarts is cut off.

### End-to-end test

On `https://dice.gtrai.sec.samsung.net/data-agent`. A second person is needed for several steps.

| Step | Expected |
|---|---|
| Open the account menu as an admin | An entry "Admin" |
| Open it | The Users tab. Your own row says "Admin" |
| Ask a colleague who has never used the data agent to open it | They see "Waiting for approval". The count on the "Waiting" tab goes up after "Refresh" |
| Press "Activate" in their row, and let them press "Check again" | They are in. Their status is "Active", and "Approved" names you |
| Deactivate them while their page is open | Their page shows "Waiting for approval" within seconds. Their status is "Deactivated" |
| Activate them again | They are in again |
| Open "Access log" from their row | Only their visits. The newest is from a few minutes ago |
| Set "From" and "To" to today | The same visits. Set both to yesterday: none of today's |
| Open "Sessions" from your own row | Your chats, with titles and times that match the chat sidebar |
| Make them an admin, and let them reload | They have the "Admin" entry |
| Remove their admin right while their admin area is open | Their next click shows "You are no longer an administrator" |
| As that colleague, not an admin, run `await api("/admin/users")` in the console | `{detail: "Administrator access is required", code: "admin_required"}` |
| As that colleague, open `/data-agent/admin/users` by hand | The "for administrators" screen, and no data |

The rule that the last admin cannot be removed is not in this table on purpose. Trying it on
the production address would remove your own admin right if a second admin happens to exist.
The backend's unit tests cover it.

---

## Part 5: Risks to settle

1. **Admins see what other people asked about.** A chat title is made from the first question,
   so the Sessions tab shows roughly what each person asked. The conversations themselves are
   not shown. This is not a new exposure: an admin can already download the server log
   (`GET /logs`), which contains the questions. Decide who should be an admin with that in mind.
2. **The access log is personal data:** who, when, from which address, with which browser. The
   page makes it easy to look through. The earlier plan's question about a retention limit
   (its Part 6 item 7) becomes more pressing.
3. **Every admin can do everything, and little is recorded.** Any admin can approve, deactivate,
   make and remove admins, including each other. The tables record who approved an account
   (`activated_by`) and who added an admin (`added_by`). Who deactivated an account, and who
   removed an admin, is only in the server log. If that matters, a small table of admin actions
   is the fix. It is not part of this work.
4. **The chat list depends on the framework's table.** If `google-adk` is upgraded in the
   requirements files, run check 1 of Part 1 again before deploying. A changed `sessions` table
   breaks only the Sessions tab, with "could not load". The chat itself is not affected.
5. **Nobody is told when someone is waiting.** An admin sees the count only when they open the
   admin area. Until there is a notification, look regularly, or let people tell you.
6. **The IP addresses are not real yet.** Until the setting in
   `data-agent-access-log-ip-2026-11-23.md` is deployed, the access log and "Last visit" show
   the frontend container's address.
7. **No test environment.** As before, everything is tried on the production address. The admin
   area can lock people out with two clicks. Test with a colleague who knows.
8. **The risks of the login work are still open,** in particular the guessable signing secret
   (`data-agent-auth-implementation-2026-11-21.md`, Part 6 item 1). Whoever can forge a pass can
   name an admin in it, and would get this admin area with it.

---

## Part 6: Left out on purpose

- **Reading another person's conversation,** and deleting or renaming another person's chat.
  The backend has no address for it, and it is a decision about privacy, not about code.
- **Deleting an account.** No address exists. Deactivating is the way to shut someone out.
- **Sorting by a column.** Every list is newest first.
- **Approving several people at once.**
- **Exporting a list** to a file.
- **A record of admin actions** (Part 5 item 3).
- **A notification** about waiting people (Part 5 item 5).
- **Changes to the gateway, the login service, or the frontend's forwarding routes.** None is
  needed.

---

## Part 7: Where each fact comes from

Paths without a repo name are relative to the root of this repo.

| Topic | File |
|---|---|
| The admin addresses that exist, and who may call them | `data_agent/routers/admin.py`, `data_agent/routers/dependencies.py` (`require_admin`) |
| Shapes of the admin requests and replies today | `data_agent/schemas/auth.py` |
| The account, visit and admin tables, and every statement on them | `data_agent/infra/user_repository.py` |
| What deactivating keeps (`activated_at`, `activated_by`) | `data_agent/infra/user_repository.py`, `set_user_active` |
| Admin always has access. The last admin cannot be removed | `data_agent/services/user_manager.py` |
| Refusal codes | `common/constants.py` (`AuthErrorCode`), `data_agent/exceptions/auth.py` |
| The owner-only rule on chat addresses | `data_agent/routers/agent.py`, `require_session_owner` in `data_agent/routers/dependencies.py` |
| How a person's own chat list is built today | `data_agent/services/agent_runner.py`, `list_sessions` |
| Running or idle | `data_agent/infra/session_lock.py`, table `session_run_locks` |
| The framework's chat tables, and that times are stored as UTC without a zone | `google/adk/sessions/schemas/v1.py` and `database_session_service.py` in the installed package, version 2.4.0 |
| The framework's own way to list chats | `google/adk/sessions/base_session_service.py`, `list_sessions` |
| The pinned framework version | `requirements_py313_prod.txt` |
| The earlier plan: tables, endpoints, behaviour worth knowing | `docs/data-agent-auth-implementation-2026-11-21.md`, Part 3 |
| The console helper `api(...)`, the deploy steps | `docs/data-agent-auth-deploy-and-test-2026-11-22.md` |
| The real IP address in the access log | `docs/data-agent-access-log-ip-2026-11-23.md` |
| `isAdmin`, the login states, what the provider reacts to | `cosmo-data-agent-frontend`: `src/providers/user-provider.tsx` |
| `apiFetch()`, and what it does on 401 and 403 | `cosmo-data-agent-frontend`: `src/lib/auth-client.ts` |
| The route that passes requests on to the backend | `cosmo-data-agent-frontend`: `src/app/backend/[...path]/route.ts` |
| The account menu | `cosmo-data-agent-frontend`: `src/components/chat/session-sidebar.tsx` |
| How the existing calls and types are written | `cosmo-data-agent-frontend`: `src/lib/session-api.ts`, `src/lib/types.ts` |
| Existing interface pieces, installed packages | `cosmo-data-agent-frontend`: `src/components/ui/`, `package.json` |
| `useSearchParams()` and `<Suspense>` | `cosmo-data-agent-frontend/node_modules/next/dist/docs/01-app/03-api-reference/04-functions/use-search-params.md` |
| Running the frontend locally | `cosmo-data-agent-frontend`: `STRUCTURE.md`, `dev/mock-login-service.mjs` |
