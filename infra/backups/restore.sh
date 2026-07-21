#!/usr/bin/env bash
#
# EPSCAxplor restore from an off-VPS restic backup (#143).
#
# Pulls a snapshot from the restic S3 repository and restores it into the
# running Postgres and Qdrant containers. DESTRUCTIVE: it overwrites the target
# database and collections. Requires an interactive confirmation unless --yes.
#
# Usage:
#   ./restore.sh [--snapshot <id|latest>] [--target <dir>] [--yes]
#                [--only postgres|qdrant]
#
# Run the same-directory backup.env (or EPSCA_BACKUP_ENV) first so the restic
# repo, S3 credentials, and container filters are in the environment.

set -euo pipefail
umask 0077   # restored dumps hold the same sensitive data as the backup

# ─── Configuration ───────────────────────────────────────────────────────────
BACKUP_ENV="${EPSCA_BACKUP_ENV:-/etc/epsca/backup.env}"
if [[ -f "$BACKUP_ENV" ]]; then
  # set -a: export sourced vars so restic (reads RESTIC_REPOSITORY / AWS_* from
  # the environment) inherits them on manual runs, matching systemd's behaviour.
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

SNAPSHOT="latest"
TARGET_DIR=""
TARGET_SUPPLIED=0
ASSUME_YES=0
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --snapshot) SNAPSHOT="$2"; shift 2 ;;
    --target)   TARGET_DIR="$2"; TARGET_SUPPLIED=1; shift 2 ;;
    --only)     ONLY="$2"; shift 2 ;;
    --yes|-y)   ASSUME_YES=1; shift ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done

log() { printf '%s [restore] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { printf '%s [restore] ERROR: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; exit 1; }

require() {
  local missing=0 var
  for var in "$@"; do
    if [[ -z "${!var:-}" ]]; then
      printf 'ERROR: required env var %s is not set (source backup.env)\n' "$var" >&2
      missing=1
    fi
  done
  [[ "$missing" -eq 0 ]] || die "missing required configuration (see backup.env.example)"
}
require RESTIC_REPOSITORY AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
if [[ -z "${RESTIC_PASSWORD:-}" && -z "${RESTIC_PASSWORD_FILE:-}" ]]; then
  die "set RESTIC_PASSWORD or RESTIC_PASSWORD_FILE"
fi
command -v docker >/dev/null || die "docker not found on PATH"
command -v restic >/dev/null || die "restic not found on PATH"

# A reused --target could mix stale artifacts from an earlier restore (restic
# restore only writes the requested snapshot's files, it does not clear first).
if [[ "$TARGET_SUPPLIED" -eq 1 && -e "$TARGET_DIR" ]]; then
  [[ -d "$TARGET_DIR" && -z "$(ls -A "$TARGET_DIR" 2>/dev/null)" ]] \
    || die "--target '$TARGET_DIR' already exists and is not empty; use a fresh directory"
fi
TARGET_DIR="${TARGET_DIR:-$(mktemp -d /tmp/epsca-restore.XXXXXX)}"
mkdir -p "$TARGET_DIR"

QDRANT_CURL_CFG=""
# NB: an `if` (not `[[ ... ]] && ...`) so the trap always returns 0 — a trap
# ending in a false test would otherwise become the script's exit status and
# make a successful restore report failure when no API key is configured.
cleanup() { if [[ -n "$QDRANT_CURL_CFG" ]]; then rm -f "$QDRANT_CURL_CFG"; fi; }
trap cleanup EXIT

resolve_container() {
  local filter="$1" ids count
  ids="$(docker ps --filter "name=${filter}" --format '{{.ID}}')"
  [[ -n "$ids" ]] || die "no running container matches name~=${filter}"
  count="$(printf '%s\n' "$ids" | wc -l | tr -d ' ')"
  [[ "$count" -eq 1 ]] || die "ambiguous: ${count} containers match name~=${filter} — refine the filter"
  printf '%s' "$ids"
}

confirm() {
  [[ "$ASSUME_YES" -eq 1 ]] && return 0
  printf '\n*** This OVERWRITES the live %s. Type "restore" to proceed: ' "$1"
  local answer; read -r answer
  [[ "$answer" == "restore" ]] || die "aborted by operator"
}

