# Data agent: deploying it on the cluster with Argo CD

Written 2026-11-26. Stage first, then production.

No secret values are written here. Where a key or password is needed, the text says where to
copy it from.

## Contents

- [The short version](#the-short-version)
- [How the pieces work together](#how-the-pieces-work-together)
- [Words used](#words-used)
- [How the defect agent is deployed, and what the data agent copies](#how-the-defect-agent-is-deployed-and-what-the-data-agent-copies)
- [What you have today and what you will have](#what-you-have-today-and-what-you-will-have)
- [All names in one place](#all-names-in-one-place)
- [Decisions I made, and why](#decisions-i-made-and-why)
- [Before you start: seven checks](#before-you-start-seven-checks)
- [Part A: build the four images and push them](#part-a-build-the-four-images-and-push-them)
- [Part B: put the deployment files on branch main](#part-b-put-the-deployment-files-on-branch-main)
- [Part C: stage](#part-c-stage)
- [Part D: production](#part-d-production)
- [Later: a new version, a changed setting, going back](#later-a-new-version-a-changed-setting-going-back)
- [If something goes wrong](#if-something-goes-wrong)
- [What I could not check from here](#what-i-could-not-check-from-here)
- [What is still open after this](#what-is-still-open-after-this)
- [Appendix: every file](#appendix-every-file)

---

## The short version

Today the four data agent programs (frontend, backend, MongoDB MCP server, Milvus MCP server)
run as Docker containers on the server `10.240.35.180`, started by hand. After this guide they
run inside the DICE cluster, the same way the defect agent does, and Argo CD starts and updates
them.

The work, in order:

1. **Part A.** Build the four images on the server and push them to the company registry.
2. **Part B.** Put the deployment files on branch `main` of the backend repo. They are one
   folder, `deploy/argocd/`: a description of the data agent (a "Helm chart") and one settings
   file per environment. Let Argo CD read that repo. No new repo is created, and nothing is
   added to the defect agent's repo.
3. **Part C, stage.** Create one Secret and one Argo CD Application. Press Sync. Test at
   `https://stage.gtrai.sec.samsung.net/data-agent`. Nobody is interrupted.
4. **Part D, production.** The same in the production namespace. The pods start beside the old
   containers and nobody is sent to them yet. One more Sync then moves
   `https://dice.gtrai.sec.samsung.net/data-agent` from the server to the cluster.

Five things run in the cluster afterwards: the four programs and a Postgres database of the
data agent's own. Stage has one database and production has another. Both start empty. The
Postgres on `10.240.35.180` is not used by the cluster.

Milvus, MongoDB and the feature extractor stay where they are, and the programs in the cluster
connect to them.

Two things are not in the cluster files but are needed first: a small change in the backend
code (a database password setting, already made in this repo on 2026-11-26), and the answers to
a few questions I cannot decide from the files you gave me. Those are collected in
[Before you start](#before-you-start-seven-checks), so you find out before anything is
deployed.

---

## How the pieces work together

1. An **image** is a packed program. You build it once, give it a **tag** (a version name) and
   push it to the **registry**, which is a store for images. The cluster downloads it from
   there.
2. A **Helm chart** is a folder of YAML templates. It describes what should run: for the data
   agent, four programs, a Postgres database with its disk, the internal addresses between
   them, and one forwarding rule. The templates have blanks.
3. A **values file** fills the blanks for one environment: which image tags, which database,
   which web address. There is one for stage and one for production. The chart is the same for
   both.
4. An **Argo CD Application** is one small object that says: "take this chart from this Git
   repo, fill it with this values file, and make this namespace look like the result".
5. **Sync** is the button that makes Argo CD do it. Argo CD compares Git with the cluster and
   creates or changes what differs.
6. Git is the source of truth. To change something later you change the values file in Git and
   press Sync. If you change an object by hand in the cluster, Argo CD shows it as "OutOfSync"
   and the next Sync puts it back.
7. Keys and passwords are the exception. They are **not** in Git. You create one **Secret** by
   hand in each namespace, and the chart only refers to it by name.

---

## Words used

| Word | Meaning |
|---|---|
| Cluster | The group of machines run by Kubernetes, where DICE and the defect agent live |
| Namespace | A named area inside the cluster. Production things are in `dice`, stage things in `dice-stage` |
| Image | A packed program with everything it needs. Made by `docker build` |
| Registry | The store for images. Here: `dice-docker-local.bart.sec.samsung.net` |
| Tag | The version name of an image, for example `2026.11.26-7561e6b` (date, then the Git commit) |
| Pod | One running copy of a program in the cluster. What a container is on the server |
| Deployment | The object that keeps a pod running and replaces it when you deploy a new tag |
| Service | A fixed internal name for a pod, for example `data-agent-backend`. Other pods use this name instead of an IP address |
| Secret | An object that holds keys and passwords. Pods receive them as environment variables |
| Disk claim (`PersistentVolumeClaim`) | A request for a disk that stays when a pod is replaced. A pod's own files are lost with the pod. The Postgres pod keeps its data on such a disk |
| Environment variable | A named setting handed to a program when it starts. All four programs can read their settings this way |
| `VirtualService` | The forwarding rule of the gateway: "paths starting with X go to Y" |
| Helm chart, values file | See the section above |
| Argo CD Application | See the section above. Shown as one tile in Argo CD |
| Sync | Make the cluster equal to Git |
| `OutOfSync` / `Synced` | Argo CD's answer to "does the cluster equal Git?" |
| `Missing` | The object is in Git but not yet in the cluster. Normal before the first Sync |
| `Progressing` / `Healthy` / `Degraded` | Starting, running fine, or failing to start |
| Sidecar | A small helper container that Istio adds to every pod. This is why a pod shows `2/2` containers although you deployed one |

---

## How the defect agent is deployed, and what the data agent copies

Read from the files you gave me (`ARGOCD_DEFECT_DEPLOY.MD`, `ARGOCD_DEPLOYMENT.md`,
`argocd-application-repository/`, `DEPLOY.md`, `DEPLOY_CONFIG_261121.md`).

| Fact about the defect agent | Value |
|---|---|
| Git repo Argo CD reads | `https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git`, branch `main` |
| Chart folder | `charts/defect-studio` |
| Values files | `environments/stage/defect-studio.yaml`, `environments/production/defect-studio.yaml` |
| Argo CD Applications | `defect-stage` into namespace `dice-stage`, `defect-prod` into namespace `dice` |
| Argo CD project | `dice` |
| Sync | Stage: automatic. Production: by hand |
| Registry and images | `dice-docker-local.bart.sec.samsung.net/defect-studio-backend:<tag>`, `.../defect-studio-frontend:<tag>` |
| Permission to download images | A Secret named `regcred` in each namespace |
| Keys and passwords | Secrets `defect-studio-stage-secrets` and `defect-studio-prod-secrets`, created by hand, not in Git |
| Forwarding | One `VirtualService` on gateway `istio-system/platform-gateway`, for `stage.gtrai.sec.samsung.net` and `dice.gtrai.sec.samsung.net`. The same rule forwards `/auth/...` to the DICE login service |
| How images get built | GitHub Actions in the defect agent repos build, push, and write the new tag into the stage values file |

The data agent follows the same pattern: a chart and one values file per environment, two
Applications, the same Argo CD project and the same two namespaces.

Four differences:

- **The data agent's deployment files are not in a repo of their own.** They live in the
  backend repo, in the folder `deploy/argocd/`. Nothing is added to the defect agent's repo.
  The price is two settings in Argo CD, made once: Argo CD has to be able to read the backend
  repo (B3), and project `dice` has to accept it (B4).
- The data agent has four programs and a Postgres of its own, so its chart has five
  Deployments. The defect agent has no database of its own: it keeps its data in a database on
  DICE's Postgres.
- Its images are built and pushed by hand for now (Part A). GitHub Actions can come later.
- Stage is synced by hand too, so that nothing happens before you press the button.

DICE itself (Application `dice`, described in `ARGOCD_DICE_DEPLOY.MD`) is deployed differently:
its chart lives inside the DICE code repo and its tags are set as parameters in Argo CD. I did
not copy that, because the defect agent's way is simpler and closer to what the data agent is.

---

## What you have today and what you will have

| Piece | Today | After Part D |
|---|---|---|
| Frontend (port 13080) | Container on `10.240.35.180` | Pod `data-agent-frontend` in the cluster |
| Backend (port 18080) | Container on `10.240.35.180` | Pod `data-agent-backend` in the cluster |
| MongoDB MCP server (port 10420) | Container on `10.240.35.180` | Pod `data-agent-mongodb-mcp` in the cluster |
| Milvus MCP server (port 10422) | Container on `10.240.35.180` | Pod `data-agent-milvus-mcp` in the cluster |
| Postgres (chats, accounts, admins) | `10.240.35.180:5432`, database `cosmoData` | Pod `data-agent-postgres` in the cluster, with its own disk. New and empty. The one on the server is not used any more |
| Milvus | `10.240.35.180:19530` | Unchanged |
| MongoDB | `dev.gtrai.sec.samsung.net:27017` | Unchanged |
| Feature extractor | `10.240.28.235:24502` | Unchanged |
| Object storage | Bucket `cosmo-storage` | Unchanged |
| Forwarding rule on DICE | `VirtualService` `data-agent`, made by hand, sends `/data-agent` to `10.240.35.180:13080` | Same name, now made by Argo CD, sends `/data-agent` to the frontend pod |
| Settings | One `config.yaml` per program, copied into the image | Values file in Git, plus one Secret |
| Starting and updating | `docker build` and `docker run` by hand on the server | Change a tag in Git, press Sync |

How a request travels afterwards:

```
Browser
   |   https://stage.gtrai.sec.samsung.net/data-agent     (stage)
   |   https://dice.gtrai.sec.samsung.net/data-agent      (production)
   v
Gateway (platform-gateway)
   |   /data-agent ...  ->  frontend                (new rule, from the data agent chart)
   |   /auth/...        ->  DICE login service      (existing rule of the defect agent)
   v
--------------------------- inside the cluster ---------------------------
frontend :13080  ->  backend :18080  ->  mongodb-mcp :10420  ->  MongoDB            (outside)
                          |          ->  milvus-mcp  :10422  ->  Milvus             (outside)
                          |                                  ->  feature extractor  (outside)
                          |                                  ->  object storage     (outside)
                          +->  postgres :5432, with its own disk                    (inside)
                          +->  object storage                                       (outside)
                          +->  language model, mlp-service.n10.sr-cloud.com         (outside)
```

Only the frontend is reachable from a browser. The backend, the two MCP servers and Postgres
have internal names only. Postgres cannot be reached from outside the cluster at all.

---

## All names in one place

| Thing | Stage | Production |
|---|---|---|
| Web address | `https://stage.gtrai.sec.samsung.net/data-agent` | `https://dice.gtrai.sec.samsung.net/data-agent` |
| Namespace | `dice-stage` | `dice` |
| Argo CD Application | `data-agent-stage` | `data-agent-prod` |
| Values file | `deploy/argocd/environments/stage/data-agent.yaml` | `deploy/argocd/environments/production/data-agent.yaml` |
| Secret (made by hand) | `data-agent-stage-secrets` | `data-agent-prod-secrets` |
| Postgres | Pod `data-agent-postgres` in `dice-stage`, database `data_agent`, new and empty | Pod `data-agent-postgres` in `dice`, database `data_agent`, new and empty |
| Database password | Invented by you in C1 | Invented by you in D1, a different one |
| Forwarding rule (`VirtualService`) | `data-agent-stage` | `data-agent` |
| Signing secret is copied from | Secret `dice-stage-runtime`, key `service-jwt` | Secret `dice-runtime`, key `service-jwt` |
| Login | The login service of stage DICE | Samsung SSO, as today |

The same in both:

| Thing | Value |
|---|---|
| Git repo and branch | The backend repo on the company GitHub, `cosmo-data-agent-backend`, branch `main` |
| Folder with all deployment files | `deploy/argocd/` |
| Chart folder | `deploy/argocd/charts/data-agent` |
| Argo CD project | `dice` |
| Registry | `dice-docker-local.bart.sec.samsung.net` |
| Images you build | `cosmo-data-agent-backend`, `cosmo-data-agent-frontend`, `cosmo-mongodb-mcp-server`, `cosmo-milvus-mcp-server` |
| Image that is not yours | `docker-remote.bart.sec.samsung.net/postgres:16-alpine`. Nothing to build |
| Objects the chart creates | Deployments and Services `data-agent-backend`, `data-agent-frontend`, `data-agent-mongodb-mcp`, `data-agent-milvus-mcp`, `data-agent-postgres`, the disk claim `data-agent-postgres-data`, and one `VirtualService` |

---

## Decisions I made, and why

You asked for one way, not a list of options. These are the choices built into the files.

1. **All deployment files live in the backend repo, in `deploy/argocd/`.** You decided this on
   2026-11-26: not the defect agent's repo, no new repo, and one place for all four programs
   instead of one per program. One place keeps it at one chart and two Applications. It has
   three consequences:
   - Argo CD reads one fixed branch, `main`. Deployment files count only there. The rule is at
     the start of [Part B](#part-b-put-the-deployment-files-on-branch-main).
   - The backend repo also holds the settings of the frontend and of the two MCP servers.
   - A new image tag is a commit in the backend repo, also when the new image is the
     frontend's.

   The two Applications stay in Argo CD project `dice`. That project already allows the two
   namespaces, as `defect-stage` and `defect-prod` show. It only has to accept one more repo
   (B4).

2. **The data agent gets a Postgres of its own in the cluster.** You decided this on
   2026-11-26: deploy Postgres too, and do not use the one on `10.240.35.180`. Postgres holds
   the data agent's own memory (chats, accounts, admins, approvals), so it belongs to the data
   agent's deployment. It is part of the same chart. I did not put the data into DICE's
   Postgres, which is what the defect agent does, so that the data agent depends on no other
   product's database.

   Milvus and MongoDB are a different case and stay where they are. They are the data the
   agent looks into, not its own memory.

3. **Stage and production each have their own database.** It follows from point 2, because
   each namespace gets its own Postgres pod. It also has to be so, for two reasons from the
   code:
   - On stage DICE, as I understood it on 2026-11-21, login is a simulator: a person on its
     allow list types a login ID and is logged in as that ID, without a password
     (`mvp-vision-ai-platform/web-auth/app/dev-login`). On a shared database, anyone on that
     list could type a colleague's ID and read that colleague's real chats, or type an admin's
     ID and be an admin.
   - When the backend starts, it marks every session as "not running"
     (`data_agent/infra/session_lock.py`, `initialize`). Two backends on one database disturb
     each other every time one of them restarts.

4. **Both databases start empty.** Nothing is copied from the server. For production this
   means that accounts and approvals start again and that today's chats are not shown after
   the switch. They stay on the server, untouched. Part D says this again where it matters,
   and how to ask for a copy if you want one.

5. **How the database is set up, and why.**
   - **Its data is on a disk that Argo CD never deletes**, not even when the Application is
     deleted. The claim carries the same two markings as the disk of DICE's own database.
   - **The disk comes from the storage class `nfs-csi`, and the image is `postgres:16-alpine`.**
     I chose both because the defect agent already runs exactly this image on exactly this
     kind of disk in this cluster (its Temporal database), so the combination is known to work
     here.
   - **It has a password**, which you invent and put into the Secret. The backend could not
     send a database password before. I added that setting on 2026-11-26
     (`POSTGRESQL_DB_PASSWORD`, in `common/config.py` and
     `data_agent/infra/postgresql_client.py`). Without a password setting nothing changes for
     the containers on the server.
   - **It is one pod, with no copy and no backup.** If the machine it runs on fails, the data
     agent is down until the pod is started elsewhere, and the data is as safe as the disk. A
     regular backup is the first thing to add afterwards. It is in
     [What is still open](#what-is-still-open-after-this).

6. **Keys and passwords are not inside the images.** Today each image contains its
   `config.yaml` with the keys. That is acceptable for an image that never leaves the server.
   An image in the shared registry can be downloaded by everyone who can use the registry.
   So the cluster images contain a `config.yaml` of one line, and every other setting arrives
   as an environment variable: plain ones from the values file, secret ones from the Secret.
   All three Python programs already support this (`common/config.py` in each). I checked it
   on this PC: each one loads its settings from a one-line file plus environment variables,
   and the backend names the missing setting when one is left out.

7. **Health checks only ask "is the port open".** The backend's `GET /health` asks Postgres and
   the object storage on every call and writes log lines each time. The MCP servers' `/health`
   asks MongoDB or Milvus. A health check that depends on another system restarts a healthy
   program when that other system is slow. The backend opens its port only after it has reached
   Postgres and created its tables, so "the port is open" already means "it started properly".
   The frontend is asked for a real page instead, which also catches an image built with the
   wrong base path. Postgres is asked with its own tool, `pg_isready`.

8. **One backend, and `Recreate`.** Because of the lock reset in point 3, the old backend pod
   is stopped before the new one starts. A deploy therefore interrupts the backend for about
   a minute, and answers that are being written at that moment are cut. The same happens today
   when you restart the container.

9. **The production switch is one Sync.** The production forwarding rule in the chart has the
   same name as the rule you made by hand (`data-agent`). When Argo CD applies it, the existing
   rule is overwritten in place. There is no moment with two rules or with none.

### What stage shares with production

Read this once, so it does not surprise you later. Stage has its own chats, accounts and
admins. Everything else is the same as production, because there is only one of each:

| Shared | Consequence |
|---|---|
| MongoDB, Milvus | A question on stage reads the real data. A tool call that changes data changes the real data |
| Bucket `cosmo-storage` | Files uploaded on stage are stored next to the production ones, under their own session IDs |
| Language model | Stage questions use the same model service and quota |

If separate stage copies of MongoDB or Milvus exist, the addresses to change are the
`mongodbMcp.env` and `milvusMcp.env` lines of `deploy/argocd/environments/stage/data-agent.yaml`.

---

## Before you start: seven checks

Do these first. Each takes a few minutes, and each one can stop the whole plan, so it is better
to know now.

### Check 1. Can you push images to the registry?

On the server `10.240.35.180`:

```bash
sudo docker login dice-docker-local.bart.sec.samsung.net
```

It asks for a user name and a password. Use your account of the company Artifactory
(`bart.sec.samsung.net`). If the password is refused, create an "identity token" on the
Artifactory web page (your profile, top right) and use the token as the password.

**You should see:** `Login Succeeded`.

This proves the account works. Whether it may *write* to `dice-docker-local` only shows at the
first push in Part A. If that push answers `denied` or `unauthorized`, your account has no
write permission there. The defect agent uses a build account for this (the GitHub secrets
`DOCKER_USERNAME` and `DOCKER_PASSWORD` in its workflows). Ask the person who manages them for
write permission for your account, or for that account.

### Check 2. Can you change branch `main` of the backend repo, and Argo CD's settings?

1. Open the backend repo `cosmo-data-agent-backend` on the company GitHub and open the branch
   selector at the top left of the file list.
   **You should see:** a branch called `main`.
2. With `main` selected, open a small file, for example `README.md`, and look for the pencil
   symbol at the top right of the file. Do not change anything.
   **You should see:** the pencil can be pressed. If GitHub says the branch is protected,
   changes to it go through a pull request. That works too. It is one more click each time.
3. In Argo CD, open "Settings" in the left bar.
   **You should see:** "Repositories" with a `+ CONNECT REPO` button, and "Projects" with the
   project `dice` in it. Open `dice`. The boxes on that page should offer an `EDIT` button. Do
   not change anything yet.

If there is no `main`, or it is not yours to change, read the last paragraph of B2: any branch
that keeps its name will do. If step 3 is not possible with your account, ask the person who
can do B3 and B4 for you.

### Check 3. Is `/data-agent` free on the stage address?

1. Open `https://stage.gtrai.sec.samsung.net/data-agent` in a browser.
   **You should see:** an error page or a "not found" page. Not a working product.
2. In the Kubernetes Dashboard, set the namespace selector to "All namespaces", open
   "Custom Resource Definitions" in the left menu, then `VirtualService`.
   **You should see:** no object with `data-agent` in its name, except the one named
   `data-agent` in namespace `dice`. That one is the production rule you made by hand.

### Check 4. Can you log in on stage DICE?

1. Open `https://stage.gtrai.sec.samsung.net/auth/session`.
   **You should see:** a short text starting with `{"authenticated":`. This proves that the
   login service answers under `/auth` on the stage address.
2. Open `https://stage.gtrai.sec.samsung.net/auth/login`.
   **You should see:** a small form that asks for a login ID. That is the login simulator.
   Type your own login ID in lower case.
3. Open `https://stage.gtrai.sec.samsung.net/auth/session` again.
   **You should see:** `"authenticated":true` and your ID.

If step 2 answers `{"error":"forbidden"}`, your ID is not on the simulator's allow list. The
list is the setting `DEV_LOGIN_ALLOWED_IDS` of the stage login service. It is set in the Argo CD
Application of stage DICE, under `webAuth.env`. Add your ID there, or ask the person who
looks after stage DICE.

If step 2 shows Samsung SSO instead of a form, stage has real SSO now. That is fine too. Carry
on.

### Check 5. Do the outside systems accept connections from other machines?

On the server the Milvus MCP container reaches Milvus on the same machine. From the cluster the
MCP pods come over the network, and a firewall could refuse them. From your company PC, in
PowerShell:

```powershell
Test-NetConnection 10.240.35.180 -Port 19530
Test-NetConnection 10.240.28.235 -Port 24502
Test-NetConnection dev.gtrai.sec.samsung.net -Port 27017
```

**You should see:** `TcpTestSucceeded : True` three times.

Your PC is not the cluster, so this is a hint and not a proof. `True` means the machine does
not block that port for others. `False` usually means the cluster will be refused too. In that
case open the port on that machine first, the way port 13080 was opened
(`sudo firewall-cmd --add-port=19530/tcp --permanent`, then `sudo firewall-cmd --reload`, or
`sudo ufw allow 19530/tcp`).

Postgres is not in this list. The database is inside the cluster.

### Check 6. Do the values I wrote match what runs today?

I filled the two values files from the `config.yaml` files in the repos on this PC. What counts
is what runs on the server. Print the three files there:

```bash
sudo docker ps --format 'table {{.Names}}\t{{.Image}}'
sudo docker exec data_agent_backend cat /home/work/cosmo-data-agent-backend/config.yaml
sudo docker exec mongodb_mcp_server cat /home/work/cosmo-mongodb-mcp-server/config.yaml
sudo docker exec milvus_mcp_server cat /home/work/cosmo-milvus-mcp-server/config.yaml
```

The first line lists the containers. If a container has another name on your server, use that
name in the lines below it. The output contains keys, so do not paste it anywhere.

Keep the output open. This table says where each line goes. "Values file" means both
`deploy/argocd/environments/stage/data-agent.yaml` and `deploy/argocd/environments/production/data-agent.yaml`.

Backend `config.yaml`:

| Line in `config.yaml` | Goes to | Name there |
|---|---|---|
| `server_port` | Nowhere. The chart sets 18080 | |
| `root_model_openapi.model` | Values file, `backend.env` | `ROOT_MODEL_OPENAPI_MODEL` |
| `root_model_openapi.endpoint` | Values file, `backend.env` | `ROOT_MODEL_OPENAPI_ENDPOINT` |
| `root_model_openapi.model_id` | Values file, `backend.env` | `ROOT_MODEL_OPENAPI_MODEL_ID` |
| `root_model_openapi.client_key` | Secret | `root-model-client-key` |
| `root_model_openapi.pass_key` | Secret | `root-model-pass-key` |
| `title_model_openapi.model` | Values file, `backend.env` | `TITLE_MODEL_OPENAPI_MODEL` |
| `title_model_openapi.endpoint` | Values file, `backend.env` | `TITLE_MODEL_OPENAPI_ENDPOINT` |
| `title_model_openapi.model_id` | Values file, `backend.env` | `TITLE_MODEL_OPENAPI_MODEL_ID` |
| `title_model_openapi.client_key` | Secret | `title-model-client-key` |
| `title_model_openapi.pass_key` | Secret | `title-model-pass-key` |
| `mongodb_mcp.host`, `.port` | Nowhere. The chart points the backend at the MCP pods | |
| `milvus_mcp.host`, `.port` | Nowhere. Same | |
| `postgresql_db.*` | Nowhere. The chart points the backend at the Postgres pod of the same environment | The password is new: you invent it in C1 and D1 |
| `object_storage.bucket`, `.endpoint` | Values file, `backend.env` and `milvusMcp.env` | `OBJECT_STORAGE_BUCKET`, `OBJECT_STORAGE_ENDPOINT` |
| `object_storage.access_key` | Secret | `s3-access-key` |
| `object_storage.secret_key` | Secret | `s3-secret-key` |
| `auth.service_jwt_secret` | Production Secret only | `service-jwt-secret`. Stage has a different one, see C1 |
| `auth.service_jwt_issuer`, `.service_jwt_audience` | Nowhere. The chart sets `web-auth` and `dice-backend` | |

MongoDB MCP `config.yaml`:

| Line | Goes to | Name there |
|---|---|---|
| `server_port` | Nowhere. The chart sets 10420 | |
| `mongodb_host`, `mongodb_port`, `mongodb_db_name` | Values file, `mongodbMcp.env` | `MONGODB_HOST`, `MONGODB_PORT`, `MONGODB_DB_NAME` |

Milvus MCP `config.yaml`:

| Line | Goes to | Name there |
|---|---|---|
| `server_port` | Nowhere. The chart sets 10422 | |
| `milvus.host`, `.port`, `.db_name` | Values file, `milvusMcp.env` | `MILVUS_HOST`, `MILVUS_PORT`, `MILVUS_DB_NAME` |
| `milvus.user`, `.password` | Nowhere, as long as both are empty | If they are not empty, tell me. The chart does not pass them yet |
| `feature_extractor.host`, `.port` | Values file, `milvusMcp.env` | `FEATURE_EXTRACTOR_HOST`, `FEATURE_EXTRACTOR_PORT` |
| `object_storage.*` | As for the backend | The chart gives both programs the same bucket and the same two keys |

Two places where I already know the repos disagree with each other, so look closely:

- **The title model.** The last committed backend `config.yaml` names another model and another
  service address for it than the file I read today. I used today's. The server's file decides.
- **The object storage address.** It is `https://s3.ap-northeast-2.samsungspc.com` in today's
  files and `https://gage.ap-northeast-2.samsungspc.com` in older ones. I used the first.

If the Milvus MCP server on your server uses other object storage keys than the backend, tell
me. The chart assumes they are the same, as they are in the repos.

### Check 7. Two things the database needs

1. **A kind of disk called `nfs-csi`.** In the Kubernetes Dashboard, open "Storage Classes" in
   the left menu (under "Cluster").
   **You should see:** a line named `nfs-csi`. The defect agent's databases use it. If the name
   is spelled differently in the list, tell me the list. It is one line in the chart.
2. **A command line inside a pod.** The first admin is put into the database from inside the
   database's pod (C5, D5). In the Dashboard, namespace `dice-stage`, "Pods", click any pod.
   **You should see:** a button "Exec into pod" at the top right. Press it. A black box with a
   prompt appears. Type nothing and close it again.

If there is no such button, look in Argo CD: click a pod there and look for a tab `TERMINAL`.
If neither exists, tell me before you start. There is another way to do C5 and D5, but it is
not written here.

---

## Part A: build the four images and push them

All of Part A happens on the server `10.240.35.180`. The running containers are not touched.

The three Python images are built in a new, clean folder, not in the folders you use today.
The reason: today's folders contain the real `config.yaml` and the log files, and both would
end up inside an image that many people can download.

### A1. Prepare

```bash
sudo docker login dice-docker-local.bart.sec.samsung.net      # Check 1, if not done yet
ls -d /home/cosmo/projects/*/*/.git                           # lists the code folders
```

The second line shows where the four code folders are. The run scripts suggest these three for
the Python programs. If yours differ, change the `SRC=` line in A2, A3 and A4.

```
/home/cosmo/projects/data-agent-backend/cosmo-data-agent-backend
/home/cosmo/projects/mongodb-mcp-server/cosmo-mongodb-mcp-server
/home/cosmo/projects/milvus-mcp-server/cosmo-milvus-mcp-server
```

Now write the list of things that must stay out of the images. Paste the whole block:

```bash
mkdir -p ~/k8s-images
cat > ~/k8s-images/dockerignore <<'EOF'
**/.git
**/__pycache__
**/logs
**/tests
**/docs
*/temp
*/deploy
*/config.yaml
*/DEPLOY*
*/ARGOCD*
*/defect-studio-backend-service
*/defect-studio-train-service
*/mvp-vision-ai-platform
*/argocd-application-repository
EOF
```

`*/config.yaml` is the important line. The code folder has a `config.yaml` of its own, and it
has held real keys. This line keeps it out. The image gets a one-line `config.yaml` instead.

### A2. Backend

The backend image has to be built from code that knows the database password setting. I added
it on this PC on 2026-11-26, in four files:

```
common/config.py
data_agent/infra/postgresql_client.py
tests/common/test_config.py
tests/infra/test_postgresql_client.py
```

Before you build: commit these four files, bring them to the company repo the way you
normally do, and run `git pull` in the backend code folder on the server. Pulling does not
touch the running container. The block below checks that the change has arrived.

```bash
REG=dice-docker-local.bart.sec.samsung.net
SRC=/home/cosmo/projects/data-agent-backend/cosmo-data-agent-backend

git -C $SRC status --short       # should print nothing
git -C $SRC log -1 --oneline     # the version that goes into the image

mkdir -p ~/k8s-images/backend && cd ~/k8s-images/backend
rm -rf cosmo-data-agent-backend
git clone -q $SRC cosmo-data-agent-backend
grep -q POSTGRESQL_DB_PASSWORD cosmo-data-agent-backend/common/config.py && echo "password setting: present" || echo "password setting: MISSING, stop here"
cp $(dirname $SRC)/Dockerfile Dockerfile
cp ~/k8s-images/dockerignore .dockerignore
echo "server_port: 18080" > config.yaml

TAG=$(date +%Y.%m.%d)-$(git -C cosmo-data-agent-backend rev-parse --short HEAD)
sudo docker build -t $REG/cosmo-data-agent-backend:$TAG .
sudo docker run --rm $REG/cosmo-data-agent-backend:$TAG cat config.yaml
sudo docker push $REG/cosmo-data-agent-backend:$TAG
echo "backend tag: $TAG"
```

What the lines do:

- `git status --short` lists changes that exist only on the server and are not committed.
  `git clone` in the next step copies committed code only. If the line prints something, those
  changes would be missing from the image. Commit and push them first, the way you normally do,
  then start A2 again.
- `git clone` makes a clean copy of exactly the version that runs today.
- `cp $(dirname $SRC)/Dockerfile` takes the `Dockerfile` you build with today. It lies beside
  the code folder. The file is used unchanged.
- `TAG` becomes today's date and the commit, for example `2026.11.26-7561e6b`.

**You should see:**

- `password setting: present`. If it says `MISSING`, the code change is not in the server's
  code folder yet. Stop, bring it there, and start A2 again. An image without it cannot log in
  to the new database.
- The build ends without an error.
- The `docker run` line prints exactly one line: `server_port: 18080`. If it prints more, the
  real `config.yaml` got into the image. Do not push. Check that `.dockerignore` exists in the
  folder (`ls -a`) and build again.
- The push ends with a line containing `digest: sha256:`.
- The last line prints the tag. **Write it down.**

### A3. MongoDB MCP server

```bash
REG=dice-docker-local.bart.sec.samsung.net
SRC=/home/cosmo/projects/mongodb-mcp-server/cosmo-mongodb-mcp-server

git -C $SRC status --short
git -C $SRC log -1 --oneline

mkdir -p ~/k8s-images/mongodb-mcp && cd ~/k8s-images/mongodb-mcp
rm -rf cosmo-mongodb-mcp-server
git clone -q $SRC cosmo-mongodb-mcp-server
cp $(dirname $SRC)/Dockerfile Dockerfile
cp ~/k8s-images/dockerignore .dockerignore
echo "server_port: 10420" > config.yaml

TAG=$(date +%Y.%m.%d)-$(git -C cosmo-mongodb-mcp-server rev-parse --short HEAD)
sudo docker build -t $REG/cosmo-mongodb-mcp-server:$TAG .
sudo docker run --rm $REG/cosmo-mongodb-mcp-server:$TAG cat config.yaml
sudo docker push $REG/cosmo-mongodb-mcp-server:$TAG
echo "mongodb-mcp tag: $TAG"
```

**You should see:** the same four things as in A2, with `server_port: 10420`.

### A4. Milvus MCP server

```bash
REG=dice-docker-local.bart.sec.samsung.net
SRC=/home/cosmo/projects/milvus-mcp-server/cosmo-milvus-mcp-server

git -C $SRC status --short
git -C $SRC log -1 --oneline

mkdir -p ~/k8s-images/milvus-mcp && cd ~/k8s-images/milvus-mcp
rm -rf cosmo-milvus-mcp-server
git clone -q $SRC cosmo-milvus-mcp-server
cp $(dirname $SRC)/Dockerfile Dockerfile
cp ~/k8s-images/dockerignore .dockerignore
echo "server_port: 10422" > config.yaml

TAG=$(date +%Y.%m.%d)-$(git -C cosmo-milvus-mcp-server rev-parse --short HEAD)
sudo docker build -t $REG/cosmo-milvus-mcp-server:$TAG .
sudo docker run --rm $REG/cosmo-milvus-mcp-server:$TAG cat config.yaml
sudo docker push $REG/cosmo-milvus-mcp-server:$TAG
echo "milvus-mcp tag: $TAG"
```

**You should see:** the same four things as in A2, with `server_port: 10422`.

### A5. Frontend

The frontend image holds no keys, and its `Dockerfile` is inside its code folder. So it is built
where you build it today. Go into the `cosmo-data-agent-frontend` folder first.

```bash
REG=dice-docker-local.bart.sec.samsung.net

git status --short
git log -1 --oneline

TAG=$(date +%Y.%m.%d)-$(git rev-parse --short HEAD)
sudo docker build -t $REG/cosmo-data-agent-frontend:$TAG .
sudo docker push $REG/cosmo-data-agent-frontend:$TAG
echo "frontend tag: $TAG"
```

This build uses the folder as it is. Lines that `git status --short` prints with an `M` are
changed files that are not committed. They do go into the image, but Git does not know them, so
commit them when you can.

Do not add `--build-arg`. A plain build is made for the path `/data-agent`, and both stage and
production use that path. One image serves both.

**You should see:** the build and the push end without an error, and the tag is printed.
**Write it down.**

### A6. The four tags

You now have four tags. They can differ from each other, because each repo has its own commit.

| Image | Tag (fill in) |
|---|---|
| `cosmo-data-agent-backend` | |
| `cosmo-data-agent-frontend` | |
| `cosmo-mongodb-mcp-server` | |
| `cosmo-milvus-mcp-server` | |

One rule: a tag is never reused for other content. A new commit gives a new tag by itself. That
is what makes "go back to the previous version" reliable.

---

## Part B: put the deployment files on branch `main`

The deployment files of all four programs and of the database live in the backend repo, in one
folder: `deploy/argocd/`. No new repo is created, and nothing is added to the defect agent's repo.

**The one rule.** Argo CD reads the folder `deploy/argocd/` on branch `main` of the backend
repo, and nothing else.

- A change to a tag or a setting counts only when it is on `main`. On any other branch it does
  nothing in the cluster.
- Change the files in `deploy/argocd/` on `main` only, never on a working branch. Two versions
  of the same file are what makes a later merge into `main` complain.
- The rest of the repo does not matter to Argo CD. Pushing code changes nothing in the cluster.
  Code reaches the cluster only as an image (Part A) whose tag you write into a values file.

The easiest way to change a file on `main` needs no Git commands: on the repo's web page,
select branch `main`, open the file, press the pencil symbol, change the line, and press
"Commit changes". Your working branch on your PC is not involved. D2, D6 and every later
deploy use this.

### B1. Fill in three things

In the folder `deploy/argocd/`:

1. **The repo address.** In `deploy/argocd/applications/data-agent-stage.yaml` and
   `deploy/argocd/applications/data-agent-prod.yaml`, replace `YOUR-ORG` in the `repoURL` line
   with the owner of the backend repo on the company GitHub. The line then holds the address
   `https://github.sec.samsung.net/<owner>/cosmo-data-agent-backend.git`. **Write that address
   down.** It is needed again in B3 and B4, and has to be spelled exactly the same there.
2. **The four tags.** In `deploy/argocd/environments/stage/data-agent.yaml`, put the tags from
   A6 into the four lines that say `tag: ""`. Keep the quotes: `tag: "2026.11.26-7561e6b"`.
   Each tag belongs to its own block: `backend:`, `frontend:`, `mongodbMcp:`, `milvusMcp:`.
3. **Lines that differ from the server** (Check 6). Correct them in both files under
   `deploy/argocd/environments/`, so that production is not forgotten. Keep every value in
   quotes, also numbers: `POSTGRESQL_DB_PORT: "5432"`.

Leave the four `tag: ""` lines of `deploy/argocd/environments/production/data-agent.yaml`
empty for now. Production gets its tags in D2.

### B2. Bring the folder to branch `main`

The folder has to arrive on branch `main` of the backend repo on the company GitHub. If you
normally bring changes to `main` by merging your working branch or through a pull request, do
it that way. What counts is the result. Done directly, in a copy of the company repo, it is:

```bash
git checkout main
git pull origin main
# copy the folder deploy/argocd into the repo here, if it is not there yet
git add deploy/argocd
git status                # should list twelve new files, all under deploy/argocd/
git commit -m "Add Argo CD deployment files for the data agent"
git push origin main
git checkout -            # back to the branch you were on
```

**You should see:** on the repo's web page, with branch `main` selected, this folder:

```
deploy/argocd/
    applications/
        data-agent-stage.yaml
        data-agent-prod.yaml
    charts/
        data-agent/
            Chart.yaml
            values.yaml
            templates/
                backend.yaml
                frontend.yaml
                mongodb-mcp.yaml
                milvus-mcp.yaml
                postgres.yaml
                virtualservice.yaml
    environments/
        stage/
            data-agent.yaml
        production/
            data-agent.yaml
```

| Folder inside `deploy/argocd/` | What it is | Who reads it |
|---|---|---|
| `charts/` | The chart: what runs. The same for stage and production | Argo CD |
| `environments/` | The settings of each environment: tags, addresses, database | Argo CD |
| `applications/` | The text of the two Argo CD Applications | Only you. You paste it into Argo CD in C2 and D3. It is kept in the repo so that it is not lost |

If the company repo has no branch `main`, or `main` is not yours to change: use another branch
that keeps its name (not one with a date in it), put the folder there, and write that branch's
name instead of `main` in the `targetRevision` line of both Application files. Everything this
guide says about `main` then applies to that branch.

### B3. Let Argo CD read the backend repo

Argo CD has to be able to download the repo. For a repo that is not public it needs a key.

First try without one. Argo CD may already hold a key that fits every repo of your
organization.

1. In Argo CD, open "Settings" in the left bar, then "Repositories", and press `+ CONNECT REPO`.
2. Fill in:

   | Field | Value |
   |---|---|
   | Connection method | `VIA HTTPS` |
   | Type | `git` |
   | Project | Leave empty |
   | Repository URL | The address from B1 |
   | Username, Password | Leave empty for this first try |

3. Press `CONNECT`.

**You should see:** the repo in the list with connection status `Successful`. Then B3 is done.

If Argo CD answers with an error about authentication instead, it has no key for this repo, and
you give it one:

1. On the company GitHub, click your picture at the top right, "Settings", "Developer
   settings", "Personal access tokens", and generate a new token. Name it
   `argocd-cosmo-data-agent`, tick the scope `repo`, and choose the longest lifetime your
   company allows. Copy the token. GitHub shows it only once.
2. Repeat `+ CONNECT REPO` with the same fields, and this time put your GitHub login into
   "Username" and the token into "Password".

**You should see:** connection status `Successful`.

The token is a key. Do not write it into any file. Argo CD stores it itself.

### B4. Let project `dice` accept the repo

An Argo CD project has a list of repos its Applications may come from. The data agent's
Applications are in project `dice` (the reason is in
[Decisions](#decisions-i-made-and-why), point 1), so that list needs the backend repo.

1. In Argo CD: "Settings", "Projects", `dice`.
2. Look at the box "SOURCE REPOSITORIES".
   - If it contains a line `*`, every repo is accepted. Nothing to do.
   - Otherwise press `EDIT` in that box, `ADD SOURCE`, paste the address from B1, and `SAVE`.

**You should see:** your address in the list, and the lines that were there before unchanged.

This is the only change in this guide to something that DICE and the defect agent share. It
adds one line and takes nothing away.

Look at the list once more ten minutes later. If your line is gone, the project itself is kept
in Git somewhere and Argo CD has put the old list back. Tell me in that case. The line then has
to be added in that Git repo instead.

Nothing has changed in the cluster yet. Argo CD can read the backend repo now, but no
Application points to it so far.

---

## Part C: stage

Nobody is interrupted in Part C. Stage is new from top to bottom, including its database.

### C1. Create the stage Secret

First invent a password for the stage database. On the server, or on any Linux machine:

```bash
openssl rand -hex 24
```

It prints 48 random characters. That is the password. Nobody has to remember or type it again:
Postgres takes it when it starts for the first time, and the backend reads it from the same
Secret.

In the Kubernetes Dashboard:

1. Set the namespace selector at the top to `dice-stage`.
2. Press the `+` button at the top right ("Create new resource"), tab "Create from input".
3. Paste the text below, replace the eight `PASTE...` parts, and press "Upload".

Type the real values only into this box in the browser. Do not save the filled-in text in a
file inside a Git folder.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: data-agent-stage-secrets
  namespace: dice-stage
type: Opaque
stringData:
  postgres-password: "PASTE_NEW_DATABASE_PASSWORD"
  service-jwt-secret: "PASTE_STAGE_SIGNING_SECRET"
  s3-access-key: "PASTE_OBJECT_STORAGE_ACCESS_KEY"
  s3-secret-key: "PASTE_OBJECT_STORAGE_SECRET_KEY"
  root-model-client-key: "PASTE_ROOT_MODEL_CLIENT_KEY"
  root-model-pass-key: "PASTE_ROOT_MODEL_PASS_KEY"
  title-model-client-key: "PASTE_TITLE_MODEL_CLIENT_KEY"
  title-model-pass-key: "PASTE_TITLE_MODEL_PASS_KEY"
```

Where each value comes from:

| Line | Copy it from |
|---|---|
| `postgres-password` | The password you just invented |
| `service-jwt-secret` | Dashboard, namespace `dice-stage`, "Secrets", `dice-stage-runtime`, key `service-jwt`. Press the eye symbol to see the plain text. In your notes it is `DEPLOY.md`, section "3d. dice-stage-runtime". It is a long random text of 64 characters |
| `s3-access-key`, `s3-secret-key` | The backend `config.yaml` from Check 6: `object_storage.access_key` and `object_storage.secret_key` |
| `root-model-client-key`, `root-model-pass-key` | Same file: `root_model_openapi.client_key` and `.pass_key` |
| `title-model-client-key`, `title-model-pass-key` | Same file: `title_model_openapi.client_key` and `.pass_key` |

Four things to get right:

- **Plain text, not base64.** The section is called `stringData`, and Kubernetes encodes the
  values itself. Paste what the eye symbol shows, not the text that ends in `==`.
- **The stage signing secret, not the production one.** Stage DICE signs its passes with a
  different secret than production. With the production secret in this place every stage login
  is refused.
- **Copy a value completely.** If a pass key starts with a word and a space (for example
  `Bearer ...`), the word belongs to the value. If a value contains a double quote, put the
  value in single quotes instead.
- **The database password is fixed at the first start.** Postgres writes it into its data when
  it starts on the empty disk. Changing the line in the Secret afterwards does not change the
  password inside the database, and the backend is then refused. How to change it properly is
  in [Later](#later-a-new-version-a-changed-setting-going-back).

**You should see:** `data-agent-stage-secrets` in the list of Secrets of `dice-stage`, with
eight entries.

To correct one of the other seven values later: delete the Secret, create it again from this
text with the **same** database password, and restart the pods. Editing a Secret in place shows
the base64 form, which is easy to get wrong.

### C2. Create the Argo CD Application

In Argo CD:

1. Open "Applications" and press `+ NEW APP`.
2. Press `EDIT AS YAML` at the top right.
3. Replace everything in the box with the content of `deploy/argocd/applications/data-agent-stage.yaml`. It
   is the text below, with your repo address from B1 in the `repoURL` line instead of
   `YOUR-ORG`.
4. Press `SAVE`, then `CREATE`.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: data-agent-stage
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: dice
  source:
    repoURL: https://github.sec.samsung.net/YOUR-ORG/cosmo-data-agent-backend.git
    targetRevision: main
    path: deploy/argocd/charts/data-agent
    helm:
      releaseName: data-agent
      valueFiles:
        - ../../environments/stage/data-agent.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: dice-stage
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
```

It has the same shape as the defect agent's stage Application. Different are the repo, the
name, the chart path, the release name and the values file. Unlike that one, it has no
automatic sync.

**You should see:** a new tile `data-agent-stage` with `Missing` and `OutOfSync`. That is
correct. Nothing is running yet: creating the Application only tells Argo CD where to look.

Click the tile. The picture shows twelve objects that Argo CD *would* create: five Deployments
(the four programs and Postgres), five Services, one disk claim (`PersistentVolumeClaim`) and
one `VirtualService`. The `DIFF` button (`APP DIFF` in older versions) shows their full text.
This is the moment where real Helm reads my templates for the first time. If something in them
is wrong, the tile shows an error here, and nothing has been changed.

### C3. Sync

Press `SYNC`, leave everything as offered, press `SYNCHRONIZE`.

**You should see**, within about three minutes:

- The tile turns to `Synced` and `Healthy`.
- The disk claim `data-agent-postgres-data` is green. It has received its disk.
- Under each of the five Deployments there is one pod, green, with `2/2` (the program and the
  Istio sidecar). `1/1` is fine too. It means this namespace adds no sidecar.
- The first start takes longer than later ones, because the machine has to download the images.

**The backend pod may restart two or three times in the first minutes. That is normal.** It
starts faster than Postgres, finds no database yet, stops, and is started again until Postgres
is up. Wait three minutes before you call it a problem.

Then look at two logs. Click the pod under `data-agent-postgres`, tab `LOGS`, container
`postgres`.

**You should see** this line near the end:

```
database system is ready to accept connections
```

Click the pod under `data-agent-backend`, tab `LOGS`, container `backend`.

**You should see** these three lines among others:

```
Starting DICE Data Agent Backend
Session run locks were reset to idle state: session table is ready
User tables are ready: user_accounts, user_access_log, user_admins
```

The backend has created its tables in the new, empty database. If a pod stays red or yellow,
go to [If something goes wrong](#if-something-goes-wrong).

### C4. First look in the browser

1. Open `https://stage.gtrai.sec.samsung.net/data-agent/backend/health`.
   **You should see:**
   `{"server_status":"healthy","postgresql_db_status":"healthy","object_storage_status":"healthy"}`.
   This one line proves the gateway, the frontend pod, the backend pod, the new database with
   its password, and the object storage keys.
2. Open `https://stage.gtrai.sec.samsung.net/data-agent`.
   **You should see:** the stage login (Check 4), and after it the data agent page saying
   "Waiting for approval", with your login ID. That is correct. The database is new, so it has
   no admin yet.

### C5. Make yourself the first admin on stage

The database is inside the cluster, so this is done from inside its pod.

Kubernetes Dashboard, namespace `dice-stage`, "Pods", click the pod whose name starts with
`data-agent-postgres`, press "Exec into pod" at the top right, and choose the container
`postgres`. Type this as one line, with your login ID in lower case in place of
`your.loginid`, exactly as the "Waiting for approval" screen shows it:

```sh
psql -U postgres -d data_agent -c "INSERT INTO user_admins (user_id, added_by) VALUES ('your.loginid', 'bootstrap') ON CONFLICT (user_id) DO NOTHING; SELECT user_id, added_by FROM user_admins;"
```

**You should see:** a small table with one row: your login ID and `bootstrap`. No password is
asked, because the command runs inside the database's own pod.

If it answers that the table `user_admins` does not exist, the backend has not started yet
(C3).

Back in the browser, press "Check again".

**You should see:** the data agent.

### C6. Test on stage

| # | Do this | You should see | What it proves |
|---|---|---|---|
| 1 | Ask a short question | An answer | The backend reaches the language model with the keys from the Secret |
| 2 | Look at the chat list after the first answer | The chat has a title | The title model and its keys |
| 3 | Ask something that needs MongoDB, the way you tested on the server | A real answer, not a tool error | Backend, MongoDB MCP pod, MongoDB |
| 4 | Ask something that needs Milvus, for example a search with an image | A real answer | Backend, Milvus MCP pod, Milvus, feature extractor |
| 5 | Ask a question with an image, then reload the page | The image is shown again | Object storage, in both directions |
| 6 | Ask the longest realistic question you have | The answer arrives, however long it takes | Nothing on the way cuts long requests |
| 7 | Open the admin page, then the access log | Your visits, with the address of your PC | See the note below |
| 8 | Ask a colleague who is on the stage allow list to open the address | "Waiting for approval" for them, and they appear in your waiting list | The approval flow |
| 9 | In Argo CD, click the three dots on the Deployment `data-agent-backend`, "Restart". Wait for green, then reload the page | Your chats are still there | Chats are in the database, not in the backend pod |
| 10 | The same "Restart" on the Deployment `data-agent-postgres`. Wait until the Postgres pod and the backend pod are green again, then reload the page | Your chats are still there, and you are still an admin | **The disk works.** The database survives the loss of its pod |

Row 10 is the most important one in this table. A database that forgets everything when its
pod is replaced would look fine in every other row. Do not go on to production before row 10
has passed.

Note for row 7. If the access log shows `127.0.0.6` or an address that is not your PC's, the
rest still works. Tell me what it shows. It concerns one setting, `FORWARDED_ALLOW_IPS`, which
I could only set from Istio's documentation.

When rows 1 to 6 and row 10 pass, the four tags in the stage values file are a tested version,
and production can get exactly these.

---

## Part D: production

D1 to D5 interrupt nobody. The switch is D6.

**Production starts with an empty database.** It does not use the Postgres on
`10.240.35.180`. Know what that means before you go on:

- **Accounts and approvals start again.** After the switch, everyone except you sees "Waiting
  for approval" once, and you approve them on the admin page. You make yourself the first
  admin in D5.
- **The chats people have today are not shown after the switch.** They are not deleted. They
  stay in the Postgres on `10.240.35.180`, untouched.

If people should keep their chats and approvals, the data can be copied into the new database
before the switch. That is not part of this guide. Tell me before D6 if you want it, together
with the Postgres version on the server, which this prints:

```bash
sudo docker exec data_agent_backend python -c "import asyncio; from data_agent.infra import PostgreSQLClient; print(asyncio.run(PostgreSQLClient().fetch_one('SELECT version()')))"
```

Tell people the time of D6 beforehand, and what the two points above mean for them. An answer
that is being written at that moment is cut.

### D1. Create the production Secret

Invent a second password, for the production database. Do not reuse the stage one.

```bash
openssl rand -hex 24
```

Kubernetes Dashboard, namespace selector on `dice`, `+`, "Create from input":

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: data-agent-prod-secrets
  namespace: dice
type: Opaque
stringData:
  postgres-password: "PASTE_NEW_DATABASE_PASSWORD"
  service-jwt-secret: "PASTE_PRODUCTION_SIGNING_SECRET"
  s3-access-key: "PASTE_OBJECT_STORAGE_ACCESS_KEY"
  s3-secret-key: "PASTE_OBJECT_STORAGE_SECRET_KEY"
  root-model-client-key: "PASTE_ROOT_MODEL_CLIENT_KEY"
  root-model-pass-key: "PASTE_ROOT_MODEL_PASS_KEY"
  title-model-client-key: "PASTE_TITLE_MODEL_CLIENT_KEY"
  title-model-pass-key: "PASTE_TITLE_MODEL_PASS_KEY"
```

Six values are the same as in C1. Two differ:

| Line | Copy it from |
|---|---|
| `postgres-password` | The second password you just invented |
| `service-jwt-secret` | The backend `config.yaml` on the server, `auth.service_jwt_secret`. It is the same text as key `service-jwt` of Secret `dice-runtime` in namespace `dice`: the short phrase of 22 characters |

**You should see:** `data-agent-prod-secrets` in the Secrets of `dice`, with eight entries.

As on stage, the database password is fixed at the first start. Do not change that line later.

### D2. Give production the tested tags

This is a change on branch `main` (the rule at the start of
[Part B](#part-b-put-the-deployment-files-on-branch-main)). On the backend repo's web page,
select branch `main`, open `deploy/argocd/environments/production/data-agent.yaml` and press the pencil.

1. Copy the four tags from `deploy/argocd/environments/stage/data-agent.yaml` into the four `tag: ""` lines.
2. Check that the last block still says `enabled: false` under `virtualService:`.

Press "Commit changes". As the message write `data-agent: production tags, forwarding still off`.

### D3. Create the production Application

Argo CD, `+ NEW APP`, `EDIT AS YAML`, paste the content of
`deploy/argocd/applications/data-agent-prod.yaml`, `SAVE`, `CREATE`. It is the text below, with your repo
address in the `repoURL` line:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: data-agent-prod
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: dice
  source:
    repoURL: https://github.sec.samsung.net/YOUR-ORG/cosmo-data-agent-backend.git
    targetRevision: main
    path: deploy/argocd/charts/data-agent
    helm:
      releaseName: data-agent
      valueFiles:
        - ../../environments/production/data-agent.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: dice
  syncPolicy:
    syncOptions:
      - CreateNamespace=false
```

**You should see:** a tile `data-agent-prod`, `Missing` and `OutOfSync`, and inside it eleven
objects: five Deployments, five Services and one disk claim. No `VirtualService`, because
forwarding is off.

### D4. Sync, with forwarding still off

Press `SYNC`, then `SYNCHRONIZE`.

**You should see:** `Synced` and `Healthy`, the disk claim green, five green pods, and in the
two logs the same lines as in C3. The backend may restart two or three times at the beginning,
as on stage.

People still use the old server. The forwarding rule made by hand is untouched and still points
there. The new pods have their own database, so they do not disturb the old backend in any
way.

### D5. Check the new pods and make yourself admin

There is no web address for these pods yet, so both steps are made from inside.

**The check.** Kubernetes Dashboard, namespace `dice`, "Pods", click the pod whose name starts
with `data-agent-frontend`, press "Exec into pod" at the top right, choose the container
`frontend`, and type:

```sh
wget -qO- http://localhost:13080/data-agent/backend/health
```

**You should see:**
`{"server_status":"healthy","postgresql_db_status":"healthy","object_storage_status":"healthy"}`.

This proves that the production frontend pod reaches the production backend pod, and that the
backend reaches the new database and the object storage with the production Secret.

**The first admin.** Same Dashboard, namespace `dice`, the pod whose name starts with
`data-agent-postgres`, "Exec into pod", container `postgres`. One line, with your login ID in
lower case, as Samsung SSO knows it:

```sh
psql -U postgres -d data_agent -c "INSERT INTO user_admins (user_id, added_by) VALUES ('your.loginid', 'bootstrap') ON CONFLICT (user_id) DO NOTHING; SELECT user_id, added_by FROM user_admins;"
```

**You should see:** a small table with one row: your login ID and `bootstrap`.

Make sure you are in namespace `dice` and not in `dice-stage`. Both have a pod with this name.

### D6. The switch

1. On branch `main`, in `deploy/argocd/environments/production/data-agent.yaml`, change the one line under
   `virtualService:` from `enabled: false` to `enabled: true`. Do it on the repo's web page
   with the pencil, as in D2. As the commit message write
   `data-agent: send /data-agent to the cluster`.
2. In Argo CD, open `data-agent-prod` and press `REFRESH`.
   **You should see:** the app becomes `OutOfSync`, and one more object appears: a
   `VirtualService` named `data-agent`. Argo CD has found the rule you made by hand under that
   name and sees that it differs from Git.
3. Press `DIFF`.
   **You should see:** the old destination `data-agent.external.local` on one side and the new
   destination `data-agent-frontend.dice.svc.cluster.local` on the other. Lines with labels
   that Argo CD adds for itself may differ too. That is normal. If the two sides differ in the
   host name `dice.gtrai.sec.samsung.net` or in the path `/data-agent`, stop and tell me.
4. Press `SYNC`, then `SYNCHRONIZE`.

From this second, `https://dice.gtrai.sec.samsung.net/data-agent` is served by the cluster.

### D7. Test production

| # | Do this | You should see |
|---|---|---|
| 1 | Open `https://dice.gtrai.sec.samsung.net/data-agent/backend/health` | Three times `healthy` |
| 2 | Open `https://dice.gtrai.sec.samsung.net/data-agent` | The app, after Samsung SSO or a silent login. No "Waiting for approval" for you, because of D5 |
| 3 | Look at the chat list | Empty. The database is new |
| 4 | Ask a question, and one with an image. Reload | Answers, as on stage, and the chat is still there after the reload |
| 5 | Open the admin page | Yourself as admin. Colleagues appear in the waiting list as they open the address. Approve them |
| 6 | On the server: `sudo docker logs --since 5m data_agent_backend` | No new request lines after the switch. The old backend is idle |

Row 6 is the proof that people are served by the cluster and not by the server any more.

If "Waiting for approval" shows for yourself in row 2, the ID in D5 is not spelled the way the
screen shows it. Repeat the D5 line with the spelling from the screen.

### D8. Afterwards

- **Leave the four old containers and the Postgres on the server running for a few days.**
  Together they are the way back, and that Postgres holds the old chats.
- **Leave the `ServiceEntry` `data-agent-server` in namespace `dice` in place** for the same
  days. On its own it forwards nothing. Going back needs it.
- When you are sure, stop the four old containers on the server (`sudo docker stop` with the
  four names from `sudo docker ps`) and delete the `ServiceEntry` `data-agent-server` in the
  Dashboard.
- **Milvus on the server must keep running.** The Milvus MCP pod uses it.
- The Postgres on the server is no longer needed by anything in the cluster. Keep it for as
  long as the old chats matter.

### Going back, if production does not work after the switch

The old containers and their database are still running, so going back only means pointing the
rule at the server again.

1. Kubernetes Dashboard, namespace `dice`: delete the `VirtualService` named `data-agent`.
2. `+`, "Create from input": paste the **lower part** of `deploy/prod/routing.yaml` from the
   backend repo, the part below the `---` line that starts with `# Sends the /data-agent
   paths`. Press "Upload".
3. On branch `main`, set `enabled: false` again under `virtualService:` in the production
   values file. This keeps a later Sync from switching again by accident.

After step 2 people are on the server again, with their old chats and their old approvals.
What they wrote in the cluster in between stays in the cluster's database and is not visible
on the server. Argo CD shows `data-agent-prod` as `OutOfSync` until step 3 is done and you
pressed `REFRESH`. Do not press `SYNC` in between.

---

## Later: a new version, a changed setting, going back

Pushing code does not deploy anything. A new version reaches the cluster only through the
steps below. Every change to a values file is made on branch `main` of the backend repo. The
rule and the easiest way (the pencil on the repo's web page) are at the start of
[Part B](#part-b-put-the-deployment-files-on-branch-main).

### A new version of one program

1. Build and push that image (the matching step of Part A). You get a new tag.
2. On branch `main`, put the tag into `deploy/argocd/environments/stage/data-agent.yaml`.
3. Argo CD, `data-agent-stage`: `REFRESH`, look at `DIFF` (only the image line should differ),
   `SYNC`.
4. Test on stage.
5. On branch `main`, put the same tag into `deploy/argocd/environments/production/data-agent.yaml`.
6. Argo CD, `data-agent-prod`: `REFRESH`, `DIFF`, `SYNC`.

This is the same for all four programs. A new frontend image also gets its tag written into
the backend repo, because that is where the values files are.

Only the pod whose tag changed is replaced. A new backend interrupts running answers for about
a minute. A new frontend does not.

### A changed setting

Change the line in the values file on branch `main`, then `REFRESH` and `SYNC`. The pod
restarts with the new value.

### A changed key

For every line of the Secret except the database password: delete the Secret, create it again
with the new value (C1 or D1), and **put the same database password in again**. Then restart
the pods that use it: in Argo CD, three dots on the Deployment, "Restart". The backend and the
Milvus MCP server read these keys. A pod reads the Secret only when it starts, so without the
restart nothing changes.

### A changed database password

The database keeps its password inside its own data, so there are two places to change, in
this order and without a pause in between:

1. In the Postgres pod ("Exec into pod", container `postgres`), with a new password that
   contains no single quote:

   ```sh
   psql -U postgres -d data_agent -c "ALTER USER postgres PASSWORD 'the-new-password';"
   ```

   **You should see:** `ALTER ROLE`.
2. Delete the Secret and create it again with the new password in the `postgres-password`
   line.
3. Restart the backend: Argo CD, three dots on the Deployment `data-agent-backend`, "Restart".

Step 1 works without knowing the old password. That also makes it the way out if the password
in the Secret and the one in the database ever disagree.

### Going back to the previous version

Put the previous tag back into the values file on branch `main`, then `REFRESH` and `SYNC`.
The old image is still in the registry, which is why tags are never reused.

### Removing stage completely

Argo CD, `data-agent-stage`, `DELETE`. Everything the Application created is removed, with one
exception made on purpose: the disk claim `data-agent-postgres-data`, which holds the stage
data. The Secret `data-agent-stage-secrets` stays too, because you made it by hand.

To remove those as well, delete them in the Kubernetes Dashboard, namespace `dice-stage`:
"Persistent Volume Claims" and "Secrets". Deleting the claim deletes the stage data for good.

If you create the Application again without deleting the claim, stage comes back with its old
data, and the database still has its old password. A new Secret then needs that old password.

---

## If something goes wrong

Where to look first: in Argo CD click the red or yellow object. The tab `EVENTS` says why a pod
does not start. The tab `LOGS` says what the program itself complained about.

| What you see | What it means | What to do |
|---|---|---|
| The tile shows an error with `backend.tag is required` (or `frontend.tag`, `mongodbMcp.tag`, `milvusMcp.tag`) | That `tag: ""` line in the values file is still empty | Fill it in on branch `main` (B1 or D2), then `REFRESH` |
| The tile shows an error about a line and column of a template | A mistake in one of my templates that my own check did not catch | Send me the full message. Nothing was changed in the cluster |
| Creating the Application answers that the repository is "not permitted in project" | Project `dice` does not accept the backend repo yet, or the address is spelled differently there | B4. The address has to be written exactly as in the `repoURL` line |
| Creating the Application answers that the destination is "not permitted in project" | Project `dice` allows less than I concluded from the defect agent | Send me the message |
| The tile shows an error with `authentication required`, `repository not found` or `not accessible` | Argo CD cannot read the backend repo | B3. If it worked before, the access token has run out: connect the repo again with a new token |
| The tile shows an error that the path `deploy/argocd/charts/data-agent` or the values file does not exist | The folder is not on branch `main`, or the sub-folders were not kept when copying | Look at the repo's web page with branch `main` selected and compare with the folder picture in B2 |
| You changed a tag, but after `REFRESH` Argo CD still says `Synced` and `DIFF` is empty | The change is on another branch than `main` | Look at the file on the repo's web page with branch `main` selected. Make the change there |
| A merge into `main` complains about a file under `deploy/argocd/` | The file was also changed on the working branch | Keep the version of `main`. Change these files on `main` only |
| Pod: `ImagePullBackOff` or `ErrImagePull` | The cluster cannot download the image | Compare the tag in the values file with A6, letter by letter. If it is right, the push did not happen, or `regcred` is missing in that namespace |
| Pod: `CreateContainerConfigError` | The Secret is missing, has another name, or lacks a key. `EVENTS` names it | Create or correct the Secret (C1, D1). The pod starts by itself within a minute |
| Backend pod: `CrashLoopBackOff`, log ends with `ValidationError` and `Field required` | A setting is missing. The log names it, for example `object_storage` | Add the missing line to `backend.env` in the values file |
| Backend pod restarts two or three times right after the first Sync, then turns green | It started before Postgres was up | Nothing. This is normal |
| Backend pod keeps restarting after five minutes. Log: `Connection refused`, or a name that cannot be found, for `data-agent-postgres` | Postgres is not running | Look at the Postgres pod and the disk claim, and at the next three rows |
| Backend pod keeps restarting. Log: `password authentication failed for user "postgres"` | The password in the Secret is not the one the database was started with. Either the Secret was changed after the first start, or a new Secret met an old disk | See "A changed database password". Run its step 1 with the password that is in the Secret now, then restart the backend. The two then agree again |
| The disk claim `data-agent-postgres-data` stays yellow, and the Postgres pod stays `Pending` | The cluster has no kind of disk called `nfs-csi`, or it cannot hand one out | Check 7, step 1. `EVENTS` on the claim names the reason. The name is one line, `postgres.persistence.storageClass`, which you can set in the values file |
| Postgres pod: `CrashLoopBackOff`. Log mentions `chown`, `Permission denied` or `Operation not permitted` | The disk does not let Postgres set up its folder | Send me the log lines. Nothing is lost, the database was never created |
| Postgres pod log: `superuser password is not specified` | The `postgres-password` line of the Secret is empty | Correct the Secret (C1, D1). The pod starts by itself |
| After restarting the Postgres pod, the chats are gone (C6, row 10) | The data is not on the disk | Stop here and do not go on to production. Tell me what Argo CD shows for the disk claim |
| Pod: `Pending`, `EVENTS` mentions `Insufficient` or `quota` | The namespace does not have that much free | Lower `resources.requests` for that program in the values file |
| Pod restarts now and then, last state `OOMKilled` | It used more memory than its limit | Raise `resources.limits.memory` for that program in the values file |
| Frontend pod never becomes ready, `EVENTS`: the check got 404 | The image was built for another base path | Build the frontend again without `--build-arg` (A5) |
| Sync fails and the message names `headers` in the `VirtualService` | This cluster refuses the cookie removal | Add `removeCookies: false` under `virtualService:` in the values file, push, sync |
| Browser: 503, "no healthy upstream" | The rule exists, but the frontend pod is not ready | Look at the frontend pod in Argo CD |
| Browser: 404 on `/data-agent` | The rule does not exist, or another rule catches the path | Check that the `VirtualService` is green in Argo CD. Then repeat Check 3, step 2 |
| "Could not check your login" | The page reached the login service, but the backend did not answer `/auth/me` | Open `.../data-agent/backend/health`. No reply: look at the backend pod. Reply fine: look at the backend log |
| After login, "You are not logged in" again and again. Backend log: `Rejected service token: InvalidSignatureError` | The signing secret in the Secret is wrong: the production one on stage or the other way round, or the base64 text | Correct `service-jwt-secret` (see "A changed key or password") |
| Stage login answers `{"error":"forbidden"}` | Your ID is not on the simulator's allow list | Check 4 |
| After the stage login you land on the stage home page | The stage login service did not accept the return address | Open the data agent address again. You are logged in by then |
| The agent answers, but tool calls fail | An MCP pod cannot reach MongoDB, Milvus or the feature extractor | Read the log of that MCP pod. Then Check 5. If Check 5 says `True`, tell me: the cluster then needs a `ServiceEntry` for that address, like the defect agent has for its proxy |
| A question always fails after the same time, for example 5 minutes | Something on the way cuts long requests | Note the time and tell me |
| The access log shows `127.0.0.6` or a `10.` address for every visit | The setting `FORWARDED_ALLOW_IPS` does not fit this cluster | Tell me what it shows. Everything else is unaffected |
| `git clone` in Part A: `detected dubious ownership` | The code folder belongs to another Linux user | Run the one `git config` line that the message itself prints, then repeat |

---

## What I could not check from here

This PC has no access to the cluster, the registry, the company GitHub or the server. These
points are conclusions from your files, not observations.

1. **Real Helm has not read the chart.** This PC has no Helm, and running a downloaded copy was
   not permitted. I rendered the templates with a small script of my own that understands the
   constructs this chart uses. All twelve objects came out as valid YAML with the expected
   content, for stage and for production. Argo CD uses real Helm in C2, before anything is
   created.
2. **Your right to push to the registry** (Check 1), **to change branch `main` of the backend
   repo, and to change Argo CD's settings** (Check 2). I also have not seen how branches are
   used in the company's backend repo. I assumed that a branch `main` exists there.
3. **Project `dice`.** That it allows the two namespaces I conclude from `defect-stage` and
   `defect-prod`. Its list of accepted repos I have not seen. I also do not know whether the
   project itself is kept in Git somewhere. If it is, the line added by hand in B4 can
   disappear again. B4 says how to notice.
4. **That pods may connect to the outside addresses:** Milvus, MongoDB, the feature extractor,
   the model service and the object storage. I conclude it from the defect agent, whose backend
   reaches the model service directly, and from the DICE chart, which has no special objects
   for its outside connections.
5. **That Postgres runs on this cluster's disks the way I set it up.** I took the image and the
   kind of disk from the defect agent's Temporal database, and the two protection markings on
   the disk claim from DICE's database. Of the first I have seen the settings only, not the
   templates. Row 10 of the stage test (C6) is the proof.
6. **The "Exec into pod" button of your Dashboard** (Check 7), which C5 and D5 need.
7. **How login works on stage DICE.** The simulator is in the login service's code. Whether it
   is switched on for stage, and who is on its list, is a setting I have not seen (Check 4).
8. **That pods get an Istio sidecar.** The image lists of `defect-prod` and `defect-stage`
   contain the sidecar image, so I expect it. Two settings depend on it: `FORWARDED_ALLOW_IPS`
   and the cookie removal.
9. **Folder paths and container names on the server.** Taken from the run scripts. A1 and
   Check 6 show the real ones.
10. **The values in the two values files.** Taken from the `config.yaml` files on this PC
    (Check 6).
11. **The memory, CPU and disk numbers.** Starting values, chosen by comparing with the defect
    agent and DICE. The Dashboard shows the real use per pod after a few days. The disk is
    10 GB.
12. **Whether production should use other MongoDB or Milvus addresses than today.** I assumed
    not, because today's containers already serve the production address with these.

What I did check on this PC:

- The chart, with my own script, for stage and for production.
- The settings loading of all three Python programs from a one-line file plus environment
  variables.
- The backend's new password setting. The test suite passes (187 tests; one other test fails
  as it did before this change). Against a real local Postgres that demands a password, the
  backend was refused without the password and with a wrong one, and with the right one it
  connected and created all its tables. The password in that test contained `@`, `:`, `/`, a
  space and `%`.
- The database command lines of C5, D5 and "A changed database password", with a real `psql`,
  each one twice.

---

## What is still open after this

1. **The database has no backup.** It is one pod with one disk. A mistake in the data, a
   deleted disk claim or a broken disk cannot be undone. A regular dump of the database to the
   object storage is the first thing I would add. Until then, do not delete the disk claim
   `data-agent-postgres-data`, and take a dump by hand before anything risky.
2. **The old data on `10.240.35.180`.** The chats and approvals from before the switch stay
   there. If they are wanted in the new database, they have to be copied once (Part D says what
   I need for that). If they are not wanted, that Postgres can be stopped once the old
   containers are stopped.
3. **Argo CD may be reading the backend repo with your personal token** (B3, if the first try
   without a key failed). When that token runs out, Argo CD can no longer read the repo. The
   pods keep running, but nothing can be deployed until the repo is connected again. A token
   of a shared team account is the lasting answer.
4. **The two Applications exist in Argo CD because you pasted them.** Their text is kept in the
   backend repo under `deploy/argocd/applications/`, so they can be pasted again. The defect
   agent's Applications are created from yet another repo, `argocd-configuration-repository`,
   which I have not seen. Whether the data agent's belong there too is a question for the
   person who looks after that repo.
5. **Building by hand.** The defect agent's workflow `Publish Backend` builds, pushes and writes
   the tag into the stage values file. The same can be made for the four data agent repos.
   Two things need care then, because the values files are in a code repo. The step that
   writes a tag into the backend repo must not start a new backend build, and the builds of
   the other three repos need permission to write into the backend repo.
6. **Splitting later.** If one of the MCP servers gets a life of its own, its part of the chart
   can move into its own repo with its own Application. Nothing in this setup prevents that.
7. **Log files.** The Python programs write log files inside their pod. They are lost when the
   pod is replaced. The same lines also go to the pod's log, which is what Argo CD and the
   Dashboard show, and the backend's `/logs` download gives the files of the current pod only.
   If the files have to survive, the pods need a volume.
8. **The old containers and open ports on `10.240.35.180`.** After D8 only Milvus needs to be
   reachable there.
9. **The production signing secret is still the short guessable phrase.** See
   `docs/data-agent-auth-implementation-2026-11-21.md`, Part 6, item 1. The data agent in the
   cluster trusts it exactly as the one on the server did.

---

## Appendix: every file

The same files are in this repo under `deploy/argocd/`. If a file here and a file there ever
differ, the one in `deploy/argocd/` is the right one.

### `deploy/argocd/charts/data-agent/Chart.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
apiVersion: v2
name: data-agent
description: COSMO Data Agent - backend (FastAPI), frontend (Next.js), MongoDB MCP server and Milvus MCP server
type: application
version: 0.1.0
appVersion: "1.0.0"
```

### `deploy/argocd/charts/data-agent/values.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). The defaults. You normally do not edit this file.

```yaml
# Default values for the data-agent chart.
#
# Environment values live in deploy/argocd/environments/<env>/data-agent.yaml
# in this repository and are referenced by the Argo CD Applications
# data-agent-stage and data-agent-prod. A value written there replaces the
# value written here.

namePrefix: data-agent

imagePullPolicy: IfNotPresent
# Lets the cluster download images from dice-docker-local.bart.sec.samsung.net.
imagePullSecrets:
  - regcred

# Kubernetes Secret that holds the keys and passwords. It is created by hand
# in the namespace, it is never in git, and it must exist before the first
# sync. The key names on the right are the names inside that Secret.
secret:
  name: data-agent-secrets
  keys:
    serviceJwtSecret: service-jwt-secret
    s3AccessKey: s3-access-key
    s3SecretKey: s3-secret-key
    rootModelClientKey: root-model-client-key
    rootModelPassKey: root-model-pass-key
    titleModelClientKey: title-model-client-key
    titleModelPassKey: title-model-pass-key
    postgresPassword: postgres-password

# The data agent's own Postgres. One per environment.
postgres:
  image: docker-remote.bart.sec.samsung.net/postgres
  # The defect agent runs this same image on the same kind of disk in this
  # cluster.
  tag: "16-alpine"
  port: 5432
  # Name of the database, and of the user the backend connects as. Both are
  # created, with the password from the Secret, when Postgres starts on an
  # empty disk. Changing these lines later does not change an existing
  # database.
  database: data_agent
  user: postgres
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 1Gi
  # The disk that holds the data. Argo CD never deletes it.
  persistence:
    storageClass: nfs-csi
    size: 10Gi
    accessModes:
      - ReadWriteOnce

backend:
  image: dice-docker-local.bart.sec.samsung.net/cosmo-data-agent-backend
  # REQUIRED: immutable tag (date-commit). Never use a moving tag such as "latest".
  # The image has to be built from code that knows the database password
  # setting (POSTGRESQL_DB_PASSWORD in common/config.py, added 2026-11-26).
  tag: ""
  # Keep one replica and Recreate. When the backend starts it marks every
  # session as "not running" (data_agent/infra/session_lock.py), so a second
  # copy starting next to a working one would release the first one's locks.
  replicas: 1
  strategy: Recreate
  port: 18080
  resources:
    requests:
      cpu: 250m
      memory: 1Gi
    limits:
      cpu: "2"
      memory: 4Gi
  # Plain settings. Each line becomes an environment variable of the backend
  # container (the names are the ones in common/config.py). Write every value
  # in quotes. An empty value is left out.
  #
  # Do not add these here, the chart sets them itself: SERVER_PORT,
  # MONGODB_MCP_HOST, MONGODB_MCP_PORT, MILVUS_MCP_HOST, MILVUS_MCP_PORT,
  # every POSTGRESQL_DB_... value (they point at the Postgres of this same
  # release), and the values that come from the Secret.
  env:
    OBJECT_STORAGE_BUCKET: ""
    OBJECT_STORAGE_ENDPOINT: ""
    ROOT_MODEL_OPENAPI_MODEL: ""
    ROOT_MODEL_OPENAPI_ENDPOINT: ""
    ROOT_MODEL_OPENAPI_MODEL_ID: ""
    TITLE_MODEL_OPENAPI_MODEL: ""
    TITLE_MODEL_OPENAPI_ENDPOINT: ""
    TITLE_MODEL_OPENAPI_MODEL_ID: ""
    AUTH_SERVICE_JWT_ISSUER: "web-auth"
    AUTH_SERVICE_JWT_AUDIENCE: "dice-backend"
    # Lets the backend record the visitor's own address in the access log.
    # 127.0.0.6 is the address the Istio sidecar hands requests over from.
    FORWARDED_ALLOW_IPS: "127.0.0.6"

frontend:
  image: dice-docker-local.bart.sec.samsung.net/cosmo-data-agent-frontend
  # REQUIRED: immutable tag.
  tag: ""
  replicas: 1
  port: 13080
  # The page the health check asks for. It starts with the base path the image
  # was built with (NEXT_PUBLIC_BASE_PATH, /data-agent by default).
  healthPath: /data-agent/chat/new
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 1Gi

mongodbMcp:
  image: dice-docker-local.bart.sec.samsung.net/cosmo-mongodb-mcp-server
  # REQUIRED: immutable tag.
  tag: ""
  # One replica: the backend keeps an open MCP session with this one process.
  replicas: 1
  port: 10420
  resources:
    requests:
      cpu: 100m
      memory: 256Mi
    limits:
      cpu: "1"
      memory: 1Gi
  # Plain settings (names from the MCP server's common/config.py).
  # SERVER_PORT is set by the chart.
  env:
    MONGODB_HOST: ""
    MONGODB_PORT: "27017"
    MONGODB_DB_NAME: ""

milvusMcp:
  image: dice-docker-local.bart.sec.samsung.net/cosmo-milvus-mcp-server
  # REQUIRED: immutable tag.
  tag: ""
  # One replica: the backend keeps an open MCP session with this one process.
  replicas: 1
  port: 10422
  resources:
    requests:
      cpu: 250m
      memory: 512Mi
    limits:
      cpu: "2"
      memory: 4Gi
  # Plain settings (names from the MCP server's common/config.py).
  # SERVER_PORT and the two object storage keys are set by the chart.
  env:
    MILVUS_HOST: ""
    MILVUS_PORT: "19530"
    MILVUS_DB_NAME: ""
    FEATURE_EXTRACTOR_HOST: ""
    FEATURE_EXTRACTOR_PORT: ""
    OBJECT_STORAGE_BUCKET: ""
    OBJECT_STORAGE_ENDPOINT: ""

virtualService:
  enabled: true
  name: data-agent
  hosts: []
  # platform-gateway (istio-system) serves *.gtrai.sec.samsung.net.
  gateways:
    - istio-system/platform-gateway
  # Must be equal to the base path the frontend image was built with.
  path: /data-agent
  # The DICE login cookie is only sent over https.
  redirectHttpToHttps: true
  # The data agent uses no cookies. Removing them keeps the DICE login cookie
  # out of the data agent containers and their logs.
  removeCookies: true
```

### `deploy/argocd/charts/data-agent/templates/backend.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
{{- $name := .Values.namePrefix -}}
{{- $ns := .Release.Namespace -}}
{{- $secret := .Values.secret -}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}-backend
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: backend
spec:
  replicas: {{ .Values.backend.replicas }}
  strategy:
    type: {{ .Values.backend.strategy }}
  selector:
    matchLabels:
      app.kubernetes.io/name: data-agent
      app.kubernetes.io/component: backend
  template:
    metadata:
      labels:
        app.kubernetes.io/name: data-agent
        app.kubernetes.io/component: backend
    spec:
      # No automatic <SERVICE>_PORT variables: they can collide with the
      # application's own setting names.
      enableServiceLinks: false
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ . }}
        {{- end }}
      containers:
        - name: backend
          image: "{{ .Values.backend.image }}:{{ required "backend.tag is required" .Values.backend.tag }}"
          imagePullPolicy: {{ .Values.imagePullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.backend.port }}
          env:
            - name: SERVER_PORT
              value: {{ .Values.backend.port | quote }}
            # The two MCP servers of this same release.
            - name: MONGODB_MCP_HOST
              value: {{ $name }}-mongodb-mcp.{{ $ns }}.svc.cluster.local
            - name: MONGODB_MCP_PORT
              value: {{ .Values.mongodbMcp.port | quote }}
            - name: MILVUS_MCP_HOST
              value: {{ $name }}-milvus-mcp.{{ $ns }}.svc.cluster.local
            - name: MILVUS_MCP_PORT
              value: {{ .Values.milvusMcp.port | quote }}
            # The Postgres of this same release.
            - name: POSTGRESQL_DB_HOST
              value: {{ $name }}-postgres.{{ $ns }}.svc.cluster.local
            - name: POSTGRESQL_DB_PORT
              value: {{ .Values.postgres.port | quote }}
            - name: POSTGRESQL_DB_NAME
              value: {{ .Values.postgres.database | quote }}
            - name: POSTGRESQL_DB_USER
              value: {{ .Values.postgres.user | quote }}
            - name: POSTGRESQL_DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.postgresPassword }}
            {{- range $k, $v := .Values.backend.env }}
            {{- if not (empty $v) }}
            - name: {{ $k }}
              value: {{ $v | toString | quote }}
            {{- end }}
            {{- end }}
            - name: AUTH_SERVICE_JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.serviceJwtSecret }}
            - name: OBJECT_STORAGE_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.s3AccessKey }}
            - name: OBJECT_STORAGE_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.s3SecretKey }}
            - name: ROOT_MODEL_OPENAPI_CLIENT_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.rootModelClientKey }}
            - name: ROOT_MODEL_OPENAPI_PASS_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.rootModelPassKey }}
            - name: TITLE_MODEL_OPENAPI_CLIENT_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.titleModelClientKey }}
            - name: TITLE_MODEL_OPENAPI_PASS_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.titleModelPassKey }}
          resources:
            {{- toYaml .Values.backend.resources | nindent 12 }}
          # "Is the port open" is the right question here: the backend opens
          # its port only after it has reached the database and created its
          # tables. GET /health is not used, because it asks the database and
          # the object storage on every call and writes log lines each time.
          # If Postgres is not up yet, the backend stops and is started again
          # until it is. A few restarts right after a first sync are normal.
          startupProbe:
            tcpSocket:
              port: http
            periodSeconds: 5
            failureThreshold: 60
          readinessProbe:
            tcpSocket:
              port: http
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: http
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}-backend
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: backend
spec:
  selector:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: backend
  ports:
    - name: http
      port: {{ .Values.backend.port }}
      targetPort: http
```

### `deploy/argocd/charts/data-agent/templates/frontend.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
{{- $name := .Values.namePrefix -}}
{{- $ns := .Release.Namespace -}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}-frontend
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: frontend
spec:
  replicas: {{ .Values.frontend.replicas }}
  selector:
    matchLabels:
      app.kubernetes.io/name: data-agent
      app.kubernetes.io/component: frontend
  template:
    metadata:
      labels:
        app.kubernetes.io/name: data-agent
        app.kubernetes.io/component: frontend
    spec:
      enableServiceLinks: false
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ . }}
        {{- end }}
      containers:
        - name: frontend
          image: "{{ .Values.frontend.image }}:{{ required "frontend.tag is required" .Values.frontend.tag }}"
          imagePullPolicy: {{ .Values.imagePullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.frontend.port }}
          env:
            # Next.js listens on the address in HOSTNAME. Kubernetes can set
            # HOSTNAME to the pod's name, so it is fixed here.
            - name: HOSTNAME
              value: "0.0.0.0"
            - name: PORT
              value: {{ .Values.frontend.port | quote }}
            # The backend of this same release. Read by the frontend server
            # only, never by the browser.
            - name: BACKEND_ORIGIN
              value: http://{{ $name }}-backend.{{ $ns }}.svc.cluster.local:{{ .Values.backend.port }}
          resources:
            {{- toYaml .Values.frontend.resources | nindent 12 }}
          # Asks for a real page. An image built without the right base path
          # answers 404 here and never becomes ready.
          startupProbe:
            httpGet:
              path: {{ .Values.frontend.healthPath }}
              port: http
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 30
          readinessProbe:
            httpGet:
              path: {{ .Values.frontend.healthPath }}
              port: http
            periodSeconds: 10
            timeoutSeconds: 5
          livenessProbe:
            httpGet:
              path: {{ .Values.frontend.healthPath }}
              port: http
            periodSeconds: 30
            timeoutSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}-frontend
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: frontend
spec:
  selector:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: frontend
  ports:
    - name: http
      port: {{ .Values.frontend.port }}
      targetPort: http
```

### `deploy/argocd/charts/data-agent/templates/mongodb-mcp.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
{{- $name := .Values.namePrefix -}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}-mongodb-mcp
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: mongodb-mcp
spec:
  replicas: {{ .Values.mongodbMcp.replicas }}
  selector:
    matchLabels:
      app.kubernetes.io/name: data-agent
      app.kubernetes.io/component: mongodb-mcp
  template:
    metadata:
      labels:
        app.kubernetes.io/name: data-agent
        app.kubernetes.io/component: mongodb-mcp
    spec:
      enableServiceLinks: false
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ . }}
        {{- end }}
      containers:
        - name: mongodb-mcp
          image: "{{ .Values.mongodbMcp.image }}:{{ required "mongodbMcp.tag is required" .Values.mongodbMcp.tag }}"
          imagePullPolicy: {{ .Values.imagePullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.mongodbMcp.port }}
          env:
            - name: SERVER_PORT
              value: {{ .Values.mongodbMcp.port | quote }}
            {{- range $k, $v := .Values.mongodbMcp.env }}
            {{- if not (empty $v) }}
            - name: {{ $k }}
              value: {{ $v | toString | quote }}
            {{- end }}
            {{- end }}
          resources:
            {{- toYaml .Values.mongodbMcp.resources | nindent 12 }}
          # The server's own GET /health also asks MongoDB. A pod must not
          # be taken out of service because the database is slow, so the
          # checks only ask whether the port is open.
          startupProbe:
            tcpSocket:
              port: http
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            tcpSocket:
              port: http
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: http
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}-mongodb-mcp
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: mongodb-mcp
spec:
  selector:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: mongodb-mcp
  ports:
    - name: http
      port: {{ .Values.mongodbMcp.port }}
      targetPort: http
