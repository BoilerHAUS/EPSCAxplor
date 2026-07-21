#!/usr/bin/env bash
#
# EPSCAxplor off-VPS backup (#143).
#
# Dumps the Postgres `epsca` database and every Qdrant collection to a staging
# directory, then ships an encrypted, deduplicated, retention-pruned copy to an
# S3-compatible bucket with restic. Intended to run nightly via the systemd
# timer in this directory. Idempotent and safe to re-run by hand.
#
# Design notes:
#   - Postgres is dumped with `docker exec` (the container is on the internal
#     dokploy-network and is not reachable from the host directly).
#   - Qdrant is snapshotted per-collection over its HTTP API from a throwaway
#     curl container attached to dokploy-network, so no host port, socat tunnel,
#     or hard-coded overlay IP is required. Per-collection snapshots restore via
#     the API without a Qdrant restart (see restore.sh).
#   - restic provides encryption-at-rest (the DB holds password hashes, refresh
#     tokens, and query logs), dedup, integrity checks, and retention.
#
# Every required secret comes from the environment / EnvironmentFile — nothing
# is hard-coded. See backup.env.example.

set -euo pipefail
# All files this script creates (plaintext dumps, snapshots, the Qdrant auth
# config) must be private: they briefly hold DB contents and, once #144 lands,
# the Qdrant API key. 0077 → files 0600, dirs 0700, regardless of caller umask.
umask 0077

# ─── Configuration ───────────────────────────────────────────────────────────

