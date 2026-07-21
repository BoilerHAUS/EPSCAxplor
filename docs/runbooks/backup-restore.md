# Runbook: Backup & Restore (#143)

Off-VPS, encrypted, nightly backups of the two stateful stores, with a tested
restore path. A VPS or volume loss must be recoverable.

| Store | Source | Method | Volume |
|---|---|---|---|
| Postgres | `epsca-db` container | `pg_dump -Fc` via `docker exec` | `epsca-db-data` |
| Qdrant | `epsca-qdrant` container | per-collection snapshot over the HTTP API | `epsca-qdrant-data` |

Both artifacts are shipped to an S3-compatible bucket with **restic**
(encryption-at-rest, dedup, retention, integrity checks). Retention: 7 daily +
4 weekly. Schedule: `systemd` timer at 03:30 daily.

Tooling lives in [`infra/backups/`](../../infra/backups/): `backup.sh`,
`restore.sh`, `backup.env.example`, and the `epsca-backup.{service,timer}` units.

> Why restic + logical dumps rather than a raw volume tar: the Postgres volume
> holds password hashes, refresh tokens, and query logs — encryption-at-rest is
> mandatory. Logical dumps also restore cleanly across minor engine versions and
> onto a fresh host; the Qdrant snapshot API gives a consistent hot copy without
> stopping the container.

---

## One-time setup (VPS)

All commands run on the VPS host as a user in the `docker` group (see CLAUDE.md
"VPS access").

### 1. Provision object storage

Create an S3-compatible bucket (OVH Object Storage → "S3 Users"/"S3 keys", or any
S3 provider) and an access key/secret scoped to it. Note the endpoint + region,
e.g. `s3.gra.io.cloud.ovh.net`.

### 2. Install restic

```bash
sudo apt-get update && sudo apt-get install -y restic
restic version   # >= 0.16 recommended
```

### 3. Create the config + secrets

```bash
sudo mkdir -p /etc/epsca
# Repo encryption password — STORE A COPY IN YOUR PASSWORD MANAGER.
# Losing it makes every backup unrecoverable.
openssl rand -base64 32 | sudo tee /etc/epsca/restic.pass >/dev/null
sudo chmod 600 /etc/epsca/restic.pass

sudo cp infra/backups/backup.env.example /etc/epsca/backup.env
sudo chmod 600 /etc/epsca/backup.env
sudoedit /etc/epsca/backup.env   # fill RESTIC_REPOSITORY, AWS_* keys
```

Confirm the container-name filters in `backup.env` match this deployment —
Dokploy/Swarm mangles the compose service names (e.g. `epscaxplor-epscadb-…`,
`epscaxplor-epscaqdrant-…`), so the generic `epsca-db`/`epsca-qdrant` will *not*
match:

```bash
docker ps --format '{{.Names}}' | grep -iE 'epscadb|epscaqdrant'
```

### 3b. Install the scripts to a root-owned location

The root timer must not execute a script writable by a normal user, so install
the scripts outside any user's home/git checkout:

```bash
sudo mkdir -p /opt/epsca/backups
sudo cp infra/backups/backup.sh infra/backups/restore.sh /opt/epsca/backups/
sudo chown -R root:root /opt/epsca/backups
sudo chmod 700 /opt/epsca/backups
```

### 4. Initialise the repository & smoke-test

```bash
set -a; source /etc/epsca/backup.env; set +a
restic snapshots || restic init          # first run initialises the repo
sudo EPSCA_BACKUP_ENV=/etc/epsca/backup.env infra/backups/backup.sh   # full dry run
restic snapshots                         # confirm a snapshot appeared
```

> Safety valve: `backup.sh` will **not** create the repo on its own — if
> `restic` can't reach it, the run fails loudly rather than silently starting a
> fresh, empty backup history behind a misconfigured endpoint. Initialise once
> with `restic init` (above), or pass `INIT_REPO=1` on the genuine first run.
> If a nightly run ever errors with "repository not accessible", the endpoint or
> S3 credentials are wrong — do not set `INIT_REPO=1` to paper over it.

> Troubleshooting `restic init`:
> - **"The request signature we calculated does not match…"** → wrong region or
>   secret key. Set `AWS_DEFAULT_REGION` to your endpoint's region (e.g. `gra`),
>   and re-check `AWS_SECRET_ACCESS_KEY` for typos / trailing whitespace and that
>   it's the **S3** key (not an OpenStack password).
> - **"Please specify repository location"** → `RESTIC_REPOSITORY` isn't in the
>   environment; on manual runs source the env with `set -a` (backup.sh does this).

