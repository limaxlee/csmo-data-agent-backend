# Data agent: recording the person's real IP address in the user access log

Written 2026-11-23. No secret values are written here.

## In short

- **Goal:** each row in the table `user_access_log` holds the address of the person's PC. Today
  it holds the address of the frontend container.
- **How:** one setting on the backend container, `FORWARDED_ALLOW_IPS`. It tells the backend's web
  server that the frontend may be believed about where a request came from.
- **What changes:** one line in the backend run script. No backend code, no frontend code, no
  database change, no change to the forwarding rule on DICE.
- **Deploying it:** restart the backend container. No image has to be built.

## Where things stand

| Piece | State |
|---|---|
| Columns `user_access_log.ip_address` and `user_accounts.last_access_ip` | Exist since the login work |
| Backend code that writes an address into them | Exists. It writes the sender of the connection |
| DICE gateway adds the person's address to the request | Yes. Seen on 2026-11-23 |
| Frontend passes that address on to the backend | Yes, in both of its forwarding routes |
| Backend believes the frontend about it | **No. This is the missing piece** |
| What the table holds today | `172.25.0.3`, the frontend container, for every visit through the page |

## Background: how the address travels

Three words used below:

- **Sender of the connection:** the machine that opened the network connection to the backend.
  Every web server knows this without being told.
- **`X-Forwarded-For`:** a line in the request in which a forwarding server writes the address it
  received the request from. Each forwarding server adds its entry at the end, after a comma.
- **uvicorn:** the web server program that runs the backend inside its container.

A request from the page passes two forwarding servers before it reaches the backend:

```
PC of the person                    10.254.163.69
  |
  v
DICE gateway                        adds  X-Forwarded-For: 10.254.163.69
  |
  v
frontend container, port 13080      passes the header on unchanged
  |
  v
backend container, port 18080       sender of the connection: 172.25.0.3 (the frontend container)
```

This was checked on 2026-11-23 with a trial log line on the server:

| Request | Sender of the connection | `X-Forwarded-For` |
|---|---|---|
| Through the page | `172.25.0.3` | `10.254.163.69` |
| Straight to `http://10.240.35.180:18080` from the same PC | `10.254.163.69` | none |

So the PC's address does arrive at the backend. It arrives in the header, not as the sender.

## Why the table has the wrong address today

The address for a row comes from `get_client_ip` in `data_agent/routers/dependencies.py`
(line 22). It returns the sender of the connection. For every request through the page that is
the frontend container.

---

## Part 1: The implementation

### 1.1 One setting on the backend container

Add this option to the `docker run` line that starts the backend:

```
-e FORWARDED_ALLOW_IPS=172.25.0.0/16
```

The value is the address range of the Docker network `da_backend`, the network that the frontend
and the backend containers share. `172.25.0.0/16` means "every address that starts with
`172.25.`". The real range has to be read from the server (step D1), because Docker chose it when
the network was created.

The run script in this repo is `run_data_agent_backend.sh`. Its first line becomes:

```bash
docker run --name da_backend -d --rm --network da_backend -p 18080:18080 -e FORWARDED_ALLOW_IPS=172.25.0.0/16 -v /home/cosmo/projects/da-backend/logs:/home/work/cosmo-da-backend/logs da-backend:0.0.1
```

On the server the script lies beside the backend repo folder and is called `run_da_backend.sh`.
Change both, so that the copy in the repo and the one on the server stay the same.

**What uvicorn does with the setting.** uvicorn reads `FORWARDED_ALLOW_IPS` by itself when it
starts. `data_agent/__main__.py` needs no change. The rule it then applies to every request:

1. If the sender of the connection is inside the trusted range, read `X-Forwarded-For` from the
   right, skip entries that are themselves inside the trusted range, and take the first one that
   is not. That address replaces the sender for the rest of the backend.
2. If the sender is not inside the trusted range, ignore the header.

Without the setting uvicorn trusts only `127.0.0.1`, which is why the header is ignored today.

The result, tested with uvicorn 0.52.3 (the version pinned in the requirements files) and the
addresses from the check above:

| Request | Sender of the connection | `X-Forwarded-For` | Address the backend uses |
|---|---|---|---|
| Through the page | `172.25.0.3` | `10.254.163.69` | `10.254.163.69` |
| Through the page, and the caller sent a header of their own | `172.25.0.3` | `1.2.3.4, 10.254.163.69` | `10.254.163.69` |
| Straight to port 18080 | `10.254.163.69` | none | `10.254.163.69` |
| Straight to port 18080 with a made-up header | `10.254.163.69` | `1.2.3.4` | `10.254.163.69` |
| Through the page, header missing | `172.25.0.3` | none | `172.25.0.3` |

**Why a setting and not code of our own that reads the header.** Reading the header correctly
needs two decisions, and both are easy to get wrong:

