# `new_session` flag on the run endpoint

**Audience:** frontend developers
**Endpoint affected:** `POST /apps/users/{user_id}/sessions/{session_id}/run`

> `/run` is now an asynchronous job: it returns `202 {run_id, status}` and the answer arrives on
> `GET /apps/runs/{run_id}/events`. The `new_session` flag itself is unchanged, but *when* the title
> is readable is — see "Reading the title back" below, and `docs/migration.md` for the full contract.

## TL;DR

The backend no longer figures out on its own when a session needs a title. **The client now
has to say so.** Send `new_session=true` on the *first* `run` call of a brand-new session, and
leave it off for every call after that.

If you never send it, sessions will simply never get titles.

## What changed

Previously the backend inspected the session state after each run and generated a title if one
was missing. That check has been removed. Title generation is now driven entirely by the
`new_session` field on the run request.

| | Before | Now |
|---|---|---|
| Who decides a title is needed | backend (auto-detect) | **client** (`new_session`) |
| Message used for the title | last user message found in session history | the `query` you just sent |
| Runs per session that generate a title | first one only | every one where you pass `new_session=true` |

## The field

`new_session` — boolean, **optional, defaults to `false`**.

It is sent as a **query parameter**, next to `query`. It is *not* part of a JSON body — this
endpoint takes its text fields on the query string, and its body is reserved for the optional
`image_file` multipart upload.

Accepted truthy values: `true`, `True`, `1`, `on`, `yes`. Falsy: `false`, `0`, `off`, `no`.
Omitting the parameter is the same as `false`.

## When to send `true`

Exactly once per session, on the first `run` after you created it:

1. `POST /apps/users/{user_id}/sessions` → returns `{ "session_id": "..." }`
2. `POST /apps/users/{user_id}/sessions/{session_id}/run?query=...&new_session=true` ← **first message only**
3. every later message in that same session → `new_session=false`, or just omit it

> **Do not send `true` on every request.** Each `true` regenerates the title from that
> request's `query` and overwrites the existing one, and it costs an extra model call. A user
> who has already renamed the conversation by hand would see their name replaced.

## Examples

Text-only first message:

```
POST /apps/users/u-123/sessions/9f2c.../run?query=How%20many%20orders%20last%20month%3F&new_session=true
```

Follow-up message in the same session:

```
POST /apps/users/u-123/sessions/9f2c.../run?query=Break%20that%20down%20by%20region
```

With an image attached (query string still carries the text fields, body carries the file):

```
POST /apps/users/u-123/sessions/9f2c.../run?query=What%20is%20in%20this%20chart%3F&new_session=true
Content-Type: multipart/form-data; boundary=...

--...
Content-Disposition: form-data; name="image_file"; filename="chart.png"
Content-Type: image/png
...binary...
```

`fetch`:

```js
const params = new URLSearchParams({ query, new_session: String(isFirstMessage) });
const url = `/apps/users/${userId}/sessions/${sessionId}/run?${params}`;

const body = new FormData();
if (imageFile) body.append("image_file", imageFile);

const { run_id } = await fetch(url, { method: "POST", body: imageFile ? body : undefined })
  .then(r => r.json());
```

`run_id` is the handle to the answer, not the answer — open the run's event stream with it.

## Reading the title back

The submit response does **not** include the title:

```json
{ "run_id": "3f1c...", "status": "queued" }
```

The generated title is written into session state under the key `session_title`. Read it from
either session endpoint:

- `GET /apps/users/{user_id}/sessions` → `sessions[].state.session_title`
- `GET /apps/users/{user_id}/sessions/{session_id}` → `state.session_title`

**Timing changed when `/run` became a job** (see `docs/migration.md`). `POST .../run` now returns
`202` before the agent has even started, so the title is *not* there when submit resolves. It is
created inside the job, **before** the run's terminal `done` event — so refetching the session list
when you see the `title` or `done` event on the run's SSE stream is safe. Do not refetch on submit.

Note that `session_title` is absent from `state` for sessions that never had a title created,
so read it defensively and fall back to your own placeholder.

## Failure behaviour

Title generation cannot break a run. If it fails, the error is logged server-side and the run
still reaches `succeeded` with the agent's answer; no `title` event is emitted. The practical
consequence is that a session can occasionally end up without a title even though you sent
`new_session=true` — your UI should tolerate a missing `session_title` rather than assume it
appears.

Title creation also runs when the agent call itself failed. In that case the run ends as `failed`,
but the session may still have been titled.

## Related endpoints (unchanged)

These still work exactly as before and are the escape hatches if you need explicit control:

- `POST /apps/users/{user_id}/sessions/{session_id}/title` — generate a title on demand. Uses
  the last user message in the session, so the session must already have at least one message.
  Returns `{ "session_title": "..." }`.
- `PATCH /apps/users/{user_id}/sessions/{session_id}/title` — set the title manually, e.g. for
  a user-driven rename. Takes `session_title` as a query parameter.
