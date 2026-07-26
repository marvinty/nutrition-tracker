#!/bin/bash
# Daily SQLite backup: WAL-safe dump, local rotation, offsite sync to Proton Drive.
# Runs on the Proxmox LXC host (not inside the api container) via cron — see
# scripts/README.md for the crontab line and one-time setup.
set -euo pipefail

VOLUME_NAME="nutrition-tracker_macromic_data"
BACKUP_DIR="/root/macromic-backups"
KEEP_DAYS=7
RCLONE_REMOTE="proton:macromic-backups"

DB_PATH="$(docker volume inspect "$VOLUME_NAME" --format '{{ .Mountpoint }}')/macromic.db"
mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/macromic-$TIMESTAMP.db"

# .backup goes through SQLite's own backup API, which is WAL-aware — unlike a plain
# `cp`, it can't catch the main db file mid-write or miss commits still sitting in
# the -wal file.
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

find "$BACKUP_DIR" -name 'macromic-*.db' -mtime "+$KEEP_DAYS" -delete

rclone copy "$BACKUP_FILE" "$RCLONE_REMOTE/"
