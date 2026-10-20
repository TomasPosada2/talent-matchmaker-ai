# Runbook de operación

Guía para levantar, operar y recuperar Talent Matchmaker AI con Docker
Compose. Todos los comandos se ejecutan desde la raíz del repositorio.

## 1. Requisitos

- Docker Engine 24 o superior con Docker Compose v2 (en Windows o macOS,
  Docker Desktop).
- 4 GB de RAM libres. ClamAV usa cerca de 1,5 GB.
- Para producción: una VM Linux con los puertos 80 y 443 abiertos y un
  dominio que apunte a ella.

## 2. Primer arranque (local o servidor)

```bash
cp .env.example .env
# Completa POSTGRES_PASSWORD, JWT_SECRET (≥ 32 caracteres) y DEMO_ADMIN_PASSWORD.
# JWT_SECRET: python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build
docker compose ps                    # todos los servicios deben quedar healthy
```

| Servicio | Qué hace | Puerto en el host |
|---|---|---|
| `db` | PostgreSQL 16 | — (solo red interna) |
| `clamav` | Antivirus clamd | — |
| `api` | FastAPI | `127.0.0.1:8000` |
| `dashboard` | Streamlit | `127.0.0.1:8501` |
| `maintenance` | Purga diaria de datos vencidos (#63) | — |
| `backup` | Backup diario de Postgres y archivos (#67) | — |

Los puertos solo escuchan en `127.0.0.1`. Para exponer el sistema a
internet se usa el proxy con HTTPS (sección 4).

### Datos de demostración

```bash
docker compose run --rm api python scripts/seed_demo.py
```

Genera 25 correos sintéticos y los pasa por el pipeline completo (con
ClamAV). Además crea el admin `DEMO_ADMIN_EMAIL` y una vacante de ejemplo.
Resultado esperado: `Pipeline: 20/21 CVs procesados.`

Abre http://localhost:8501 e inicia sesión con `DEMO_ADMIN_EMAIL` /
`DEMO_ADMIN_PASSWORD`. En **Rankings**, el modo *Demostración gratuita*
funciona sin `ANTHROPIC_API_KEY`.

### Cuentas de usuario

El registro no es público (#61). Hay dos formas de crear cuentas:

```bash
# Primer admin, o promover una cuenta existente a admin:
docker compose run --rm api python scripts/create_admin.py admin@empresa.com
```

Después, un admin crea recruiters desde el dashboard (sección **Usuarios**)
o con `POST /auth/register`.

## 3. Gmail (opcional)

1. En Google Cloud, crea credenciales OAuth de tipo *Desktop app* y descarga
   `credentials.json` en `./secrets/`.
2. La primera autorización abre un navegador, así que se hace en el host:
   ```bash
   GMAIL_CREDENTIALS_PATH=secrets/credentials.json GMAIL_TOKEN_PATH=secrets/token.json \
     python -c "from src.gmail_auth import obtener_credenciales_gmail as c; c()"
   ```
3. En Linux, da escritura al usuario del contenedor: `sudo chown -R 10001 secrets`.
4. Levanta el listener: `docker compose --profile gmail up -d`.

El listener revisa la bandeja cada `POLL_INTERVAL_SECONDS` y queda
*unhealthy* si pasa 5 minutos sin completar un ciclo.

## 4. Producción con HTTPS

```bash
# En .env: APP_ENV=produccion, DOMAIN=talento.empresa.com, LOG_FORMAT=json, ALERT_WEBHOOK_URL=...
docker compose --profile proxy up -d
```

Caddy obtiene el certificado de Let's Encrypt y publica solo el dashboard.
La API, la base de datos y ClamAV no se exponen.

Checklist antes de abrir a usuarios:

- [ ] `.env` con secretos únicos y fuera del repositorio.
- [ ] `ENABLE_API_DOCS` sin definir o en `false`.
- [ ] `ALERT_WEBHOOK_URL` configurado y probado (sección 6).
- [ ] Backups copiados fuera del servidor (sección 5).
- [ ] Volumen de Postgres sobre un disco cifrado (`docs/privacy.md`).
- [ ] Aviso de privacidad aprobado por asesoría legal (`docs/privacy.md`).

### Actualizar a una nueva versión

```bash
git pull
docker compose up -d --build
docker compose ps
```

Las tablas se crean o migran solas al arrancar (`CREATE TABLE IF NOT EXISTS`
y `ADD COLUMN IF NOT EXISTS`). Si algo falla, vuelve al commit anterior con
`git checkout <commit>` y repite `docker compose up -d --build`.

## 5. Backups y recuperación ante desastres (#67)

**Qué se respalda:** el servicio `backup` corre `scripts/backup.sh` cada
`BACKUP_INTERVAL_SECONDS` (24 h por defecto):

- `backups/db_<fecha>.dump`: `pg_dump` en formato custom, verificado con
  `pg_restore --list` antes de darlo por bueno.
- `backups/files_<fecha>.tar.gz`: CVs originales y reportes en disco.
- Se borran los backups con más de `BACKUP_RETENTION_DAYS` días (14 por defecto).
- Si un backup falla, se envía una alerta a `ALERT_WEBHOOK_URL`.

**Objetivos:**

| Métrica | Objetivo | Medido el 2026-10-20 |
|---|---|---|
| RPO (pérdida máxima de datos) | 24 h (intervalo de backup) | — |
| RTO (tiempo de restauración de la base) | < 15 min | 2 s con 20 perfiles |

**Copia fuera del servidor.** `./backups` vive en el mismo disco que la base
de datos: si se pierde el servidor, se pierden ambos. En producción,
sincroniza esa carpeta a otro lugar (S3, Azure Blob, Google Drive,
etc.), por ejemplo con un cron del host:
`rclone sync ./backups remoto:talent-backups`.

### Backup manual

```bash
docker compose exec backup sh /scripts/backup.sh
```

### Restaurar la base de datos

```bash
docker compose stop api dashboard listener maintenance
docker compose exec backup sh /scripts/restore.sh /backups/db_<fecha>.dump
docker compose start api dashboard maintenance      # y listener, si se usa
```

En Git Bash (Windows), antepón `MSYS_NO_PATHCONV=1` para que no convierta
las rutas `/backups/...`.

### Restaurar los CVs en disco

```bash
docker compose run --rm -v "$PWD/backups:/backups:ro" api \
  tar -xzf /backups/files_<fecha>.tar.gz -C /app/data
```

### Simulacro (realizarlo cada trimestre)

Se ejecutó el 2026-10-20 sobre el entorno local:

1. Backup con 20 perfiles.
2. Se borraron 7 perfiles para simular la pérdida: quedaron 13.
3. Se restauró el backup: volvieron a ser 20, en 2 segundos.

## 6. Monitoreo y diagnóstico

Ver `docs/monitoring.md`. Comandos frecuentes:

```bash
docker compose ps                         # estado y healthchecks
docker compose logs -f api                # logs en vivo
curl -s localhost:8000/health/ready       # API + base de datos
curl -s localhost:8000/metrics | head     # métricas Prometheus
docker compose --profile monitoring up -d # Prometheus en localhost:9090
```

Para probar el canal de alertas:

```bash
docker compose exec api python -c "from src.observability import alertar; print(alertar('prueba', 'canal de alertas OK'))"
```

| Síntoma | Causa probable | Acción |
|---|---|---|
| `api` unhealthy, `/health/ready` da 503 | Postgres caído o `DATABASE_URL` incorrecta | `docker compose logs db`; revisar `.env` |
| Todos los CVs fallan con "Escaneo de seguridad fallido" | `clamav` caído o descargando firmas | `docker compose logs clamav`; esperar a que quede healthy |
| `listener` unhealthy | Token de Gmail vencido o revocado | Repetir el paso 2 de la sección 3 |
| Ranking con IA da error 500 | Falta `ANTHROPIC_API_KEY` o no hay saldo | Revisar `.env`; mientras tanto, usar el modo demostración |
| Login devuelve 429 | 5 intentos fallidos en 15 minutos | Esperar, o reiniciar la API (el contador vive en memoria) |

## 7. Datos personales

Solicitudes de titulares (consulta o supresión) y retención: ver
`docs/privacy.md`, sección 4.