```

### `deploy/argocd/charts/data-agent/templates/milvus-mcp.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
{{- $name := .Values.namePrefix -}}
{{- $secret := .Values.secret -}}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}-milvus-mcp
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: milvus-mcp
spec:
  replicas: {{ .Values.milvusMcp.replicas }}
  selector:
    matchLabels:
      app.kubernetes.io/name: data-agent
      app.kubernetes.io/component: milvus-mcp
  template:
    metadata:
      labels:
        app.kubernetes.io/name: data-agent
        app.kubernetes.io/component: milvus-mcp
    spec:
      enableServiceLinks: false
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ . }}
        {{- end }}
      containers:
        - name: milvus-mcp
          image: "{{ .Values.milvusMcp.image }}:{{ required "milvusMcp.tag is required" .Values.milvusMcp.tag }}"
          imagePullPolicy: {{ .Values.imagePullPolicy }}
          ports:
            - name: http
              containerPort: {{ .Values.milvusMcp.port }}
          env:
            - name: SERVER_PORT
              value: {{ .Values.milvusMcp.port | quote }}
            {{- range $k, $v := .Values.milvusMcp.env }}
            {{- if not (empty $v) }}
            - name: {{ $k }}
              value: {{ $v | toString | quote }}
            {{- end }}
            {{- end }}
            - name: OBJECT_STORAGE_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.s3AccessKey }}
            - name: OBJECT_STORAGE_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.s3SecretKey }}
          resources:
            {{- toYaml .Values.milvusMcp.resources | nindent 12 }}
          # The server's own GET /health also asks Milvus. A pod must not be
          # taken out of service because Milvus is slow, so the checks only
          # ask whether the port is open.
          startupProbe:
            tcpSocket:
              port: http
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:
            tcpSocket:
              port: http
            periodSeconds: 10
          livenessProbe:
            tcpSocket:
              port: http
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}-milvus-mcp
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: milvus-mcp
spec:
  selector:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: milvus-mcp
  ports:
    - name: http
      port: {{ .Values.milvusMcp.port }}
      targetPort: http