- *Which entry.* The gateway adds its entry at the end. Everything before it was sent by the
  caller, and a caller can type anything there. So the last entry is the one to believe, not the
  first.
- *Whom to believe.* Port 18080 can also be called directly from a PC. A direct caller can send
  any header, so the header may only be believed when the request comes from the frontend.

uvicorn makes both decisions as described above. It also corrects the sender in one place, so
every part of the backend that asks for it gets the person's address, without any of them
reading a header.

**Why in the run script.** The value is a fact about the Docker network on that server. The run
script is the place that already names that network (`--network da_backend`). The `Dockerfile`
and `config.yaml` describe the backend itself, which does not change.

### 1.2 Backend code: nothing changes

This is the path an address takes into the table. All of it exists.

| Step | Where |
|---|---|
| Read the address of the request | `get_client_ip`, `data_agent/routers/dependencies.py` line 22 |
| Hand it on when the page asks "who am I" (`/auth/me`) | `data_agent/routers/auth.py` line 25 |
| Hand it on for every other protected address | `require_active_user`, `data_agent/routers/dependencies.py` line 59 |
| Decide whether to write a row | `get_current_user` and `authorize`, `data_agent/services/user_manager.py` |
| Write it | `record_access`, `data_agent/infra/user_repository.py` |

`record_access` writes the address into two columns with one statement:
`user_access_log.ip_address` (one new row per visit) and `user_accounts.last_access_ip` (the
latest address of that person).

When a row is written:

- Every time the page asks `/auth/me`, which it does at least each time it is opened.
- On the very first request of a person the backend has never seen, whatever address they call.

Do not add code that reads `X-Forwarded-For` or `X-Envoy-External-Address` anywhere in the
backend. With the setting in place `request.client.host` is already the person's address.

**The trial code in the middleware.** On 2026-11-23 a trial version of
`data_agent/middleware/logging.py` on the server printed the address and the two headers into the
log file. Its only purpose was to see what arrives. It is not part of this work. Put the file
back to the version in this repo, which has no address code, at the next build. The table does
not depend on it.

### 1.3 One test to add

The setting lives outside the code, so nothing in the test suite notices if a later version of
uvicorn treats the header differently. This test does. Add it to
`tests/routers/test_dependencies.py`, inside `class TestDependencies`, below
`test_get_client_ip`.

Two imports at the top of the file. `Request` joins the existing `fastapi` line:

```python
from fastapi import Depends, FastAPI, Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
```

The test:

```python
    def test_get_client_ip_behind_frontend(self):
        app = FastAPI()

        @app.get("/ip")
        async def ip(request: Request):
            return {"ip": get_client_ip(request)}

        # uvicorn wraps the app in this middleware when FORWARDED_ALLOW_IPS is set
        trusted_app = ProxyHeadersMiddleware(app, trusted_hosts="172.25.0.0/16")
        frontend = TestClient(trusted_app, client=("172.25.0.3", 50000))
        direct = TestClient(trusted_app, client=("10.0.0.9", 50000))

        # Through the frontend: the address the gateway wrote, which is the last one
        assert frontend.get("/ip", headers={"X-Forwarded-For": "10.0.0.1"}).json() == {"ip": "10.0.0.1"}
        assert frontend.get("/ip", headers={"X-Forwarded-For": "1.2.3.4, 10.0.0.1"}).json() == {"ip": "10.0.0.1"}
        assert frontend.get("/ip").json() == {"ip": "172.25.0.3"}

        # Straight to the backend: the header is not believed
        assert direct.get("/ip", headers={"X-Forwarded-For": "1.2.3.4"}).json() == {"ip": "10.0.0.9"}
        assert direct.get("/ip").json() == {"ip": "10.0.0.9"}
```

It passes against the current code. The existing tests stay as they are.

### 1.4 Frontend and gateway: nothing changes

- **Frontend.** Both forwarding routes already pass `x-forwarded-for` on unchanged:
  `src/app/backend/[...path]/route.ts` (lines 39 to 45) and `src/app/api/chat/route.ts`
  (line 68) in the frontend repo. Keep it that way. The frontend must not add an entry of its own
  and must not replace the header.
- **Gateway.** `deploy/prod/routing.yaml` stays as it is. The gateway adds the header by itself.

---

## Part 2: Deployment

### What is deployed

| Piece | Deployed? |
|---|---|
| Backend run script on the server | Yes: one option added |
| Backend container | Yes: restarted, same image |
| Backend image | No build needed |
| Frontend, database, forwarding rule on DICE | No |

The restart interrupts the backend for a few seconds. A question that is being answered at that
moment is cut off, and the person has to ask it again.

Follow the steps from top to bottom on the server `10.240.35.180`. Every step says what you
should see.

### D1. Read the address range of the Docker network

