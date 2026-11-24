# Brief: add an admin area to the data agent frontend

You are working in the repository `cosmo-data-agent-frontend` (Next.js 16, React 19, TypeScript,
Tailwind CSS 4). This brief is the whole task. It was written by the person who built the
backend half, after reading this frontend and the backend. Nobody from that work is in your
session, so everything you need is meant to be here.

Where this brief and the code disagree about the code (a file moved, a name changed), trust the
code and say so in your final report. Where they disagree about the contract (addresses,
parameters, reply shapes, error codes), trust this brief: it was written from the backend code,
and that code was run against a real database.

**This task has two phases, with a stop between them.** First you show the user several design
ideas for the admin area. Then you wait. You write no application code until the user has
chosen. Section 3 says exactly how.

## 1. The task

The data agent has a login and an approval gate: a new person can open the app only after an
administrator ("admin") has approved them. Until now admins do all of this by typing commands
into the browser's developer tools. They need a proper area inside the app.

After your change, an admin can:

1. See all accounts and their information, and narrow the list by login ID and other fields.
2. See who is waiting for approval.
3. Approve ("activate") a waiting person.
4. Make a person an admin, see who the admins are, and remove an admin.
5. Take an approval away ("deactivate").
6. Look through the access log (who opened the app, when, from which address), for one person
   and across everybody, narrowed by date.
7. Look through the chats ("sessions"), for one person and across everybody, narrowed by
   creation date. Only the list: an admin does not read other people's conversations.

Nobody who is not an admin may get any of this data.

The backend already offers all of it. Your work is the page.

## 2. Before you start

- **Branch.** This brief describes the branch `develop-261123` at commit `3a1edad`. Run
  `git branch --show-current` and `git log -1 --oneline` first. A newer commit, or a newer
  branch the user has put you on, is fine: where the code then differs from this brief, trust
  the code and mention it. Do not switch branches or stash on your own.
- **Changes that are already in the working tree belong to the user.** Leave them as they are
  and do not ask about them.
- **Do not commit or push** unless the user asks.
- **Scope.** Only this repository. Do not change the backend, the gateway, or anything about
  the login service. Do not change how login works in this app. Section 10 lists what is
  deliberately left out.
- **Baseline.** Before you change anything, run the four static checks of section 12 once and
  note what each one says. If one of them fails before your work, do not try to repair it:
  say so in your first message to the user, next to the designs.
- **Decisions already made.** These were settled with the user. Build on them, do not reopen
  them:
  1. The browser never calls the backend directly. It calls this app's own server
     (`/backend/...`), which passes the call on. This is how the app works today.
  2. The backend is what protects the data. The page only hides things from people who are not
     admins.
  3. Searching, filtering and cutting a list into pages are done by the backend. The page never
     loads everything and filters it in the browser.
  4. An admin sees who owns a chat, its title and its times. An admin does not open or read
     another person's conversation, and the backend has no address for it.
  5. "Waiting" means never approved. "Deactivated" means approved once and then taken away.
     The two are shown apart.
  6. On their own account, an admin is offered neither "Deactivate" nor "Remove admin".
  7. No new npm package, unless the user agrees to one when choosing the design.
  8. Nothing reloads by itself. No timers.

## 3. How you must work: design first, then build

### 3.1 Phase 1: show design ideas

Produce **three** design ideas for the admin area and let the user see them. The three must
differ in structure: how the admin moves around, and where the things about one person live.
Three colour variations of the same layout do not count.

Directions that are worth considering. You may replace any of them with a better idea:

- **Lists side by side.** One view per list (waiting, accounts, access log, sessions, admins),
  reached through tabs or a side menu. A person's access log is the general access log with
  that person preselected.
- **People first.** One list of people. Choosing a person opens that person's details beside
  or over the list: their state, the actions, their visits, their chats. The lists across
  everybody are secondary views.
- **Overview first.** A start view with the waiting people and a few key numbers on top, and
  the lists behind it.

What an admin actually does, most frequent first. Judge your ideas against this:

1. Approves a new person. This should take very few clicks from opening the admin area, and
   the number of waiting people should be visible at a glance.
