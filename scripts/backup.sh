#!/bin/sh
# Backup de PostgreSQL y de los CVs en disco (Sprint 7 - #67).
#
# Variables: PGHOST, PGDATABASE, PGUSER, PGPASSWORD (las usa pg_dump),
# BACKUP_DIR (por defecto /backups), BACKUP_RETENTION_DAYS (por defecto 14).
#
# Cada backup se verifica con pg_restore --list antes de darlo por bueno.
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DB_FILE="$BACKUP_DIR/db_${STAMP}.dump"
FILES_FILE="$BACKUP_DIR/files_${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

# 1. Base de datos (formato custom: comprimido y restaurable por tabla).
pg_dump --format=custom --no-owner --file="$DB_FILE.tmp"
pg_restore --list "$DB_FILE.tmp" > /dev/null
mv "$DB_FILE.tmp" "$DB_FILE"

# 2. CVs originales y reportes en disco.
if [ -d /app/data/salida ]; then
    tar -czf "$FILES_FILE.tmp" -C /app/data salida
    mv "$FILES_FILE.tmp" "$FILES_FILE"
fi

# 3. Retención: borrar backups más antiguos que RETENTION_DAYS.
find "$BACKUP_DIR" -maxdepth 1 \( -name 'db_*.dump' -o -name 'files_*.tar.gz' \) \
    -mtime +"$RETENTION_DAYS" -delete

echo "Backup OK: $DB_FILE ($(du -h "$DB_FILE" | cut -f1))"