```

### `deploy/argocd/charts/data-agent/templates/postgres.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). The database and its disk.

```yaml
{{- $name := .Values.namePrefix -}}
{{- $secret := .Values.secret -}}
{{- $pg := .Values.postgres -}}
# The data agent's own Postgres: chats, accounts, admins, approvals.
# One database per environment. Stage and production never share one.
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ $name }}-postgres-data
  annotations:
    # The disk holds the data, so it must outlive everything else: Argo CD
    # never removes it, also not when the Application is deleted.
    helm.sh/resource-policy: keep
    argocd.argoproj.io/sync-options: Prune=false,Delete=false
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: postgres
spec:
  accessModes:
    {{- toYaml $pg.persistence.accessModes | nindent 4 }}
  storageClassName: {{ $pg.persistence.storageClass | quote }}
  resources:
    requests:
      storage: {{ $pg.persistence.size | quote }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ $name }}-postgres
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: postgres
spec:
  # Exactly one. Two Postgres processes must never open the same data folder.
  replicas: 1
  strategy:
    type: Recreate
  selector:
    matchLabels:
      app.kubernetes.io/name: data-agent
      app.kubernetes.io/component: postgres
  template:
    metadata:
      labels:
        app.kubernetes.io/name: data-agent
        app.kubernetes.io/component: postgres
    spec:
      enableServiceLinks: false
      imagePullSecrets:
        {{- range .Values.imagePullSecrets }}
        - name: {{ . }}
        {{- end }}
      containers:
        - name: postgres
          image: "{{ $pg.image }}:{{ $pg.tag }}"
          imagePullPolicy: {{ .Values.imagePullPolicy }}
          ports:
            - name: postgres
              containerPort: {{ $pg.port }}
          env:
            # User, database and password are created when Postgres starts
            # on an empty disk. On a disk that already holds a database
            # these three lines change nothing.
            - name: POSTGRES_USER
              value: {{ $pg.user | quote }}
            - name: POSTGRES_DB
              value: {{ $pg.database | quote }}
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: {{ $secret.name }}
                  key: {{ $secret.keys.postgresPassword }}
            - name: PGPORT
              value: {{ $pg.port | quote }}
            # A sub-folder of the disk, as the Postgres image asks for.
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            {{- toYaml $pg.resources | nindent 12 }}
          # Asks over the network address, not the local socket, so that
          # "ready" is only reported once other pods can really connect.
          startupProbe:
            exec:
              command: ["pg_isready", "-h", "127.0.0.1", "-U", {{ $pg.user | quote }}, "-d", {{ $pg.database | quote }}]
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 60
          readinessProbe:
            exec:
              command: ["pg_isready", "-h", "127.0.0.1", "-U", {{ $pg.user | quote }}, "-d", {{ $pg.database | quote }}]
            periodSeconds: 10
            timeoutSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-h", "127.0.0.1", "-U", {{ $pg.user | quote }}, "-d", {{ $pg.database | quote }}]
            periodSeconds: 30
            timeoutSeconds: 5
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: {{ $name }}-postgres-data
---
apiVersion: v1
kind: Service
metadata:
  name: {{ $name }}-postgres
  labels:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: postgres
spec:
  selector:
    app.kubernetes.io/name: data-agent
    app.kubernetes.io/component: postgres
  ports:
    - name: tcp-postgres
      port: {{ $pg.port }}
      targetPort: postgres
```