```bash
sudo docker network inspect da_backend --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

**You should see:** one range, most likely `172.25.0.0/16`. It must contain `172.25.0.3`, the
address the frontend container had in the check. Use the range this command prints in D2,
whatever it is.

### D2. Add the option to the run script

Open `run_da_backend.sh` and add `-e FORWARDED_ALLOW_IPS=<the range from D1>` to the `docker run`
line of `da_backend`, anywhere before the image name `da-backend:0.0.1`. Section 1.1 shows the
finished line.

### D3. Restart the backend

```bash
sudo docker stop da_backend
sudo bash ./run_da_backend.sh
sudo docker ps --filter name=da_backend
sudo docker exec da_backend printenv FORWARDED_ALLOW_IPS
```

**You should see:** `da_backend` listed as "Up", then the range from D1.

### D4. Check the table

From your PC, open `https://dice.gtrai.sec.samsung.net/data-agent`, or reload it. That writes a
row. Then on the server:

```bash
sudo docker exec da_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; print(asyncio.run(PostgreSQLClient().fetch_all('SELECT user_id, accessed_at, ip_address FROM user_access_log ORDER BY id DESC LIMIT 5')))"
```

**You should see:** the newest row first, with your login ID and the address of your PC. Your PC
shows its address with `ipconfig`, under "IPv4 Address". Rows from before the restart still say
`172.25.0.3`.

A second sign is in the backend log. The line uvicorn writes for the request now starts with
your address followed by `:0`, for example `10.254.163.69:0 - "GET /auth/me HTTP/1.1" 200`.
Before, it started with `172.25.0.3`.

The same can be read from the page, with the `api` helper from
`data-agent-auth-deploy-and-test-2026-11-22.md`, section "Approving people":

| To see | Type |
|---|---|
| The last visits of a person | `await api("/admin/users/their.loginid/access-log?limit=5")` |
| The latest address of every person (`last_access_ip`) | `await api("/admin/users")` |

### D5. Check that a made-up address is not believed

This is the one thing that has not been seen on this gateway yet: that it puts its own entry
after a header the caller sent. On the data agent page, press F12, open the "Console" tab and
paste:

```js
const pass = (await (await fetch("/auth/token")).json()).accessToken;
await fetch("/data-agent/backend/auth/me", { headers: { Authorization: "Bearer " + pass, "X-Forwarded-For": "1.2.3.4" } });
```

Then run the command from D4 again.

**You should see:** the newest row has your real address.

If it says `1.2.3.4`, the gateway passes a caller's header on without adding its own entry. Then
anybody can choose the address that gets recorded, and the gateway has to be looked at before the
column can be relied on. Stop there and report it.

### With the next build

These two need the image to be built, and can wait for the next time you build it anyway:

- Put `data_agent/middleware/logging.py` back to the version in this repo (section 1.2).
- Commit the changed run script and the test from section 1.3.

---

## What the recorded address is, and its limits

- **It is the address the DICE gateway received the request from.** For a PC on the company
  network that is the PC. If a person comes in through a VPN or another forwarding device, it is
  that device's address.
- **Old rows stay wrong.** Rows written before the restart say `172.25.0.3`. The real address was
  never stored for them, so they cannot be repaired. They are easy to tell apart.
- **Calls made on the server itself** (`curl http://localhost:18080/...`) are recorded with an
  address of Docker's own, not `127.0.0.1`. This is how Docker hands such connections to a
  container. Expected, not checked on this server.
- **One way to fake the address remains.** A person with a valid pass can call the frontend
  directly at `http://10.240.35.180:13080`, around the gateway, and send a header of their own.
  The frontend server keeps a header that the caller sent, so the made-up address is recorded.
  The login ID in the row is still the true one. Closing this means letting only the DICE cluster
  reach port 13080, which is a firewall matter and not part of this work.

## If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| New rows still say `172.25.0.3` | The setting is not inside the container, or the range does not contain that address | Run the last command of D3. No output: the option is not on the `docker run` line that was used. Wrong range: repeat D1 |
| New rows show another address starting with `172.` or `192.168.` | The frontend reaches the backend from an address outside the trusted range. This happens when the Docker network was created anew, or the frontend no longer joins it | Repeat D1 to D3 |
| New rows have no address at all | The request arrived without a sender. Not expected with this setup | Report it, with the log line of that request |
| `printenv` prints the range, but D4 still shows `172.25.0.3` | The row you are looking at was written before the restart | Reload the page and run D4 again |
| A message that the name `milvus_mcp_server` is already in use, in D3 | The run script also starts that container, and it was still running | Nothing. Only `da_backend` was stopped |
| The newest row says `1.2.3.4` after D5 | See D5 | Stop and report it |
| The address is right now, and wrong again weeks later | The server or Docker was set up again and the network got another range | Repeat D1 to D3 |

## Going back

Remove the option from the run script and restart the backend as in D3. The backend then records
the frontend container's address again, as before. Rows that were already written stay as they
are.
