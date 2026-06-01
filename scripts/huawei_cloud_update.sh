#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/spm}"
REMOTE="${REMOTE:-origin}"
BRANCH="${BRANCH:-}"
DB_DUMP_FILE="${DB_DUMP_FILE:-dataset/spm_postgres_dump.sql}"
BACKUP_DIR="${BACKUP_DIR:-backups/cloud-db}"
RESTORE_DB="${RESTORE_DB:-1}"
RUN_BUILD="${RUN_BUILD:-1}"
WAIT_SECONDS="${WAIT_SECONDS:-90}"
PROGRESS_INTERVAL_SECONDS="${PROGRESS_INTERVAL_SECONDS:-15}"
GIT_RETRIES="${GIT_RETRIES:-5}"
GIT_RETRY_DELAY_SECONDS="${GIT_RETRY_DELAY_SECONDS:-8}"
APP_PORT="${APP_PORT:-}"
POSTGRES_DB="${POSTGRES_DB:-}"
POSTGRES_USER="${POSTGRES_USER:-}"

usage() {
    cat <<'EOF'
Usage:
  bash scripts/huawei_cloud_update.sh [options]

Options:
  --app-dir DIR     Project directory on the cloud server. Default: /opt/spm
  --branch NAME     Git branch to pull. Default: current branch
  --dump FILE       SQL dump to restore. Default: dataset/spm_postgres_dump.sql
  --skip-db         Pull code and rebuild containers without restoring the DB
  --skip-build      Pull code and start containers without rebuilding the API image
  --help            Show this help

Environment variables:
  APP_DIR, REMOTE, BRANCH, DB_DUMP_FILE, BACKUP_DIR, RESTORE_DB, RUN_BUILD,
  WAIT_SECONDS, PROGRESS_INTERVAL_SECONDS, GIT_RETRIES,
  GIT_RETRY_DELAY_SECONDS, APP_PORT, POSTGRES_DB, POSTGRES_USER

Examples:
  bash scripts/huawei_cloud_update.sh
  bash scripts/huawei_cloud_update.sh --skip-db
  APP_DIR=/opt/spm RESTORE_DB=0 bash scripts/huawei_cloud_update.sh
EOF
}

log() {
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

run_with_heartbeat() {
    local label="$1"
    local start_ts elapsed status heartbeat_pid heartbeat_file
    shift

    start_ts="$(date '+%s')"
    heartbeat_file="${TMPDIR:-/tmp}/spm_update_heartbeat_$$_${RANDOM}"
    log "${label} started."
    : > "$heartbeat_file"

    (
        while [ -e "$heartbeat_file" ]; do
            sleep "$PROGRESS_INTERVAL_SECONDS" || exit 0
            if [ -e "$heartbeat_file" ]; then
                elapsed=$(($(date '+%s') - start_ts))
                log "${label} still running (${elapsed}s elapsed)..."
            fi
        done
    ) &
    heartbeat_pid=$!

    set +e
    "$@"
    status=$?
    set -e

    rm -f "$heartbeat_file"
    kill "$heartbeat_pid" >/dev/null 2>&1 || true
    wait "$heartbeat_pid" >/dev/null 2>&1 || true

    elapsed=$(($(date '+%s') - start_ts))
    if [ "$status" -eq 0 ]; then
        log "${label} finished (${elapsed}s elapsed)."
    else
        log "${label} failed after ${elapsed}s with exit code ${status}."
    fi

    return "$status"
}

git_retry() {
    local attempt=1

    while true; do
        if run_with_heartbeat "Git attempt ${attempt}/${GIT_RETRIES}: git $*" git \
            -c http.version=HTTP/1.1 \
            -c http.lowSpeedLimit=0 \
            -c http.lowSpeedTime=999999 \
            "$@"; then
            return 0
        fi

        if [ "$attempt" -ge "$GIT_RETRIES" ]; then
            die "Git command failed after ${GIT_RETRIES} attempts: git $*"
        fi

        log "Git command failed. Retrying in ${GIT_RETRY_DELAY_SECONDS}s (${attempt}/${GIT_RETRIES})..."
        attempt=$((attempt + 1))
        sleep "$GIT_RETRY_DELAY_SECONDS"
    done
}

read_env_value() {
    local key="$1"
    local line=""

    if [ -f ".env" ]; then
        line="$(grep -E "^[[:space:]]*${key}=" ".env" | tail -n 1 || true)"
    fi

    if [ -z "$line" ]; then
        return 0
    fi

    line="${line#*=}"
    line="${line%$'\r'}"
    line="${line%\"}"
    line="${line#\"}"
    line="${line%\'}"
    line="${line#\'}"
    printf '%s' "$line"
}

wait_for_db() {
    log "Waiting for PostgreSQL to become ready..."
    for _ in $(seq 1 "$WAIT_SECONDS"); do
        if docker compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
            log "PostgreSQL is ready."
            return 0
        fi
        sleep 1
    done
    docker compose ps || true
    die "PostgreSQL did not become ready within ${WAIT_SECONDS}s."
}

backup_db() {
    local timestamp backup_file

    timestamp="$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$BACKUP_DIR"
    backup_file="${BACKUP_DIR}/pre_update_${timestamp}.sql"

    log "Backing up current cloud database to ${backup_file}..."
    if docker compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_file"; then
        if command -v gzip >/dev/null 2>&1; then
            gzip -f "$backup_file"
            backup_file="${backup_file}.gz"
        fi
        log "Database backup saved: ${backup_file}"
    else
        rm -f "$backup_file"
        die "Database backup failed; aborting restore."
    fi
}

restore_db() {
    if [ "$RESTORE_DB" != "1" ]; then
        log "Skipping database restore because RESTORE_DB=${RESTORE_DB}."
        return 0
    fi

    if [ ! -f "$DB_DUMP_FILE" ]; then
        log "Skipping database restore because dump file was not found: ${DB_DUMP_FILE}"
        return 0
    fi

    backup_db
    log "Restoring cloud database from ${DB_DUMP_FILE}..."
    docker compose exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$DB_DUMP_FILE"
    log "Database restore completed."
}

wait_for_api() {
    local health_url response

    health_url="${HEALTH_URL:-http://127.0.0.1:${APP_PORT}/health}"
    log "Waiting for API health check: ${health_url}"

    for _ in $(seq 1 "$WAIT_SECONDS"); do
        if response="$(curl -fsS "$health_url" 2>/dev/null)"; then
            log "API health check passed: ${response}"
            return 0
        fi
        sleep 1
    done

    docker compose logs --tail=100 api || true
    die "API health check did not pass within ${WAIT_SECONDS}s."
}

while [ $# -gt 0 ]; do
    case "$1" in
        --app-dir)
            APP_DIR="${2:-}"
            [ -n "$APP_DIR" ] || die "--app-dir requires a value."
            shift 2
            ;;
        --branch)
            BRANCH="${2:-}"
            [ -n "$BRANCH" ] || die "--branch requires a value."
            shift 2
            ;;
        --dump)
            DB_DUMP_FILE="${2:-}"
            [ -n "$DB_DUMP_FILE" ] || die "--dump requires a value."
            shift 2
            ;;
        --skip-db)
            RESTORE_DB=0
            shift
            ;;
        --skip-build)
            RUN_BUILD=0
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            usage
            die "Unknown option: $1"
            ;;
    esac
