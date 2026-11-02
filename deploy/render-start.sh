#!/bin/sh
# Arranque en Render: un solo contenedor con la API y el dashboard.
# La API escucha solo en localhost; el dashboard se publica en $PORT.
set -e

uvicorn src.api:app --host 127.0.0.1 --port 8000 --proxy-headers &

# Espera a que la API responda antes de abrir el dashboard.
for _ in $(seq 1 60); do
    curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && break
    sleep 1
done

exec streamlit run dashboard/main.py \
    --server.address=0.0.0.0 \
    --server.port="${PORT:-8501}" \
    --server.headless=true \
    --browser.gatherUsageStats=false
