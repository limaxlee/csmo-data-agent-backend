# Database capacity for Defect Studio preview workers

Defect Studio's 64-preview profile uses four worker Pods with 16 thumbnail
slots each. Each active preview currently retains one PostgreSQL advisory-lock
connection. Alongside Platform/Labeler/API pools, the old PostgreSQL default of
100 connections can be exhausted. The chart now starts PostgreSQL with
`database.postgres.maxConnections: 200` (`postgres -c max_connections=200`).

This is a startup setting and requires a database Pod restart, briefly
interrupting all clients of that environment's shared database. Apply this DB
capacity before enabling the 4 x 16 Defect worker profile. Existing PVCs, database
names, credentials, initialization scripts, images and PostgreSQL's 2GiB request /
4GiB limit are retained. Runtime override works on existing data volumes; it is
not an empty-volume init script or a database migration. Argo inline resource
values do not mask the new startup argument. The value remains overridable;
the schema accepts integers from 100 to 1000.

Use the normal stage chart deployment and manual production promotion. Do not
merge/sync live state as part of code review. After the chosen rollout, verify
`SHOW max_connections` is 200 and observe `pg_stat_activity`, DB memory and
worker completion/error logs under load. The 4GiB DB memory limit is not a
reservation for image bytes: all image buffers remain in worker Pods.