done

need_cmd git
need_cmd docker
need_cmd curl

[ -d "$APP_DIR" ] || die "Project directory not found: ${APP_DIR}"
cd "$APP_DIR"
[ -d ".git" ] || die "Not a git repository: ${APP_DIR}"
docker compose version >/dev/null

if [ -z "$BRANCH" ]; then
    BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi
[ "$BRANCH" != "HEAD" ] || die "Repository is in detached HEAD state; pass --branch explicitly."

log "Updating source code from ${REMOTE}/${BRANCH}..."
git_retry fetch --progress --prune "$REMOTE"
if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
    git_retry pull --progress --ff-only --autostash
else
    git_retry pull --progress --ff-only --autostash "$REMOTE" "$BRANCH"
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    log "Creating .env from .env.example..."
    cp .env.example .env
fi

APP_PORT="${APP_PORT:-$(read_env_value APP_PORT)}"
POSTGRES_DB="${POSTGRES_DB:-$(read_env_value POSTGRES_DB)}"
POSTGRES_USER="${POSTGRES_USER:-$(read_env_value POSTGRES_USER)}"
APP_PORT="${APP_PORT:-8000}"
POSTGRES_DB="${POSTGRES_DB:-spm}"
POSTGRES_USER="${POSTGRES_USER:-spm}"

if [ "$RESTORE_DB" = "1" ] && [ -f "$DB_DUMP_FILE" ]; then
    log "Starting PostgreSQL service before database restore..."
    run_with_heartbeat "Docker Compose start db" docker compose up -d db
    wait_for_db

    log "Stopping API before database restore..."
    run_with_heartbeat "Docker Compose stop api" docker compose stop api || true
fi

restore_db

if [ "$RUN_BUILD" = "1" ]; then
    log "Building and starting Docker Compose services..."
    run_with_heartbeat "Docker Compose build and start services" docker compose up -d --build
else
    log "Starting Docker Compose services without rebuilding..."
    run_with_heartbeat "Docker Compose start services" docker compose up -d
fi

wait_for_db
wait_for_api

log "Current Docker Compose status:"
docker compose ps

log "Recent API logs:"
docker compose logs --tail=60 api

log "Huawei Cloud update completed."