# ─── 1. Pull the snapshot from S3 ────────────────────────────────────────────
log "restic: restoring snapshot '${SNAPSHOT}' → ${TARGET_DIR}"
restic restore "$SNAPSHOT" --target "$TARGET_DIR"

# restic preserves the absolute staging path; locate the restored tree.
PG_DUMP="$(find "$TARGET_DIR" -type f -name "${DB_NAME}.dump" | head -n1)"
QDRANT_DIR="$(find "$TARGET_DIR" -type d -name qdrant | head -n1)"
[[ -n "$PG_DUMP" ]]   || log "warning: no ${DB_NAME}.dump found in snapshot"
[[ -n "$QDRANT_DIR" ]] || log "warning: no qdrant/ directory found in snapshot"

# ─── 2. Postgres ─────────────────────────────────────────────────────────────
restore_postgres() {
  [[ -n "$PG_DUMP" ]] || die "cannot restore Postgres: dump not present in snapshot"
  confirm "Postgres database '${DB_NAME}'"
  local cid; cid="$(resolve_container "$PG_CONTAINER_FILTER")"
  log "postgres: restoring ${DB_NAME} into container ${cid:0:12}"
  # --clean --if-exists drops existing objects first; --no-owner ignores the
  # dump's role grants (we restore as the connecting superuser/app role).
  docker exec -i "$cid" pg_restore -U "$DB_USER" --clean --if-exists --no-owner \
    -d "$DB_NAME" < "$PG_DUMP"
  log "postgres: restore complete"
}

# ─── 3. Qdrant ───────────────────────────────────────────────────────────────
restore_qdrant() {
  [[ -n "$QDRANT_DIR" ]] || die "cannot restore Qdrant: qdrant/ not present in snapshot"
  confirm "Qdrant collections"
  local qcid; qcid="$(resolve_container "$QDRANT_CONTAINER_FILTER")"
  local qip
  qip="$(docker inspect \
    -f "{{(index .NetworkSettings.Networks \"${DOCKER_NETWORK}\").IPAddress}}" "$qcid")"
  [[ -n "$qip" ]] || die "could not resolve Qdrant IP on ${DOCKER_NETWORK}"

  # API key (if any) via a 0600 config file, never on the docker/curl argv.
  local mount=() cfg=()
  if [[ -n "$QDRANT_API_KEY" ]]; then
    QDRANT_CURL_CFG="$(mktemp)"; chmod 600 "$QDRANT_CURL_CFG"
    printf 'header = "api-key: %s"\n' "$QDRANT_API_KEY" > "$QDRANT_CURL_CFG"
    mount=(-v "$QDRANT_CURL_CFG:/qcfg:ro"); cfg=(-K /qcfg)
  fi

  local collection
  while IFS= read -r collection; do
    [[ -n "$collection" ]] || continue
    [[ -f "${QDRANT_DIR}/${collection}.snapshot" ]] \
      || { log "warning: snapshot for '${collection}' missing, skipping"; continue; }
    log "qdrant: recovering collection '${collection}' via snapshot upload"
    # priority=snapshot: the uploaded snapshot's data wins over any live data.
    # upload recreates the collection if it is absent (verified for full DR).
    # --user matches the host caller so the read-only mounts are readable.
    docker run --rm --network "$DOCKER_NETWORK" --user "$(id -u):$(id -g)" \
      -v "${QDRANT_DIR}:/in:ro" "${mount[@]}" "$CURL_IMAGE" \
      -sS --fail --max-time 3600 "${cfg[@]}" \
      -X POST "http://${qip}:${QDRANT_PORT}/collections/${collection}/snapshots/upload?priority=snapshot" \
      -F "snapshot=@/in/${collection}.snapshot"
    printf '\n'
  done < "${QDRANT_DIR}/collections.txt"
  log "qdrant: restore complete"
}

case "$ONLY" in
  postgres) restore_postgres ;;
  qdrant)   restore_qdrant ;;
  "")       restore_postgres; restore_qdrant ;;
  *) die "invalid --only value '${ONLY}' (expected postgres|qdrant)" ;;
esac

log "restore finished. Restored tree left in ${TARGET_DIR}"
log "Verify the app, then remove ${TARGET_DIR} when satisfied."