### `deploy/argocd/charts/data-agent/templates/virtualservice.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2).

```yaml
{{- if .Values.virtualService.enabled }}
{{- $vs := .Values.virtualService }}
# Forwarding rule:
#   {{ $vs.path }} and {{ $vs.path }}/...  ->  frontend, path unchanged
#
# The backend and the two MCP servers are not forwarded. The browser only
# talks to the frontend server, which passes backend calls on by itself.
# The login paths (/auth/...) are forwarded on the same host by the
# defect-studio rule, so they are not repeated here.
---
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {{ $vs.name }}
spec:
  hosts:
    {{- toYaml $vs.hosts | nindent 4 }}
  gateways:
    {{- toYaml $vs.gateways | nindent 4 }}
  http:
    {{- if $vs.redirectHttpToHttps }}
    # http -> https
    - match:
        - port: 80
          uri:
            prefix: {{ $vs.path }}
      redirect:
        scheme: https
        port: 443
        redirectCode: 308
    {{- end }}
    # Both spellings are forwarded and neither is redirected here: the
    # frontend itself redirects {{ $vs.path }}/ to {{ $vs.path }}, so a redirect in the
    # other direction at this point would loop forever.
    # No timeout is set: Istio leaves it off by default, so long answers
    # are not cut.
    - match:
        - uri:
            exact: {{ $vs.path }}
        - uri:
            prefix: {{ $vs.path }}/
      {{- if $vs.removeCookies }}
      headers:
        request:
          remove:
            - cookie
      {{- end }}
      route:
        - destination:
            host: {{ .Values.namePrefix }}-frontend.{{ .Release.Namespace }}.svc.cluster.local
            port:
              number: {{ .Values.frontend.port }}
{{- end }}
```

