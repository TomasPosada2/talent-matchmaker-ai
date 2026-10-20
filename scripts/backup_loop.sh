#!/bin/sh
# Ejecuta scripts/backup.sh periódicamente y alerta si falla (Sprint 7 - #67).
INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"

alertar() {
    echo "ALERTA: $1" >&2
    if [ -n "${ALERT_WEBHOOK_URL:-}" ]; then
        wget -q -O /dev/null --header 'Content-Type: application/json' \
            --post-data "{\"text\": \"[Talent Matchmaker] backup: $1\"}" \
            "$ALERT_WEBHOOK_URL" || echo "No fue posible enviar la alerta." >&2
    fi
}

while true; do
    if ! sh /scripts/backup.sh; then
        alertar "falló el backup de $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    fi
    sleep "$INTERVAL"
done
