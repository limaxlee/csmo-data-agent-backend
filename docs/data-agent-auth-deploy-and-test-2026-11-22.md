# Data agent login: deploying it and testing it on production DICE

Written 2026-11-22. Follow it from top to bottom. Every step says what you should see. If you see
something else, stop and look at [If something goes wrong](#if-something-goes-wrong).

No secret values are written here.

## Where things stand

| Piece | State |
|---|---|
| Backend code | Done. In the backend repo, branch `develop-261121`, not committed |
| Frontend code | Done. In the frontend repo, branch `develop-261121`, not committed. It passed its twelve checks against a stand-in login service and a fake backend |
| Do the two fit together? | Checked by reading both on 2026-11-22: the addresses, the reply fields and the error codes the frontend uses are the ones the backend has |
| Server `10.240.35.180` | Still runs the old backend and the old frontend |
| Forwarding rule on DICE | Still the first one (`data-agent-stage`), which has to be replaced |

What has never been tried, and what this document is for:

- Samsung SSO sending a person back to the data agent address.
- The new backend accepting a real pass from DICE.
- The gateway, the frontend server and the backend working in a row.
- A long question getting through the gateway.

## What changes for the people who use the data agent

- The address becomes `https://dice.gtrai.sec.samsung.net/data-agent`. Opening it by IP address
  (`http://10.240.35.180:13080`) no longer works, because the login only exists on the DICE
  address.
- Nobody types an ID any more. Samsung SSO says who they are.
- Everyone except admins sees "Waiting for approval" on their first visit, until you approve
  them ([Approving people](#approving-people)).
- Old chats stay visible only to a person whose SSO login ID, in lower case, is the ID they
  used to type.

From step B1 on, the app is interrupted for anyone using it by IP address. Part A causes no
interruption, so do all of it first.

---

## Part A: prepare (nobody is interrupted)

### A1. Three things before you commit

1. **The icon file.** The frontend imports `src/app/dice_icon.png`, and that file was never added
   to git on any branch. It only exists on the machine where the frontend was built before.
   Find it there and commit it. Without it the frontend image cannot be built.
2. **The secret in the backend repo's `config.yaml`.** That file currently has the real signing
   secret typed in. Empty it again before committing (`service_jwt_secret: ""`), because this
   repo is pushed to github.com. The secret belongs in the `config.yaml` on the server (A2).
3. **Commit and push both repos** the way you normally do, so the server can get the code.

### A2. Put the secret in the server's `config.yaml`

On the server, open the `config.yaml` that lies beside the backend repo folder (the one that
already holds the storage and model keys, and gets copied into the image). Add:

```yaml
auth:
  service_jwt_secret: "<the plain secret>"
  service_jwt_issuer: web-auth
  service_jwt_audience: dice-backend
```

The plain secret is the short phrase of 22 characters (`DEPLOY.md`, section "2f. dice-runtime",
key `service-jwt`). It is not the text that ends in `==`.

### A3. Replace the forwarding rule

In the Kubernetes web page, namespace `dice`:

1. Delete the `VirtualService` named `data-agent-stage`.
2. Delete the `ServiceEntry` named `data-agent-server`.
3. Create the two objects from `deploy/prod/routing.yaml`: copy the whole file into the "create
   from YAML" box. If the page refuses two objects at once, paste the part above the `---`
   line first, then the part below it.

**You should see:** `https://dice.gtrai.sec.samsung.net/data-agent/` changes its address to
`/data-agent` and shows a blank or broken page. That is correct at this point, because the old
frontend is still running. What matters: no error 503, and no message about too many redirects.

If the web page refuses the file and names `headers`: delete the four lines from `headers:` to
`- cookie` in the file and create it again.

### A4. Get the code onto the server and build both images

The old containers keep running while you build. The two `docker tag` lines keep a copy of the
old images, so you can go back ([Going back](#going-back)).

Backend. Run this in the folder that holds `Dockerfile`, `config.yaml` and the
`cosmo-data-agent-backend` folder:

```bash
(cd cosmo-data-agent-backend && git pull)
sudo docker tag da-backend:0.0.1 da-backend:before-auth
sudo docker build -t da-backend:0.0.1 .
```

Frontend. Run this inside the `cosmo-data-agent-frontend` folder:

```bash
git pull
ls src/app/dice_icon.png          # must list the file (A1)
sudo docker tag da-frontend:0.0.1 da-frontend:before-auth
sudo docker build -t da-frontend:0.0.1 .
```

**You should see:** both builds finish without an error. The backend build installs one new
package, `PyJWT`.

Run the two `docker tag` lines only this one time. If you have to build again later, leave them
out. Running them a second time would replace the saved old image with the new one, and there
would be nothing left to go back to.

### A5. Check the settings inside the new backend image

```bash
sudo docker run --rm da-backend:0.0.1 python -c "from common.config import SETTINGS; a = SETTINGS.auth; print('auth ok', a.service_jwt_issuer, a.service_jwt_audience, 'secret length', len(a.service_jwt_secret))"
```

**You should see:** `auth ok web-auth dice-backend secret length 22`

- A long error that mentions `auth`: the section from A2 is missing or empty in the server's
  `config.yaml`. Fix it and build the backend again.
- `secret length 32`: the base64 text was pasted instead of the plain secret. Fix it and build
  again.

This prints only the length, never the secret.

---

## Part B: the switch (people are interrupted from here)

### B1. Start the new backend

```bash
sudo docker stop da_backend
sudo bash ./run_da_backend.sh
sudo docker ps --filter name=da_backend
sudo docker logs da_backend 2>&1 | grep "User tables are ready"
```

**You should see:** `da_backend` listed as "Up", and the line
`User tables are ready: user_accounts, user_access_log, user_admins`.

If `da_backend` is not listed, it stopped right after starting, and because of `--rm` its
messages are gone. Start it once in the foreground to read them:
`sudo docker run --rm --network da_backend da-backend:0.0.1`

### B2. Make yourself the first admin

Put your login ID in place of `your.loginid`, in lower case, exactly as `sub` shows it in a pass:

```bash
sudo docker exec da_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; asyncio.run(PostgreSQLClient().execute(\"INSERT INTO user_admins (user_id, added_by) VALUES ('your.loginid', 'bootstrap') ON CONFLICT (user_id) DO NOTHING\"))"
```

Then look at the result:

```bash
sudo docker exec da_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; print(asyncio.run(PostgreSQLClient().fetch_all('SELECT user_id, added_by FROM user_admins')))"
```

**You should see:** `[{'user_id': 'your.loginid', 'added_by': 'bootstrap'}]`. A warning line that
contains `EXPERIMENTAL` may appear before it. Ignore it.

This runs the SQL through the backend's own database settings, so it cannot land in the wrong
database. Running it twice does no harm. If you prefer your own SQL tool, the statement is the
part between the escaped quotes.

### B3. Three checks on the backend alone

On the server:

```bash
curl -s http://localhost:18080/health
curl -s -i http://localhost:18080/apps/users/x/sessions | head -1
```

**You should see:** the health reply with three times `healthy`, then `HTTP/1.1 401 Unauthorized`.
The second line proves the backend is no longer open.

Now the first real proof. In a browser where you are logged in to DICE, open
`https://dice.gtrai.sec.samsung.net/auth/token` and copy the long value of `accessToken`. On the
server:

```bash
curl -s -H "Authorization: Bearer PASTE_THE_PASS" http://localhost:18080/auth/me
```

**You should see:** your account, with your login ID, `"is_active":true` and `"is_admin":true`.
This means the production secret, a real pass and the new backend agree.

- `{"detail":"Invalid service token","code":"invalid_token"}`: the secret in the server's
  `config.yaml` is not the one DICE signs with, or the pass is more than an hour old. Get a
  fresh pass and try once more before changing anything.
- `"is_admin":false`: the ID in B2 is not spelled like `user_id` in this reply.

A pass works as your login for up to an hour. Do not paste it anywhere else.

### B4. Start the new frontend

Inside the `cosmo-data-agent-frontend` folder:

```bash
sudo docker stop da_frontend
sudo bash ./run_da_frontend.sh
```

**You should see**, from your PC:

- `http://10.240.35.180:13080/data-agent/backend/health` shows the same health reply. The
  frontend server reaches the backend.
- `http://10.240.35.180:13080/data-agent` shows a tidy screen titled "Could not check your
  login". That is correct by IP address: the login service does not exist there. It proves the
  new frontend is running under `/data-agent`.

---

## Part C: test with the real DICE login

Use a private browser window for C2, so you start logged out.

| # | Do this | You should see |
|---|---|---|
| C1 | Open `https://dice.gtrai.sec.samsung.net/data-agent/backend/health` | The health reply. Gateway, frontend server and backend work in a row |
| C2 | Open `https://dice.gtrai.sec.samsung.net/data-agent` | Samsung SSO, or a silent login. Then the address `/data-agent/chat/new` and the app. No "Waiting for approval", because you are an admin |
| C3 | Run `await api("/admin/users")` (see [Approving people](#approving-people)) | Your row, with your email, department and company filled in |
| C4 | Ask a short question. Ask one with an image. Reload the page | Answers arrive. The image shows again after the reload |
| C5 | Ask the longest realistic question you have | The answer arrives, however long it takes. This is the check on the gateway that was never run |
| C6 | Ask a colleague to open the address | They see "Waiting for approval" with their login ID |
| C7 | Approve them, and let them press "Check again" | They are in |
| C8 | Run `await api("/apps/users/someone.else/sessions")` | `{detail: "This address belongs to another user", code: "user_mismatch"}`. Nobody can read another person's chats |
| C9 | From any PC: `curl.exe -s -i http://10.240.35.180:18080/logs` | First line `HTTP/1.1 401 Unauthorized` |
| C10 | Take the colleague's approval away while their page is open | Within a few seconds their page shows "Waiting for approval" |
| C11 | Leave the page open for more than an hour, then use it | It reloads once by itself and carries on in the same chat |
| C12 | Press "Log out" in the account menu. Then open the data agent address again in the same tab | You land on a DICE page. Back on the data agent you see either "You are not logged in" with a "Log in" button, or the app itself. The second happens when DICE logged you straight back in, which the company SSO often does silently. Both are correct. What must not happen is the page jumping to SSO again and again |

When C1 to C8 pass, tell people the new address.

## Approving people

There is no admin page yet. Until there is, use the browser's developer tools on the data agent
page while you are logged in as an admin.

Press F12, open the "Console" tab, and paste this once. Chrome asks you to type `allow pasting`
the first time.

```js
const api = async (path, method = "GET") => {
  const pass = (await (await fetch("/auth/token")).json()).accessToken;
  const res = await fetch("/data-agent/backend" + path, { method, headers: { Authorization: "Bearer " + pass } });
  return res.json();
};
```

Then:

| To do this | Type this |
|---|---|
| See who is waiting | `await api("/admin/users?is_active=false")` |
| Approve a person | `await api("/admin/users/their.loginid?is_active=true", "PATCH")` |
| Take the approval away | `await api("/admin/users/their.loginid?is_active=false", "PATCH")` |
| See everyone | `await api("/admin/users")` |
| See a person's visits | `await api("/admin/users/their.loginid/access-log")` |
| See the admins | `await api("/admin/admins")` |
| Make someone an admin | `await api("/admin/admins/their.loginid", "PUT")` |
| Remove an admin | `await api("/admin/admins/their.loginid", "DELETE")` |

A person appears in the waiting list only after they have opened the data agent once.

An admin always has access. A person who was made admin without being approved loses access
when you remove them from the admins, so approve them as well if they should stay.

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| Browser message about too many redirects on `/data-agent` | The old rule `data-agent-stage` still exists | Delete it (A3) |
| Error 503 on the DICE address | The gateway cannot reach port 13080 on the server | Check that `da_frontend` is running. If it is, check the `ServiceEntry` from A3 |
| A page without styles, or a blank page, at C2 | The frontend image was built without the base path, or the old image is running | Build again with a plain `docker build` (A4) and restart (B4) |
| "Could not check your login" on the DICE address | The page reached the login service, but the backend did not answer `/auth/me` properly | Open C1. No health reply: the frontend server cannot reach the backend, check `BACKEND_ORIGIN` in the frontend run script and that `da_backend` is running. Health reply fine: the old backend is still running (B1), or look at `sudo docker logs da_backend` |
| After SSO you end on "You are not logged in", and "Log in" brings you back to the same screen | Either the login did not stick, or the backend refuses the pass | Open `https://dice.gtrai.sec.samsung.net/auth/session`. `"authenticated": true` means the backend refuses the pass: the secret is wrong, repeat B3. `false` means the login itself failed, which is a DICE matter and not a data agent one |
| "Waiting for approval" for yourself | You are not in `user_admins` under the ID the backend sees | Compare the ID on that screen with the one from B2, and run B2 again with the right spelling |
| After SSO you land on the DICE home page | The address you opened was not on `dice.gtrai.sec.samsung.net` | Open the address from C2 exactly |
| A question fails after a fixed time, for example always at 5 minutes | Something on the way cuts long requests | Note the time and tell me. This is the one open point about the gateway |
| The backend log shows `Rejected service token: InvalidSignatureError` | The pass was signed with a different secret | Same as the row about "You are not logged in" |
| The backend build (A4) stops at `PyJWT==2.15.1` | The server's package source does not offer that version | Tell me which versions it offers. Any 2.x from 2.10 on will do |
| The backend log shows `InsecureKeyLengthWarning` once | The production secret is short. Known, see the plan document, Part 6 item 1 | Nothing now |

## Going back

If the test fails and people need the app back before you can fix it:

```bash
sudo docker stop da_frontend da_backend
sudo docker tag da-backend:before-auth da-backend:0.0.1
sudo docker tag da-frontend:before-auth da-frontend:0.0.1
sudo bash ./run_da_backend.sh        # in the backend folder
sudo bash ./run_da_frontend.sh       # in the frontend folder
```

The app then works by IP address as before. Two things to know:

- The backend is open to everyone again, as it was.
- The three new tables stay in the database and disturb nothing. The new forwarding rule can
  stay too.

## After it works

- Tell people the new address, and approve them as they arrive.
- The risks in the plan document (`data-agent-auth-implementation-2026-11-21.md`, Part 6) are
  still open. The first one, the guessable production signing secret, matters more now that the
  data agent trusts it.
