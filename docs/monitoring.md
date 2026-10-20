# Monitoreo y alertas — Sprint 7, issue #66

Hay dos niveles. El primero funciona sin instalar nada adicional; el segundo
añade Prometheus para tener tableros e históricos.

## Nivel 1: alertas directas a un webhook (sin infraestructura extra)

Basta con definir `ALERT_WEBHOOK_URL` con un webhook entrante de Slack o de
Microsoft Teams. El cuerpo enviado es `{"text": "..."}`.

| Evento | Quién lo detecta | Umbral (variable) |
|---|---|---|
| Respuesta 5xx de la API, incluidas excepciones no controladas | Middleware de `src/api.py` | — |
| Petición lenta | Middleware de `src/api.py` | `SLOW_REQUEST_SECONDS` (30 s por defecto) |
| Lote del pipeline con demasiados CVs fallidos | `src/pipeline.py` | `BATCH_FAILURE_ALERT_RATIO` (0.5 por defecto) |
| Fallo de un ciclo del listener de Gmail (token vencido, red, etc.) | `src/email_polling.py` | — |

Cada tipo de alerta se envía como máximo una vez cada 10 minutos, para no
inundar el canal. Si el webhook falla, se registra en el log y el servicio
sigue funcionando.

## Nivel 2: Prometheus

```bash
docker compose --profile monitoring up -d
```

Prometheus queda en `http://localhost:9090`. Lee `GET /metrics` de la API y
carga las reglas de `monitoring/alerts.yml`. Si `METRICS_TOKEN` está definido,
el endpoint exige `Authorization: Bearer <token>`; en ese caso hay que añadir
`authorization.credentials` en `monitoring/prometheus.yml`.

| Métrica | Tipo | Etiquetas |
|---|---|---|
| `tm_http_requests_total` | counter | `method`, `route`, `status` |
| `tm_http_request_duration_seconds` | histogram | `method`, `route` |
| `tm_pipeline_cvs_total` | counter | `estado` (`exito`, `error`, `ignorado`, `descartado`) |
| `tm_pipeline_batch_duration_seconds` | histogram | — |
| `tm_alerts_total` | counter | `tipo` |

Las métricas del pipeline se publican desde el proceso que lo ejecuta. El
listener corre en su propio contenedor, así que su salud se vigila por
heartbeat (ver abajo) y por las alertas del nivel 1.

## Health checks

| Endpoint / archivo | Qué responde | Lo usa |
|---|---|---|
| `GET /health` | El proceso de la API responde. | Dashboard (pantalla Inicio) |
| `GET /health/ready` | La API puede consultar PostgreSQL; si no, devuelve `503`. | Healthcheck de Docker del servicio `api` |
| `data/salida/listener_heartbeat.json` | Último ciclo del listener (`ok` / `error`). | Healthcheck de Docker del servicio `listener`: queda *unhealthy* si no hay ciclo en 5 minutos. |

## Logs

- `LOG_FORMAT=json` emite una línea JSON por evento (`ts`, `level`,
  `logger`, `message`), lista para Loki, CloudWatch, Datadog, etc.
- La API registra cada petición con método, ruta, estado y duración.
- Los correos de recruiters se enmascaran (ver `docs/privacy.md`).
- `docker compose logs -f api listener` muestra los logs en vivo.