### 5. Install the schedule

The unit's `ExecStart` points at `/opt/epsca/backups/backup.sh` (installed in
step 3b). Edit the unit if you install the scripts elsewhere.

```bash
sudo cp infra/backups/epsca-backup.service /etc/systemd/system/
sudo cp infra/backups/epsca-backup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now epsca-backup.timer
systemctl list-timers epsca-backup.timer   # confirm next run
```

---

## Daily operation

- **Run now:** `sudo systemctl start epsca-backup.service`
- **Logs:** `journalctl -u epsca-backup.service -n 100 --no-pager`
- **List backups:** `restic snapshots` (source `/etc/epsca/backup.env` first)
- **Last run status:** `systemctl status epsca-backup.service`

Consider a weekly deep integrity check (cheap insurance):

```bash
restic check --read-data-subset=10%
```

---

## Restore

`restore.sh` is **destructive** — it overwrites the live DB and collections. It
prompts for confirmation (`--yes` to skip) and restores the `latest` snapshot
unless `--snapshot <id>` is given.

```bash
set -a; source /etc/epsca/backup.env; set +a

# Full disaster recovery (both stores):
sudo -E infra/backups/restore.sh

# Selective:
sudo -E infra/backups/restore.sh --only postgres
sudo -E infra/backups/restore.sh --only qdrant --snapshot 4a7f9c2b
```

Steps performed:
1. `restic restore <snapshot> --target <tmp>` pulls + decrypts the artifacts.
2. Postgres: `pg_restore --clean --if-exists --no-owner` into `epsca-db`.
3. Qdrant: each collection is recovered via `POST /collections/{c}/snapshots/upload?priority=snapshot`.

After a restore, hit `/health` and run a known query to confirm retrieval works,
then delete the temporary restore directory the script prints.

### Recovering onto a brand-new VPS

1. Bring the stack up empty (Dokploy deploy) so `epsca-db` + `epsca-qdrant` run.
2. Install restic, copy `/etc/epsca/backup.env` **and the restic password**.
3. Run `restore.sh`. (`pg_restore --clean` tolerates the empty target.)

---

## Verifying a restore (do this at least once — acceptance criterion)

Rehearse the round-trip against throwaway containers so you never test restore
for the first time during a real incident. This mirrors CLAUDE.md "Testing
migrations locally" and needs no VPS or object storage.

```bash
# 1. Throwaway Postgres + Qdrant with seed data
docker run -d --name epsca-db-test  -e POSTGRES_DB=epsca -e POSTGRES_USER=epsca_user \
  -e POSTGRES_PASSWORD=testpw postgres:16-alpine
docker run -d --name epsca-qdrant-test qdrant/qdrant:latest
sleep 5
docker exec -i epsca-db-test psql -U epsca_user -d epsca <<'SQL'
CREATE TABLE canary(id int primary key, note text);
INSERT INTO canary VALUES (1,'before-backup');
SQL

# 2. Dump  →  3. destroy  →  4. restore  →  5. assert the canary survived.
#    (Point PG_CONTAINER_FILTER/QDRANT_CONTAINER_FILTER at the -test containers
#     and use a local restic repo: RESTIC_REPOSITORY=/tmp/epsca-restic-test.)

docker rm -f epsca-db-test epsca-qdrant-test
```

The maintained, self-checking version of this drill is
[`infra/backups/verify_roundtrip.sh`](../../infra/backups/verify_roundtrip.sh);
run it locally to prove backup → restore before trusting production. It needs
`docker` + `restic` on PATH, spins up throwaway containers, and cleans up after
itself:

```bash
infra/backups/verify_roundtrip.sh                          # default path
QDRANT_API_KEY=some-test-key infra/backups/verify_roundtrip.sh   # also exercise Qdrant API-key auth (#144)
```

---

## Security notes

- `/etc/epsca/backup.env` and `/etc/epsca/restic.pass` are `chmod 600`, root-owned,
  and never committed (only `backup.env.example` is in git).
- restic encrypts client-side, so the S3 provider never sees plaintext DB
  contents. Scope the S3 key to the single backup bucket.
- Rotate the S3 key and `restic.pass` if a VPS compromise is suspected; a new
  `restic.pass` requires re-initialising the repo (old snapshots stay readable
  only with the old password).
```