### `deploy/argocd/environments/stage/data-agent.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). Fill in the four tags (B1).

```yaml
# Stage values for the data-agent chart.
# Referenced by the data-agent-stage Argo CD Application.
# Address: https://stage.gtrai.sec.samsung.net/data-agent   Namespace: dice-stage
#
# No passwords or keys in this file. They are in the Kubernetes Secret named
# below, which is created by hand in dice-stage.
#
# The database is not set here. Stage gets its own Postgres from the chart
# (pod data-agent-postgres in dice-stage), and the chart points the backend
# at it.

namePrefix: data-agent

secret:
  # Must exist in dice-stage before the first sync (NOT in git).
  name: data-agent-stage-secrets

backend:
  # The tag printed when the image was pushed, for example "2026.11.26-7561e6b".
  tag: ""
  env:
    OBJECT_STORAGE_BUCKET: "cosmo-storage"
    OBJECT_STORAGE_ENDPOINT: "https://s3.ap-northeast-2.samsungspc.com"
    ROOT_MODEL_OPENAPI_MODEL: "openai/qwen/qwen3.8-flash-next"
    ROOT_MODEL_OPENAPI_ENDPOINT: "https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1"
    ROOT_MODEL_OPENAPI_MODEL_ID: "605"
    TITLE_MODEL_OPENAPI_MODEL: "openai/qwen/qwen3.8-flash-next"
    TITLE_MODEL_OPENAPI_ENDPOINT: "https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1"
    TITLE_MODEL_OPENAPI_MODEL_ID: "81"

frontend:
  tag: ""

mongodbMcp:
  tag: ""
  env:
    MONGODB_HOST: "dev.gtrai.sec.samsung.net"
    MONGODB_PORT: "27017"
    MONGODB_DB_NAME: "cosmoData"

milvusMcp:
  tag: ""
  env:
    MILVUS_HOST: "10.240.35.180"
    MILVUS_PORT: "19530"
    MILVUS_DB_NAME: "cosmoData"
    FEATURE_EXTRACTOR_HOST: "10.240.28.235"
    FEATURE_EXTRACTOR_PORT: "24502"
    OBJECT_STORAGE_BUCKET: "cosmo-storage"
    OBJECT_STORAGE_ENDPOINT: "https://s3.ap-northeast-2.samsungspc.com"

virtualService:
  enabled: true
  name: data-agent-stage
  hosts:
    - stage.gtrai.sec.samsung.net
  gateways:
    - istio-system/platform-gateway
  redirectHttpToHttps: true
```