# Load an env file for manual runs; systemd supplies these via EnvironmentFile.
# `set -a` so sourced vars are EXPORTED — restic reads RESTIC_REPOSITORY / AWS_*
# from the environment, and a plain `source` would only set shell (unexported)
# vars that child processes never see. (systemd's EnvironmentFile exports for us.)
BACKUP_ENV="${EPSCA_BACKUP_ENV:-/etc/epsca/backup.env}"
if [[ -f "$BACKUP_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$BACKUP_ENV"
  set +a
fi

DB_NAME="${DB_NAME:-epsca}"
DB_USER="${DB_USER:-epsca_user}"
PG_CONTAINER_FILTER="${PG_CONTAINER_FILTER:-epsca-db}"
QDRANT_CONTAINER_FILTER="${QDRANT_CONTAINER_FILTER:-epsca-qdrant}"
QDRANT_PORT="${QDRANT_PORT:-6333}"
QDRANT_API_KEY="${QDRANT_API_KEY:-}"          # optional; forward-compat with #144
DOCKER_NETWORK="${DOCKER_NETWORK:-dokploy-network}"
CURL_IMAGE="${CURL_IMAGE:-curlimages/curl:8.10.1}"
STAGING_DIR="${STAGING_DIR:-/var/lib/epsca-backups/staging}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
BACKUP_HOST="${BACKUP_HOST:-epsca-vps}"
LOCK_FILE="${LOCK_FILE:-/var/lock/epsca-backup.lock}"
# First-run safety valve: this script refuses to CREATE a restic repo, so an
# unreachable/misconfigured repo can never be mistaken for a fresh one (which
# would silently start an empty backup history). Set INIT_REPO=1 once, on the
# genuine first run, to allow `restic init`.
INIT_REPO="${INIT_REPO:-0}"
# Deep (read-data) restic verification is expensive; off by default. A weekly
# `restic check --read-data-subset=10%` is recommended instead (see runbook).
RESTIC_DEEP_CHECK="${RESTIC_DEEP_CHECK:-0}"

log() { printf '%s [backup] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
warn() { printf '%s [backup] WARNING: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
die() { printf '%s [backup] ERROR: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; exit 1; }

require() {
  local missing=0 var
  for var in "$@"; do
    if [[ -z "${!var:-}" ]]; then
      printf 'ERROR: required env var %s is not set\n' "$var" >&2
      missing=1
    fi
  done
  [[ "$missing" -eq 0 ]] || die "missing required configuration (see backup.env.example)"
}

# restic reads RESTIC_REPOSITORY + a password and S3 credentials from the env.
require RESTIC_REPOSITORY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
if [[ -z "${RESTIC_PASSWORD:-}" && -z "${RESTIC_PASSWORD_FILE:-}" ]]; then
  die "set RESTIC_PASSWORD or RESTIC_PASSWORD_FILE"
fi
command -v docker >/dev/null || die "docker not found on PATH"
command -v restic >/dev/null || die "restic not found on PATH (see runbook for install)"

# Guard the root-owned `rm -rf` target: never an empty value or a system path.
case "$STAGING_DIR" in
  /var/*|/tmp/*|/srv/*) : ;;
  *) die "refusing to use STAGING_DIR='$STAGING_DIR' (must be under /var, /tmp, or /srv)" ;;
esac

# ─── Concurrency guard ───────────────────────────────────────────────────────
# flock keeps a slow run from overlapping the next scheduled one. The kernel
# releases the lock automatically if this process dies, so it never wedges.
exec 9>"$LOCK_FILE" || die "cannot open lock file $LOCK_FILE"
flock -n 9 || die "another backup run holds $LOCK_FILE; aborting"

# ─── Workspace ───────────────────────────────────────────────────────────────
# A stable staging path keeps restic's stored paths constant → better dedup.
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR/postgres" "$STAGING_DIR/qdrant"
chmod 700 "$STAGING_DIR"

# Track Qdrant snapshots created on the server so we can delete them on exit.
declare -a CREATED_SNAPSHOTS=()
QDRANT_IP=""
QDRANT_CURL_CFG=""   # set iff a Qdrant API key is configured

cleanup() {
  local rc=$?
  local entry collection snap
  for entry in "${CREATED_SNAPSHOTS[@]:-}"; do
    [[ -n "$entry" ]] || continue
    collection="${entry%%:*}"
    snap="${entry#*:}"
    qdrant_curl -X DELETE \
      "http://${QDRANT_IP}:${QDRANT_PORT}/collections/${collection}/snapshots/${snap}" \
      >/dev/null 2>&1 || true
  done
  rm -rf "$STAGING_DIR"   # also removes the Qdrant auth config, if any
  [[ "$rc" -eq 0 ]] && log "done" || log "failed (exit $rc)"
  exit "$rc"
}
trap cleanup EXIT

# ─── Helpers ─────────────────────────────────────────────────────────────────

# Write the Qdrant API key to a 0600 curl config file (mounted read-only into
# the curl containers and read via `-K`), so it never appears on any process
# argv / world-readable /proc/<pid>/cmdline. No-op when no key is configured.
init_qdrant_auth() {
  [[ -n "$QDRANT_API_KEY" ]] || return 0
  QDRANT_CURL_CFG="$STAGING_DIR/.qdrant-curl.cfg"
  printf 'header = "api-key: %s"\n' "$QDRANT_API_KEY" > "$QDRANT_CURL_CFG"
}

# Build the docker mount + curl flags that inject the auth config, if present.
_qdrant_auth_docker() { [[ -n "$QDRANT_CURL_CFG" ]] && printf -- '-v\n%s:/qcfg:ro\n' "$QDRANT_CURL_CFG"; }
_qdrant_auth_curl()   { [[ -n "$QDRANT_CURL_CFG" ]] && printf -- '-K\n/qcfg\n'; }

# Run curl inside a throwaway container on dokploy-network. Extra args passed on.
qdrant_curl() {
  local mount=() cfg=()
  mapfile -t mount < <(_qdrant_auth_docker)
  mapfile -t cfg   < <(_qdrant_auth_curl)
  docker run --rm --network "$DOCKER_NETWORK" --user "$(id -u):$(id -g)" \
    "${mount[@]}" "$CURL_IMAGE" \
    -sS --fail --max-time 600 "${cfg[@]}" "$@"
}

# Same, but stream a download into the staging dir (mounted at /out). --user
# matches the host caller (root under systemd) so it can write the mounted dir.
qdrant_download() {
  local url="$1" outfile="$2" mount=() cfg=()
  mapfile -t mount < <(_qdrant_auth_docker)
  mapfile -t cfg   < <(_qdrant_auth_curl)
  docker run --rm --network "$DOCKER_NETWORK" --user "$(id -u):$(id -g)" \
    -v "$STAGING_DIR/qdrant:/out" "${mount[@]}" "$CURL_IMAGE" \
    -sS --fail --max-time 3600 "${cfg[@]}" -o "/out/${outfile}" "$url"
}

# Resolve exactly one running container by name substring; refuse ambiguity.
resolve_container() {
  local filter="$1" ids count
  ids="$(docker ps --filter "name=${filter}" --format '{{.ID}}')"
  [[ -n "$ids" ]] || die "no running container matches name~=${filter}"
  count="$(printf '%s\n' "$ids" | wc -l | tr -d ' ')"
  [[ "$count" -eq 1 ]] || die "ambiguous: ${count} containers match name~=${filter} — refine the filter"
  printf '%s' "$ids"
}

# ─── 1. Postgres ─────────────────────────────────────────────────────────────
backup_postgres() {
  local cid
  cid="$(resolve_container "$PG_CONTAINER_FILTER")"
  log "postgres: dumping '${DB_NAME}' from container ${cid:0:12} (custom format)"
  # -Fc: compressed, self-contained, restores with pg_restore --clean --if-exists.
  docker exec "$cid" pg_dump -U "$DB_USER" -Fc -d "$DB_NAME" \
    > "$STAGING_DIR/postgres/${DB_NAME}.dump"
  local size
  size="$(du -h "$STAGING_DIR/postgres/${DB_NAME}.dump" | cut -f1)"
  log "postgres: dump complete (${size})"
}

# ─── 2. Qdrant ───────────────────────────────────────────────────────────────
backup_qdrant() {
  local qcid
  qcid="$(resolve_container "$QDRANT_CONTAINER_FILTER")"
  QDRANT_IP="$(docker inspect \
    -f "{{(index .NetworkSettings.Networks \"${DOCKER_NETWORK}\").IPAddress}}" "$qcid")"
  [[ -n "$QDRANT_IP" ]] || die "could not resolve Qdrant IP on ${DOCKER_NETWORK}"
  init_qdrant_auth
  log "qdrant: reachable at ${QDRANT_IP}:${QDRANT_PORT}"

  # Enumerate collections via the API (jq-free JSON parse with python3).
  local collections
  collections="$(qdrant_curl "http://${QDRANT_IP}:${QDRANT_PORT}/collections" \
    | python3 -c 'import sys,json; print("\n".join(c["name"] for c in json.load(sys.stdin)["result"]["collections"]))')"
  [[ -n "$collections" ]] || die "no Qdrant collections found — refusing to write an empty backup"

  local collection snap
  while IFS= read -r collection; do
    [[ -n "$collection" ]] || continue
    log "qdrant: snapshotting collection '${collection}'"
    snap="$(qdrant_curl -X POST \
      "http://${QDRANT_IP}:${QDRANT_PORT}/collections/${collection}/snapshots" \
      | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["name"])')"
    [[ -n "$snap" ]] || die "snapshot creation returned no name for '${collection}'"
    CREATED_SNAPSHOTS+=("${collection}:${snap}")
    log "qdrant: downloading ${collection}/${snap}"
    qdrant_download \
      "http://${QDRANT_IP}:${QDRANT_PORT}/collections/${collection}/snapshots/${snap}" \
      "${collection}.snapshot"
  done <<<"$collections"

  # Record collection → file mapping so restore knows what to recover.
  printf '%s\n' "$collections" > "$STAGING_DIR/qdrant/collections.txt"
  log "qdrant: $(wc -l <"$STAGING_DIR/qdrant/collections.txt" | tr -d ' ') collection(s) captured"
}

# ─── 3. Ship with restic ─────────────────────────────────────────────────────
ship() {
  # Never auto-create the repo on a failed access: that would hide a
  # misconfigured/unreachable repo behind a fresh, empty backup history.
  local status
  if ! status="$(restic cat config 2>&1)"; then
    if [[ "$INIT_REPO" == "1" ]]; then
      log "restic: initialising new repository (INIT_REPO=1)"
      restic init
    else
      die "restic repository not accessible; refusing to auto-create it. For genuine first-time setup run 'restic init' (see runbook) or re-run with INIT_REPO=1. restic said: ${status}"
    fi
  fi

  log "restic: backing up staging tree"
  restic backup --tag epsca --host "$BACKUP_HOST" "$STAGING_DIR"
  # Past this point the backup is safely stored. Retention/verification
  # failures are logged but must NOT mark the whole run failed — a stale,
  # unpruned repo is far better than an operator distrusting a good backup.

  log "restic: applying retention (daily=${KEEP_DAILY} weekly=${KEEP_WEEKLY})"
  restic forget --host "$BACKUP_HOST" --tag epsca \
    --keep-daily "$KEEP_DAILY" --keep-weekly "$KEEP_WEEKLY" --prune \
    || warn "restic forget/prune failed; backup IS stored, but retention did not run"

  log "restic: structural check"
  restic check || warn "restic check reported problems; inspect the repository"
  if [[ "$RESTIC_DEEP_CHECK" == "1" ]]; then
    log "restic: deep check (read-data-subset=10%)"
    restic check --read-data-subset=10% || warn "restic deep check reported problems"
  fi
}

# ─── Main ────────────────────────────────────────────────────────────────────
log "starting backup run"
backup_postgres
backup_qdrant
ship
log "backup succeeded"
