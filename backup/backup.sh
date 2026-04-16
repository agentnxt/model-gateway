#!/usr/bin/env bash
# backup/backup.sh — Daily backup of all persistent data
# Runs as a cron job inside the backup container.
# Uploads to S3-compatible storage (Cloudflare R2, MinIO, Backblaze B2, AWS S3).
#
# Required env vars (from docker-compose):
#   S3_ENDPOINT, S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
#   POSTGRES_ROOT_PASSWORD, POSTGRES_USER

set -euo pipefail

DATE=$(date +%Y-%m-%d-%H%M)
BACKUP_DIR="/tmp/backup-${DATE}"
mkdir -p "$BACKUP_DIR"

echo "=== Autonomyx Backup — $DATE ==="

# ── Postgres — all databases ───────────────────────────────────────────────────
echo "→ Backing up Postgres..."
for DB in litellm langflow openfga glitchtip; do
    PGPASSWORD="$POSTGRES_ROOT_PASSWORD" pg_dump \
        -h postgres -U "$POSTGRES_USER" \
        --no-password \
        -Fc "$DB" \
        > "$BACKUP_DIR/postgres-${DB}.dump"
    echo "  ✅ $DB ($(du -sh "$BACKUP_DIR/postgres-${DB}.dump" | cut -f1))"
done

# ── SurrealDB — export ─────────────────────────────────────────────────────────
echo "→ Backing up SurrealDB..."
surreal export \
    --conn http://surrealdb:8000 \
    --user "$SURREAL_USER" \
    --pass "$SURREAL_PASS" \
    --ns autonomyx \
    "$BACKUP_DIR/surrealdb.surql" 2>/dev/null && \
    echo "  ✅ SurrealDB ($(du -sh "$BACKUP_DIR/surrealdb.surql" | cut -f1))" || \
    echo "  ⚠️  SurrealDB backup skipped (not reachable)"

# ── Compress ──────────────────────────────────────────────────────────────────
echo "→ Compressing..."
ARCHIVE="/tmp/autonomyx-backup-${DATE}.tar.gz"
tar -czf "$ARCHIVE" -C /tmp "backup-${DATE}"
SIZE=$(du -sh "$ARCHIVE" | cut -f1)
echo "  ✅ Archive: $ARCHIVE ($SIZE)"

# ── Upload to S3 ──────────────────────────────────────────────────────────────
echo "→ Uploading to s3://${S3_BUCKET}/backups/${DATE}..."
aws s3 cp "$ARCHIVE" \
    "s3://${S3_BUCKET}/backups/autonomyx-backup-${DATE}.tar.gz" \
    --endpoint-url "$S3_ENDPOINT" \
    --no-progress

echo "  ✅ Uploaded"

# ── Retention — delete backups older than 30 days ─────────────────────────────
echo "→ Pruning old backups (>30 days)..."
aws s3 ls "s3://${S3_BUCKET}/backups/" \
    --endpoint-url "$S3_ENDPOINT" \
    | awk '{print $4}' \
    | while read -r key; do
        # Extract date from filename
        FILE_DATE=$(echo "$key" | grep -oP '\d{4}-\d{2}-\d{2}' | head -1)
        if [ -n "$FILE_DATE" ]; then
            AGE=$(( ( $(date +%s) - $(date -d "$FILE_DATE" +%s) ) / 86400 ))
            if [ "$AGE" -gt 30 ]; then
                aws s3 rm "s3://${S3_BUCKET}/backups/$key" \
                    --endpoint-url "$S3_ENDPOINT"
                echo "  🗑  Deleted $key (${AGE}d old)"
            fi
        fi
    done

# ── Cleanup ───────────────────────────────────────────────────────────────────
rm -rf "$BACKUP_DIR" "$ARCHIVE"

echo "=== Backup complete — $DATE ==="