### `deploy/argocd/environments/production/data-agent.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). Tags in D2, the switch in D6.

```yaml
# Production values for the data-agent chart.
# Referenced by the data-agent-prod Argo CD Application.
# Address: https://dice.gtrai.sec.samsung.net/data-agent   Namespace: dice
#
# No passwords or keys in this file. They are in the Kubernetes Secret named
# below, which is created by hand in dice.
#
# The database is not set here. Production gets its own Postgres from the
# chart (pod data-agent-postgres in dice), and the chart points the backend
# at it. It starts empty. The Postgres on 10.240.35.180 is not used.

namePrefix: data-agent

secret:
  # Must exist in dice before the first sync (NOT in git).
  name: data-agent-prod-secrets

backend:
  # Copy the four tags from the stage file (../stage/data-agent.yaml), and
  # only after that version passed the stage test.
  tag: ""
  env:
    OBJECT_STORAGE_BUCKET: "cosmo-storage"
    OBJECT_STORAGE_ENDPOINT: "https://s3.ap-northeast-2.samsungspc.com"
    ROOT_MODEL_OPENAPI_MODEL: "openai/qwen/qwen3.8-flash-next"
    ROOT_MODEL_OPENAPI_ENDPOINT: "https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1"
    ROOT_MODEL_OPENAPI_MODEL_ID: "605"
    TITLE_MODEL_OPENAPI_MODEL: "openai/qwen/qwen3.8-flash-next"
    TITLE_MODEL_OPENAPI_ENDPOINT: "https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1"
    TITLE_MODEL_OPENAPI_MODEL_ID: "81"

frontend:
  tag: ""

mongodbMcp:
  tag: ""
  env:
    MONGODB_HOST: "dev.gtrai.sec.samsung.net"
    MONGODB_PORT: "27017"
    MONGODB_DB_NAME: "cosmoData"

milvusMcp:
  tag: ""
  env:
    MILVUS_HOST: "10.240.35.180"
    MILVUS_PORT: "19530"
    MILVUS_DB_NAME: "cosmoData"
    FEATURE_EXTRACTOR_HOST: "10.240.28.235"
    FEATURE_EXTRACTOR_PORT: "24502"
    OBJECT_STORAGE_BUCKET: "cosmo-storage"
    OBJECT_STORAGE_ENDPOINT: "https://s3.ap-northeast-2.samsungspc.com"

virtualService:
  # false: the containers run, but nobody is sent to them. People keep
  # reaching the server 10.240.35.180 through the rule that was made by hand.
  # true: the switch. This rule replaces the hand-made one, which has the
  # same name on purpose, so the change happens in one step.
  enabled: false
  name: data-agent
  hosts:
    - dice.gtrai.sec.samsung.net
  gateways:
    - istio-system/platform-gateway
  redirectHttpToHttps: true
```