2. Finds one person and looks at or changes their state.
3. Looks at what one person did: their visits and their chats.
4. Looks across everybody for a period: who visited last week, which chats were created today.
5. Rarely: makes or removes an admin.

What the data looks like:

- Accounts: tens today, a few hundred later.
- Access log: one row every time anybody opens the app. Thousands.
- Sessions: thousands.
- Text can be Korean. Department names can be long. A browser name ("user agent") is around
  120 characters.
- Admins work at a desktop screen.

**A design may only show what the backend can deliver** (section 7). There are no statistics
addresses. A count is available as the `total` of a list request with `limit=1`, for example
"how many are waiting" or "how many visits since midnight". Charts over time are out.

**How to show the ideas.** The user has to see rendered pictures, not descriptions.

- Write the mock-ups as self-contained HTML files in a new folder `dev/admin-design/`: one file
  per idea and an `index.html` that links them. The folder `dev/` already holds this
  repository's development tools and is left out of the Docker image.
- A file must open by double click, without a server and without the internet: no script,
  font, style or icon loaded from a network address. The company network blocks many of them.
  Inline CSS and inline SVG are fine. A system font instead of the app's font is acceptable in
  a mock-up.
- Use the app's real colours. Copy the values from `src/app/globals.css`: the light set under
  `:root` and the dark set under `[data-theme="dark"]`. Give each file a switch between light
  and dark. Match the look of the existing pieces in `src/components/ui/` and of the chat
  sidebar, so that the admin area reads as part of the same app.
- Use the same invented data in all three ideas, so they can be compared: around forty
  accounts with a believable mix (most active, some waiting, a few deactivated, two admins of
  whom one was never approved), Korean and English department names, long values, a chat
  without a title, a chat that is running. Invented people only, for example `gildong.hong`.
- If your environment can also show a rendered page or picture to the user directly, do that
  as well. Text sketches alone are not enough.

**Each idea must show:**

1. The accounts: search, the filters, and how status and admin are marked.
2. The waiting people and how one is approved.
3. The actions on one person, and what the question before an action looks like.
4. The access log with a person and a date range chosen.
5. The sessions with filters.
6. The admins, and how a login ID is made admin.

For the idea you recommend, also show once: what a list looks like while loading, when nothing
was found, and when loading failed; and the screen a person who is not an admin gets.

**With each idea, in your message to the user:**

- The idea in two or three sentences.
- What it is best at, and where it is weakest.
- How many clicks each of the five jobs above takes from opening the admin area.
- Which addresses the views would have (`/admin/...`).

Then say which idea you recommend and why, in a few sentences.

During phase 1 you create files only under `dev/admin-design/`. Nothing under `src/` changes.

### 3.2 The stop

