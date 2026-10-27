"""
Sprint 7 - Issue #66: monitoreo y alertas.

- Logging configurable (texto o JSON) mediante LOG_LEVEL y LOG_FORMAT.
- Métricas Prometheus de la API (peticiones, latencia, errores) y del
  pipeline (CVs procesados por estado, duración de lotes).
- Alertas a un webhook (Slack, Teams, etc.) mediante ALERT_WEBHOOK_URL,
  con supresión de repeticiones para no saturar el canal.
- Heartbeat del listener de Gmail para detectar si dejó de correr.
"""

import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from prometheus_client import Counter, Histogram

logger = logging.getLogger("observability")

SILENCIO_ALERTAS_SEGUNDOS = 10 * 60

# ------------------------------------------------------------
# Métricas
# ------------------------------------------------------------

PETICIONES_HTTP = Counter(
    "tm_http_requests_total",
    "Peticiones HTTP atendidas por la API.",
    ["method", "route", "status"],
)

LATENCIA_HTTP = Histogram(
    "tm_http_request_duration_seconds",
    "Latencia de las peticiones HTTP de la API.",
    ["method", "route"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120),
)

CVS_PROCESADOS = Counter(
    "tm_pipeline_cvs_total",
    "Correos procesados por el pipeline, por estado final.",
    ["estado"],
)

DURACION_LOTE = Histogram(
    "tm_pipeline_batch_duration_seconds",
    "Duración de cada lote del pipeline.",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1800),
)

ALERTAS_ENVIADAS = Counter(
    "tm_alerts_total",
    "Alertas enviadas al webhook.",
    ["tipo"],
)


# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

class FormatoJson(logging.Formatter):
    """Una línea JSON por evento, fácil de indexar en cualquier agregador."""

    def format(self, record: logging.LogRecord) -> str:
        evento = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            evento["exception"] = self.formatException(record.exc_info)
        return json.dumps(evento, ensure_ascii=False)


def configurar_logging() -> None:
    """Configura el logging raíz según LOG_LEVEL y LOG_FORMAT (text|json)."""
    nivel = os.getenv("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()

    if os.getenv("LOG_FORMAT", "text").lower() == "json":
        handler.setFormatter(FormatoJson())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    raiz = logging.getLogger()
    raiz.handlers[:] = [handler]
    raiz.setLevel(nivel)


# ------------------------------------------------------------
# Alertas
# ------------------------------------------------------------

_ultima_alerta: dict[str, float] = {}
_lock_alertas = threading.Lock()


def _debe_enviarse(clave: str, ahora: float) -> bool:
    with _lock_alertas:
        ultima = _ultima_alerta.get(clave)
        if ultima is not None and ahora - ultima < SILENCIO_ALERTAS_SEGUNDOS:
            return False
        _ultima_alerta[clave] = ahora
        return True


def reiniciar_alertas() -> None:
    with _lock_alertas:
        _ultima_alerta.clear()


def alertar(tipo: str, mensaje: str, clave: str | None = None) -> bool:
    """
    Envía una alerta al webhook configurado en ALERT_WEBHOOK_URL.

    El cuerpo es {"text": "..."}, compatible con Slack y Microsoft Teams.
    La misma ``clave`` no se repite durante SILENCIO_ALERTAS_SEGUNDOS.
    Nunca lanza excepciones: una alerta fallida no debe tumbar el servicio.

    Devuelve True si la alerta se envió.
    """
    logger.warning("ALERTA [%s] %s", tipo, mensaje)

    url = os.getenv("ALERT_WEBHOOK_URL")
    if not url:
        return False

    if not _debe_enviarse(clave or f"{tipo}:{mensaje}", time.monotonic()):
        return False

    entorno = os.getenv("APP_ENV", "local")

    try:
        respuesta = httpx.post(
            url,
            json={"text": f"[Talent Matchmaker · {entorno}] {tipo}: {mensaje}"},
            timeout=5,
        )
        respuesta.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("No fue posible enviar la alerta %s: %s", tipo, exc)
        return False

    ALERTAS_ENVIADAS.labels(tipo=tipo).inc()
    return True


def umbral_peticion_lenta_segundos() -> float:
    return float(os.getenv("SLOW_REQUEST_SECONDS", "30"))


def umbral_tasa_fallos_lote() -> float:
    return float(os.getenv("BATCH_FAILURE_ALERT_RATIO", "0.5"))


# ------------------------------------------------------------
# Heartbeat del listener
# ------------------------------------------------------------

def escribir_heartbeat(
    ruta: Path,
    estado: str,
    detalle: str | None = None,
    extra: dict | None = None,
) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(
            {
                **(extra or {}),
                "timestamp": time.time(),
                "estado": estado,
                "detalle": detalle,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def heartbeat_vigente(ruta: Path, max_segundos: float) -> bool:
    """True si el heartbeat existe y es más reciente que ``max_segundos``."""
    try:
        datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return time.time() - float(datos.get("timestamp", 0)) <= max_segundos
