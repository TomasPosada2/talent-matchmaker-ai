#!/bin/sh
# Restaura la base de datos desde un backup (Sprint 7 - #67).
#
# Uso (desde el host):
#   docker compose exec backup sh /scripts/restore.sh /backups/db_<fecha>.dump
#
# Reemplaza las tablas existentes (--clean). Detén api, listener y
# maintenance antes de restaurar para que nadie escriba durante el proceso.
set -eu

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
    echo "Uso: restore.sh /backups/db_<fecha>.dump" >&2
    exit 1
fi

pg_restore --list "$1" > /dev/null
pg_restore --clean --if-exists --no-owner --single-transaction --dbname="$PGDATABASE" "$1"

echo "Restauración completada desde $1"
psql --tuples-only --command "SELECT 'perfiles: ' || COUNT(*) FROM profiles;" 2>/dev/null || true