End phase 1 by asking the user to choose: one of the three, or a mix ("the layout of B with
the waiting list of C"). Tell them the full path of `dev/admin-design/index.html`.

**Then stop and wait for the answer.** Do not begin phase 2 on your own, however obvious the
choice looks to you. If the user asks for changes to a design, change the mock-up and ask
again.

### 3.3 Phase 2: build what was chosen

When the user has chosen, restate the chosen design in a few lines, including the addresses of
its views, so that both of you mean the same thing. Then build it.

Sections 7 to 9 hold for any design. They are not up for redesign: they are what makes the
admin area correct, whichever way it looks.

At the end, remove `dev/admin-design/` unless the user wants to keep it. Ask in your final
report.

## 4. What exists today

| File | What it does now |
|---|---|
| `src/app/layout.tsx` | Wraps the whole app in `ThemeProvider`, `UserProvider` and `UserGate`. The title template is `%s - <app title>` |
| `src/components/user-gate.tsx` | Shows a view only to a person who is logged in and approved. In every other state it shows its own screen (checking, going to login, "Waiting for approval", and so on). Its `Screen` helper is a good model for a centred message |
| `src/providers/user-provider.tsx` | `useUser()` gives `status`, `user`, `userId`, `isAdmin`, `checkAgain`, `logout`. The values come from the backend's `/auth/me`, asked once per page load. Nothing is built on `isAdmin` yet |
| `src/lib/auth-client.ts` | `apiFetch(path, init)`: the one way the app calls its own server. It puts the base path in front, adds the login pass, renews the pass on a 401, and tells the provider about an ended login and about the refusals `account_inactive` and `user_mismatch` |
| `src/lib/base-path.ts` | `BASE_PATH`: empty in local development, `/data-agent` in the Docker build |
| `src/app/backend/[...path]/route.ts` | Server route. Passes any `/backend/<path>` on to the backend, for GET, POST, PUT, PATCH and DELETE, with the query string. It needs no change |
| `src/app/chat/new/page.tsx`, `src/app/chat/[sessionId]/page.tsx` | The two existing views. A server file that sets the tab title and renders the client component `ChatView` |
| `src/components/chat/session-sidebar.tsx` | The chat sidebar. At its bottom is the account row with a menu that has one entry, "Log out" (`handleLogout`) |
| `src/lib/session-api.ts`, `src/lib/types.ts` | How the existing backend calls and their types are written. A model for yours |
| `src/components/ui/` | button, card, dropdown-menu, input, scroll-area, sheet, switch, tooltip. There is no table, badge, select, tabs or dialog yet |
| `src/components/theme-toggle.tsx` | The light / dark / system switch shown in the chat header |
| `src/app/globals.css` | All colours, as CSS variables. The theme is the attribute `data-theme` on `<html>` |
| `dev/mock-login-service.mjs` | A stand-in for the login service, for local development |
| `STRUCTURE.md` | Describes the app, its addresses and how to run it locally |

Installed and usable without adding anything: `@radix-ui/react-dialog`,
`@radix-ui/react-dropdown-menu`, `@radix-ui/react-scroll-area`, `@radix-ui/react-switch`,
`@radix-ui/react-tooltip`, `lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`.

## 5. How the pieces talk

```
browser ── https://dice.gtrai.sec.samsung.net ──► gateway
    /auth/...            ──► DICE login service            (not this app)
    /data-agent/...      ──► this app's server, port 13080

this app's server ── BACKEND_ORIGIN ──► data agent backend
```

1. The person opens the app, is logged in through the company single sign-on and approved.
   All of that exists and stays as it is.
2. At the start the page asked the backend "who am I" (`/auth/me`). The answer says `is_admin`.
   This is `useUser().isAdmin`.
3. An admin view asks for its data with `apiFetch("/backend/admin/...")`. The browser sends that
   to this app's server, which passes it on to the backend as `/admin/...`, with the pass.
4. The backend checks the pass and looks the caller up in its list of admins, on every single
   request. An admin gets the data. Anyone else gets 403 with the code `admin_required`.

What follows from this:

- **Hiding is not protecting.** The code of the admin area can be downloaded by anyone who can
  open the app. That is fine, because it contains no data. Never put a decision about access
  into the page alone.
- **`isAdmin` can be out of date.** It is from the page load. An admin can be removed while
  their admin area is open. Their next request is then refused, and every view has to cope.
- **Two things look alike.** `/admin/users` is a view of this app. `/backend/admin/users` is
  the backend's data. Mixing them up is the most likely bug.

## 6. Words

| Word | Meaning |
|---|---|
| Account | One person the backend has seen. It appears the first time that person opens the app |
| Admin | A person in the backend's list of admins. An admin can always use the app, approved or not |
| Active | Approved by an admin |
| Waiting | Never approved |
| Deactivated | Was approved, and an admin took the approval away |
| Visit, access log | One entry each time a person opens the app: who, when, from which IP address, with which browser |
| Session | One chat |

## 7. The backend contract

Every address below is written as the backend knows it. From the browser each one is called as
`apiFetch("/backend" + address)`. All of them need the pass, which `apiFetch` adds, and all of
them are for admins only.

### 7.1 Rules for the three lists

**Pages.**

| Parameter | Meaning | Accounts, sessions | Access log |
|---|---|---|---|
| `limit` | Rows in one page | 1 to 200, default 50 | 1 to 1000, default 100 |
| `offset` | Rows skipped before the page | 0 or more, default 0 | the same |

Every list reply carries `total`: how many rows match the filters, whatever `limit` and `offset`
are. A page behind the end is an empty list with the true `total`.

**`search`** is a piece of text, at most 255 characters. A row matches when the text appears
anywhere in one of the fields that the list searches. Upper and lower case do not matter. `%`
and `_` are ordinary characters. Spaces around the text are ignored, and an empty `search` is
the same as none.

**`user_id`** on the access log and on the sessions means "this person and nobody else". Upper
and lower case do not matter. It exists next to `search` because login IDs contain each other:
a search for `j.kim` also finds `hj.kim`, and `user_id=j.kim` does not.

**Dates.** A date filter is a moment, written with a time zone: `2026-11-23T15:00:00.000Z` or
`2026-11-24T00:00:00+09:00`. `..._from` includes that moment. `..._to` excludes it. A value
without a time zone is refused.

**Several filters at once** all have to hold.

**Order** is newest first and cannot be chosen.

**Times in replies** are text like `2026-11-23T01:00:00Z`. `new Date(...)` reads them.

### 7.2 `GET /admin/users`

| Parameter | Value | Keeps accounts where |
|---|---|---|
| `search` | text | the text appears in `user_id`, `email`, `full_name`, `department` or `company` |
| `status` | `waiting`, `active` or `deactivated` | the account has that status |
| `is_admin` | `true` or `false` | the person is, or is not, an admin |
| `limit`, `offset` | see 7.1 | |

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

About the fields:

- `user_id` is the login ID, in lower case.
- `status` is about the approval only. Being an admin is separate. **An admin who was never
  approved has the status `waiting` and still has full access.** The first admin of the real
  system is exactly this case. So:
  - "The people who are waiting" is `status=waiting&is_admin=false`.
  - An admin whose status is not `active` needs a visible note such as "has access as admin",
    or people will wonder why a waiting person can use the app.
- `email`, `department`, `company`, `activated_at`, `activated_by`, `last_access_at` and
  `last_access_ip` can be `null`.
- `full_name` holds the email again. The login service sends no real name. Do not show it as a
  separate column.
- `activated_at` and `activated_by` say when and by whom the account was last approved. They
  stay filled after a deactivation.
- `created_at` is the person's first visit.
- `unique_name`, `sid` and `roles` are technical values from the company login. Show them, if
  at all, only in a details view.

### 7.3 `PATCH /admin/users/{user_id}?is_active=true`

Approves the account. With `is_active=false` it takes the approval away. The value travels in
the address, not in a body. The reply is the account, in the shape of one entry of 7.2.

- Approving sets `activated_at` and `activated_by` anew, also after a deactivation.
- Deactivating takes effect at that person's next request. If their app is open, it switches
  to "Waiting for approval" within seconds.
- A person who is an admin keeps their access when deactivated.
- 404 `user_not_found` when there is no account with that ID.

### 7.4 `GET /admin/access-log`

| Parameter | Value | Keeps visits where |
|---|---|---|
| `user_id` | a login ID | the visit is this person's |
| `search` | text | the text appears in the `user_id` or in the `ip_address` |
| `accessed_from` | a moment | the visit is at or after it |
| `accessed_to` | a moment | the visit is before it |
| `limit`, `offset` | see 7.1 | |

```json
{
  "access_logs": [
    {
      "user_id": "gildong.hong",
      "accessed_at": "2026-11-23T01:00:00Z",
      "ip_address": "10.254.163.69",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ..."
    }
  ],
  "total": 1
}
```

`ip_address` and `user_agent` can be `null`.

### 7.5 `GET /admin/sessions`

| Parameter | Value | Keeps chats where |
|---|---|---|
| `user_id` | a login ID | the chat is this person's |
| `search` | text | the text appears in the owner's `user_id`, in the title or in the session ID |
| `created_from`, `created_to` | moments | the chat was created in that range |
| `updated_from`, `updated_to` | moments | the last activity in the chat is in that range |
| `limit`, `offset` | see 7.1 | |

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

- `session_title` is `null` for a chat that has no title yet. Show the session ID then, as the
  chat sidebar does.
- `run_state` is `running` while the agent is answering in that chat, otherwise `idle`.
- `last_update_time` is the last activity in the chat.
- There are no messages in the reply, and there is no admin address that returns them. A row
  is not a link to the chat.
- Old chats can belong to login IDs that have no account. That is expected.

### 7.6 The admins

**`GET /admin/admins`** has no parameters and no pages. The list is short.

```json
{ "admins": [ { "user_id": "gildong.hong", "added_at": "2026-11-22T10:15:00Z", "added_by": "bootstrap" } ] }
```

`added_by` is the admin who added this one. The word `bootstrap` means the entry was put in by
hand, in the database. It can be `null`.

**`PUT /admin/admins/{user_id}`** makes that login ID an admin and replies with the entry, in
the shape above. Calling it for someone who already is an admin changes nothing and still
answers 200.

**`DELETE /admin/admins/{user_id}`** removes an admin. It answers 200 with the body `null`.

Behaviour to design for:

- Making someone an admin gives them full access at once, approved or not.
- Removing an admin who was never approved takes all their access away at once.
- The last admin cannot be removed: 409 `last_admin`.
- **A login ID can be made admin before that person has ever opened the app.** Such an admin
  has no account. They are in the list of admins and not in the list of accounts. This is why
  the admin area needs a place that lists the admins by themselves, and a way to type a login
  ID. Do not rely on the accounts list alone.
- The backend trims the login ID and turns it into lower case. It refuses an ID that is empty,
  longer than 255 characters, contains a space, `/` or `\`, or is one of the words `null`,
  `undefined`, `none`: 400 with `{"detail": "User id is invalid"}`.

### 7.7 Refusals

A refusal by the authorization layer always has the shape `{"detail": "...", "code": "..."}`.

| Status | `code` | When | What the page does |
|---|---|---|---|
| 401 | `invalid_token` | The pass is not accepted | Nothing for a read: `apiFetch` renews the pass and sends a read again by itself. For a change see 9 |
| 403 | `admin_required` | The caller is not an admin (any more) | Replace the whole admin area by "You are no longer an administrator", with a way back to the chat |
| 403 | `account_inactive`, `user_mismatch` | Not expected on admin addresses | Nothing. `apiFetch` tells the provider, which handles them |
| 404 | `user_not_found` | No account with that `user_id` | Show the message, then ask for the list again. Somebody else changed it meanwhile |
| 404 | `admin_not_found` | Removing an admin who is not one | The same |
| 409 | `last_admin` | Removing the only admin | "The last administrator cannot be removed." |
| 400 | none | The login ID in the address is not valid | Show "This is not a valid login ID." |
| 422 | none | A filter value is not valid | "This filter is not valid." **`detail` is a list here, not a text.** Do not print it |
| 500 | none | The backend failed. The body is `{"detail": "..."}` | "Could not load", with a way to try again |

This app's own server can also answer in plain text (`502 Backend unreachable`,
`500 BACKEND_ORIGIN is not configured`). Never assume that an error body is JSON.

### 7.8 What `/auth/me` gives you

Already called by the provider, once per page load. You do not call it. `useUser().user` holds:

```json
{ "user_id": "gildong.hong", "is_active": true, "is_admin": true,
  "email": "gildong.hong@samsung.com", "full_name": "gildong.hong@samsung.com",
  "department": "Some Department", "company": "Some Site", "created_at": "2026-11-22T10:00:00Z" }
```

## 8. Rules that hold for any design

### 8.1 Getting in

- **The entry.** In the account menu of the chat sidebar (`session-sidebar.tsx`), add an entry
  "Admin" above "Log out". It leads to `/admin`. Show it only when `useUser().isAdmin` is true.
  Close the mobile sheet the way `handleLogout` does.
- **The guard.** Everything under `/admin` sits behind one check: if `useUser().isAdmin` is
  false, show a short screen "This area is for administrators" with a way back to the chat,
  and nothing else. Do not redirect, and do not ask the backend for anything. The existing
  `UserGate` has already made sure that the person is logged in and approved.
- **The way out.** A visible way back to the chat (`/chat/new`) from every admin view.
- **The theme switch** is available in the admin area as it is in the chat.
- **Tab titles.** Each view sets a title, the way `src/app/chat/new/page.tsx` does.

### 8.2 The actions

Every action that changes something asks first. The question says what will happen, in the
person's terms:

| Action | Offered when | Request | The question has to say |
|---|---|---|---|
| Activate | Status is `waiting` or `deactivated` | `PATCH /admin/users/{id}?is_active=true` | The person will be able to use the app |
| Deactivate | Status is `active`, and it is not your own account | `PATCH /admin/users/{id}?is_active=false` | The person will be shut out at their next click. If they are an admin: as an admin they keep their access |
| Make admin | Not an admin | `PUT /admin/admins/{id}` | The person will be able to use the app and this admin area, and to approve and remove people, including you |
| Remove admin | Is an admin, and it is not your own account | `DELETE /admin/admins/{id}` | The person will lose the admin area. If their status is not `active`: they are not approved, so they will also lose the app |

- "Your own account" is the one whose `user_id` equals `useUser().userId`. Another admin can
  still deactivate or remove you. The page only stops a slip of your own hand.
- After an action: ask the backend for the current list again, and for the number of waiting
  people if you show it. Do not change the row by hand and hope that it matches.
- While a request is on its way, its button cannot be pressed a second time.
- "Activate" for a waiting person is the most frequent action. It may be a plain button with
  one confirming step. It must not be buried in a menu.

### 8.3 Lists and filters

- **The state of a view lives in its address:** the filters, the page number, and a chosen
  person. Three things depend on it. A reload keeps the view. About once an hour the login
  takes the browser through a full page reload and returns to the same address. And one view
  can link to another with a filter already set, for example from a person to their visits.
- **Pages of 50 rows,** with "1 to 50 of 132", "Previous" and "Next". Changing a filter goes
  back to the first page.
- **Typing.** Wait about 300 milliseconds after the last key before asking the backend.
- **Late answers.** Answers can arrive in another order than the questions were sent. Only the
  answer to the newest question may be shown.
- **Empty filters are left out of the request.**
- **Dates.** The admin picks days. "From 1 November to 23 November" means both days in full,
  in the admin's own time zone. Send the start of the first day as `..._from` and the start of
  the day after the last day as `..._to`:

  ```ts
  // A picked day ("2026-11-23"). Without a zone in the text, JavaScript reads it in the
  // admin's own time zone.
  const startOfDay = (day: string) => new Date(`${day}T00:00:00`).toISOString();

  const startOfNextDay = (day: string) => {
    const date = new Date(`${day}T00:00:00`);
    date.setDate(date.getDate() + 1);
    return date.toISOString();
  };
  ```

- **Times on screen** are in the admin's own time zone, as `2026-11-23 10:15`.
- **Every list has three more states:** loading, "nothing found", and "could not load" with a
  way to try again.
- **A "Refresh" control** on each list. Nothing reloads on a timer.
- **Long values** must not stretch the layout. Cut them and show the full text on hover.
- **Status is never shown by colour alone.** There is always a word.
- **One person exactly.** When a view is opened for one person, it sends `user_id`, shows that
  clearly ("Only gildong.hong"), and lets the admin remove it. A typed search sends `search`.
- **Keyboard.** Every action can be reached and triggered without a mouse.

### 8.4 One module for the calls

Put every call to `/backend/admin/...` and the types of the replies in one module, for example
`src/lib/admin-api.ts`, built on `apiFetch`. A sketch of the idea. Adapt it freely:

```ts
import { apiFetch } from "./auth-client";

export type UserStatus = "waiting" | "active" | "deactivated";

// One entry of GET /admin/users. Only the fields the page shows.
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
```

## 9. Things that are easy to get wrong

- **Page address and data address.** `/admin/users` is a view. `/backend/admin/users` is data.
- **Never ask for another person's chat.** A call to `/backend/apps/users/<someone else>/...`
  is answered with 403 `user_mismatch`. `apiFetch` reads that as "a different person has
  logged in" and reloads the page. The admin area uses `/backend/admin/...` and nothing else.
- **`useSearchParams()` needs `<Suspense>` around the component that calls it.** In
  development everything seems to work without it. The production build is where it shows.
  Run the build.
- **The base path.** `<Link>`, `router.push()`, `router.replace()` and `redirect()` get it by
  themselves, and `apiFetch` adds it to requests. The admin area should need no address that
  is written by hand. Do not add the base path a second time.
- **Do not call `/auth/me` to refresh `isAdmin`.** Each call is recorded as a visit, and would
  fill the very access log that this area shows. The value from the page load is good enough
  for showing the menu entry. The backend's answer is what counts.
- **A change is not sent twice.** After a 401 on PATCH, PUT or DELETE, `apiFetch` fetches a
  new pass and deliberately does not send the request again. Show "Could not save. Please try
  again." Do not add a retry of your own.
- **`DELETE` answers 200 with the body `null`.** That is success.
- **Dates are days in the admin's time zone, not in UTC.** A visit at 08:30 Korean time on
  23 November is 22 November in UTC. The two helpers in 8.3 put it on the right day.
- **The last day is included.** The request excludes `..._to`, so the page sends the start of
  the following day.
- **`+` in a time zone.** In an address a bare `+` means a space. `toISOString()` ends in `Z`
  and avoids the problem. Build every query string with `URLSearchParams`.
- **Encode the login ID** in an address with `encodeURIComponent`.
- **`user_id` and `search` are different filters.** Sending a person's ID as `search` also
  brings other people whose ID contains it.
- **The waiting count** is `total` of `status=waiting&is_admin=false&limit=1`. Without
  `is_admin=false` it counts admins who were never approved.
- **Hydration.** The provider is in `loading` on the server and at first in the browser. Do
  not read `isAdmin` in a way that renders differently on the two sides.
- **The chat must not be running underneath.** The chat polls the backend every few seconds.
  The admin views are their own pages, so `ChatView` is not mounted there. Keep it that way.

## 10. Not part of this task

- Reading, renaming or deleting another person's chat.
- Deleting an account. The backend has no address for it.
- Sorting by a column. Every list is newest first.
- Approving several people at once.
- Exporting a list to a file.
- Notifying anybody about waiting people.
- A record of what admins did.
- Charts and statistics.
- Changes to the login, to `apiFetch`'s behaviour, to the server routes under
  `src/app/backend/` and `src/app/api/`, to the backend, the gateway or the login service.
- Deployment. The user deploys.

Two things you may run into that are known and not yours to fix:

- `npm run lint` reports 5 errors and 8 warnings at commit `3a1edad`, all in the chat code
  (`chat-view.tsx`, `message-item.tsx`, `session-sidebar.tsx`, `theme-provider.tsx`). The rule
  for this work is "no new problem". Leave the existing ones, also in `session-sidebar.tsx`,
  where you add the menu entry.
- After a fresh company login, the DICE login service currently returns people to the DICE
  home page and not to the address they came from. A bookmarked admin address therefore needs
  a second try. This is a fault of that service.

## 11. Trying it locally

The backend with the admin addresses is not reachable from a development machine. To run the
admin area locally you need the stand-in login service that exists, and a stand-in backend that
you write.

- `STRUCTURE.md`, section "Running locally", describes `dev/mock-login-service.mjs` and the
  setting `AUTH_DEV_PROXY_TARGET`.
- Write a small, dependency-free Node script for the backend, for example
  `dev/fake-backend.mjs`, and point `BACKEND_ORIGIN` at it. It is a development tool. It must
  never be imported by the app. Whether you keep it is your call. If you keep it, describe it
  in `STRUCTURE.md`.

What the stand-in backend has to answer:

- `GET /auth/me`: the reply of 7.8. Make `is_admin` switchable by an environment variable, so
  that you can try the app as a person who is not an admin.
- `GET /apps/users/{id}/sessions`: `{"sessions": []}`, so that the chat does not show an error
  when you go back to it.
- Every address of section 7, on data held in memory. Start from the invented accounts of your
  mock-ups and add enough to have more than 50 accounts, more than 50 visits and more than 50
  chats, so that pages can be tried.

What it has to get right, because the page depends on it:

- `total` counts all matching rows, not the rows of the page.
- `search` and `user_id` behave differently (7.1). Have both `j.kim` and `hj.kim` in the data.
- `..._to` excludes its moment, and a date without a time zone is answered with 422 and a
  `detail` that is a list.
- The three statuses follow these rules: `active` when `is_active`. Otherwise `waiting` when
  `activated_at` is `null`, and `deactivated` when it is filled. Approving fills `activated_at`
  and `activated_by`. Deactivating leaves them.
- Have one admin who was never approved (`status` is `waiting`, `is_admin` is `true`).
- Have one admin who has no account at all.
- Removing the last admin answers 409 `last_admin`. Removing someone who is no admin answers
  404 `admin_not_found`. `PATCH` for an unknown ID answers 404 `user_not_found`.
- A switch that makes every admin address answer 403 `admin_required`, to try what happens
  when the admin right is taken away.
- A switch that slows the answers down, to see the loading state and to try late answers.

Log the `Authorization` header of each call once while you test, to confirm that the pass
arrives. Do not keep that logging.

## 12. Checking your work

Static checks:

```
npm run lint
npx tsc --noEmit
npm run build
NEXT_PUBLIC_BASE_PATH=/data-agent npm run build
```

`npm run lint` must report nothing that it did not report before your work (see 10). The other
three must pass.

On Windows, Git Bash can rewrite a value that starts with `/` into a Windows folder path before
Node sees it. If the base path comes out as something like `C:/Program Files/Git/data-agent`,
that is what happened. Set the variable in PowerShell, or in a local `.env.local` file, for
that build.

Then try each of these against the stand-ins, with and without the base path where it matters.
Word them for the design that was chosen:

1. A person who is not an admin: no "Admin" entry in the account menu. An admin address typed
   by hand shows "This area is for administrators", and no request to `/backend/admin/...` is
   made.
2. An admin: the entry is there, and every view loads.
3. A waiting person is visible as waiting. "Activate" lets them in, and the number of waiting
   people goes down.
4. Accounts: search, status and admin narrow the list, alone and together. The address changes
   with them, and a reload keeps them.
5. Deactivate an active person: their status becomes "Deactivated", not "Waiting". Activate
   them again.
6. Make a person admin and remove them again. Your own account offers neither "Deactivate" nor
   "Remove admin". Make a login ID admin that has no account, and remove it again.
7. From a person to their visits: only that person's visits, clearly marked as such. A date
   range narrows them, and both end days are included.
8. The same for sessions, plus a search for a title and the creation dates. A chat without a
   title shows its ID. A running chat is marked.
9. More than 50 rows: the next and the previous page work, and a new filter returns to the
   first page.
10. Type quickly in a search box with slow answers: the list ends on the result for the full
    text.
11. The admin right is taken away while the admin area is open: the next click shows "You are
    no longer an administrator".
12. Each refusal of 7.7 shows what the table says. A failed load can be tried again.
13. Light and dark both look right. A long department name and a long browser name do not
    break the layout. A narrow window stays usable.
14. Back to the chat: the chat works as before, and nothing in it changed.
15. With the base path: every admin address works under `/data-agent/admin/...`, also after a
    reload, and every request goes to `/data-agent/backend/admin/...`.

Verify as far as your tools allow. If you cannot drive a browser, check what you can (the
build, the calls with `curl` against your stand-in, the logic by reading it again) and say
plainly which of the fifteen you could not try.

What cannot be checked on a development machine at all: the real backend, the real login, and
the gateway. That has to wait for the deployment.

## 13. Your messages to the user

The user develops both repositories and is fluent in Python and TypeScript. Write in plain
words, define a term the first time you use it, and give one clear statement instead of a list
of options, except where this brief asks for options: the three designs.

**At the end of phase 1:** the three ideas as described in 3.1, your recommendation, the path
of `dev/admin-design/index.html`, anything the baseline checks showed, and the question which
design to build. Nothing else.

**At the end of phase 2:**

- What an admin now sees and can do, in a few sentences.
- The files you changed or added, each with one line on why.
- Which of the fifteen checks you ran, how, and what you saw. Which you could not run.
- Anything in this brief that did not match the code, and what you did about it.
- What the user has to do next: deploy the backend with the admin addresses first and this
  frontend second, then open the admin area through the DICE address as an admin and click
  through the checks of section 12 that could not be tried locally.
- Whether `dev/admin-design/` and the stand-in backend should be kept or removed.
- That nothing was committed, unless they asked you to.