### `deploy/argocd/applications/data-agent-stage.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). Fill in the repo address (B1). Pasted into Argo CD in C2.

```yaml
# Argo CD Application for the data agent on stage.
# Pasted into Argo CD by hand (guide, step C2). Argo CD does not read this
# file from the repo; it is kept here so that the text is not lost.
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: data-agent-stage
  namespace: argocd
  finalizers:
    # Deleting this Application also deletes everything it created.
    - resources-finalizer.argocd.argoproj.io
spec:
  project: dice
  source:
    # The backend repo on the company GitHub. Replace YOUR-ORG with the owner.
    repoURL: https://github.sec.samsung.net/YOUR-ORG/cosmo-data-agent-backend.git
    # The one branch Argo CD reads. Deployment files count only on this branch.
    targetRevision: main
    path: deploy/argocd/charts/data-agent
    helm:
      releaseName: data-agent
      valueFiles:
        - ../../environments/stage/data-agent.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: dice-stage
  syncPolicy:
    # No "automated" block: syncing is by hand.
    syncOptions:
      - CreateNamespace=false
```

### `deploy/argocd/applications/data-agent-prod.yaml`

Part of the folder `deploy/argocd/` of the backend repo (B2). Fill in the repo address (B1). Pasted into Argo CD in D3.

```yaml
# Argo CD Application for the data agent in production.
# Pasted into Argo CD by hand (guide, step D3). Argo CD does not read this
# file from the repo; it is kept here so that the text is not lost.
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: data-agent-prod
  namespace: argocd
  finalizers:
    # Deleting this Application also deletes everything it created.
    - resources-finalizer.argocd.argoproj.io
spec:
  project: dice
  source:
    # The backend repo on the company GitHub. Replace YOUR-ORG with the owner.
    repoURL: https://github.sec.samsung.net/YOUR-ORG/cosmo-data-agent-backend.git
    # The one branch Argo CD reads. Deployment files count only on this branch.
    targetRevision: main
    path: deploy/argocd/charts/data-agent
    helm:
      releaseName: data-agent
      valueFiles:
        - ../../environments/production/data-agent.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: dice
  syncPolicy:
    # No "automated" block: syncing is by hand.
    syncOptions:
      - CreateNamespace=false
```
