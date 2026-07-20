#!/usr/bin/env bash
#
# End-to-end backup → restore drill against throwaway containers (#143).
#
# Proves backup.sh + restore.sh actually round-trip data before you trust them
# in production. Uses a LOCAL restic repository and disposable Postgres/Qdrant
# containers on a private bridge network — no VPS, no object storage, no
# /etc/epsca config touched. Everything is torn down on exit.
#
# Requires: docker + restic on PATH. Run from anywhere:
#   infra/backups/verify_roundtrip.sh

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NET="epsca-backup-verify-net"
PG="epsca-db-verify"
QD="epsca-qdrant-verify"
TMP="$(mktemp -d /tmp/epsca-verify.XXXXXX)"
CURL_IMAGE="${CURL_IMAGE:-curlimages/curl:8.10.1}"
# Match whatever Qdrant tag production runs (compose currently uses :latest);
# override to pin once prod pins Qdrant.
QDRANT_IMAGE="${QDRANT_IMAGE:-qdrant/qdrant:latest}"
# Set to also exercise the API-key auth path (forward-compat with #144): the
# throwaway Qdrant is started with this key and the real scripts must use it.
QDRANT_API_KEY="${QDRANT_API_KEY:-}"

log()  { printf '\033[1;34m[verify]\033[0m %s\n' "$*"; }
pass() { printf '\033[1;32m[verify] PASS:\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[verify] FAIL:\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || fail "docker not found"
command -v restic >/dev/null || fail "restic not found (install it to run this drill)"

cleanup() {
  docker rm -f "$PG" "$QD" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT

# ─── Environment the real scripts consume ────────────────────────────────────
export EPSCA_BACKUP_ENV=/nonexistent            # never load a real /etc/epsca file
export RESTIC_REPOSITORY="$TMP/restic"
export RESTIC_PASSWORD="verify-not-secret"
export AWS_ACCESS_KEY_ID="unused" AWS_SECRET_ACCESS_KEY="unused"  # required by scripts; ignored by a local repo
export DB_NAME="epsca" DB_USER="epsca_user"
export PG_CONTAINER_FILTER="$PG" QDRANT_CONTAINER_FILTER="$QD"
export DOCKER_NETWORK="$NET" STAGING_DIR="$TMP/staging"
export CURL_IMAGE LOCK_FILE="$TMP/lock"
export QDRANT_API_KEY   # empty unless the caller opted into the auth path
export INIT_REPO=1      # the drill always uses a fresh throwaway restic repo

qcurl() {  # curl against the test Qdrant from a container on the same network
  local auth=()
  [[ -n "$QDRANT_API_KEY" ]] && auth=(-H "api-key: $QDRANT_API_KEY")
  docker run --rm --network "$NET" "$CURL_IMAGE" -sS --fail --max-time 60 "${auth[@]}" "$@"
}

# ─── Spin up throwaway infra ─────────────────────────────────────────────────
log "creating network + containers"
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_DB="$DB_NAME" -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD=verify \
  postgres:16-alpine >/dev/null
qdrant_env=()
[[ -n "$QDRANT_API_KEY" ]] && qdrant_env=(-e "QDRANT__SERVICE__API_KEY=$QDRANT_API_KEY")
docker run -d --name "$QD" --network "$NET" "${qdrant_env[@]}" "$QDRANT_IMAGE" >/dev/null

log "waiting for Postgres"
for _ in $(seq 1 30); do
  docker exec "$PG" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1 && break
  sleep 1
done
QD_IP="$(docker inspect -f "{{(index .NetworkSettings.Networks \"$NET\").IPAddress}}" "$QD")"
log "waiting for Qdrant at $QD_IP:6333"
for _ in $(seq 1 30); do
  qcurl "http://$QD_IP:6333/readyz" >/dev/null 2>&1 && break
  sleep 1
done

# ─── Seed canary data ────────────────────────────────────────────────────────
log "seeding Postgres + Qdrant canaries"
docker exec -i "$PG" psql -U "$DB_USER" -d "$DB_NAME" >/dev/null <<'SQL'
CREATE TABLE canary (id int PRIMARY KEY, note text);
INSERT INTO canary VALUES (1, 'before-backup');
SQL
qcurl -X PUT "http://$QD_IP:6333/collections/canary" \
  -H 'Content-Type: application/json' \
  -d '{"vectors":{"size":4,"distance":"Cosine"}}' >/dev/null
qcurl -X PUT "http://$QD_IP:6333/collections/canary/points?wait=true" \
  -H 'Content-Type: application/json' \
  -d '{"points":[{"id":1,"vector":[0.1,0.2,0.3,0.4],"payload":{"note":"before-backup"}}]}' >/dev/null

# ─── Back up ─────────────────────────────────────────────────────────────────
log "running backup.sh"
"$HERE/backup.sh"

# ─── Simulate data loss ──────────────────────────────────────────────────────
log "destroying live data (DROP TABLE + DELETE collection)"
docker exec -i "$PG" psql -U "$DB_USER" -d "$DB_NAME" -c 'DROP TABLE canary;' >/dev/null
qcurl -X DELETE "http://$QD_IP:6333/collections/canary" >/dev/null

# ─── Restore ─────────────────────────────────────────────────────────────────
log "running restore.sh --yes"
"$HERE/restore.sh" --yes

# ─── Assert ──────────────────────────────────────────────────────────────────
log "verifying restored data"
note="$(docker exec -i "$PG" psql -U "$DB_USER" -d "$DB_NAME" -tAc \
  'SELECT note FROM canary WHERE id = 1;' 2>/dev/null || true)"
[[ "$note" == "before-backup" ]] || fail "Postgres canary not restored (got: '${note:-<none>}')"
pass "Postgres canary row restored"

count="$(qcurl "http://$QD_IP:6333/collections/canary" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["result"]["points_count"])' 2>/dev/null || echo "")"
[[ "$count" == "1" ]] || fail "Qdrant canary not restored (points_count=${count:-<none>})"
pass "Qdrant canary collection restored (1 point)"

printf '\n\033[1;32m[verify] backup → restore round-trip OK\033[0m\n'
