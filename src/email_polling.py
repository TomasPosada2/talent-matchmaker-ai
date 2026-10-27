"""
Sprint 5 - Issue #44.

Polling de Gmail para detectar correos nuevos sin necesidad
de ejecutar manualmente el pipeline en cada ocasión.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from . import observability
from .gmail_inbox import obtener_correos_gmail, obtener_cuenta_gmail
from .pipeline import procesar_lote

logger = logging.getLogger("email_polling")


def cargar_ids_procesados(ruta_estado: Path) -> set[str]:
    """
    Carga los IDs de correos que ya fueron detectados anteriormente.
    """
    ruta_estado = Path(ruta_estado)

    if not ruta_estado.exists():
        return set()

    try:
        datos = json.loads(
            ruta_estado.read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError):
        logger.warning(
            "No se pudo leer el estado de polling: %s",
            ruta_estado,
        )
        return set()

    return set(datos.get("processed_email_ids", []))


def guardar_ids_procesados(
    ruta_estado: Path,
    ids: set[str],
) -> None:
    """
    Persiste los IDs ya detectados para evitar reprocesarlos.
    """
    ruta_estado = Path(ruta_estado)
    ruta_estado.parent.mkdir(parents=True, exist_ok=True)

    datos = {
        "processed_email_ids": sorted(ids),
    }

    ruta_estado.write_text(
        json.dumps(
            datos,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def ejecutar_polling_una_vez(
    carpeta_descargas: Path,
    carpeta_trabajo: Path,
    ruta_estado: Path,
    max_resultados: int | None = None,
) -> dict | None:
    """
    Ejecuta un ciclo de polling.

    1. Consulta Gmail.
    2. Identifica correos todavía no procesados.
    3. Envía únicamente esos correos al pipeline.
    4. Guarda sus IDs para no procesarlos nuevamente.

    Devuelve None cuando no existen correos nuevos.
    """
    ids_procesados = cargar_ids_procesados(ruta_estado)

    correos = obtener_correos_gmail(
        carpeta_descargas=carpeta_descargas,
        max_resultados=max_resultados,
    )

    correos_nuevos = [
        correo
        for correo in correos
        if correo.email_id not in ids_procesados
    ]

    if not correos_nuevos:
        logger.info("No se detectaron correos nuevos.")
        return None

    logger.info(
        "Se detectaron %d correos nuevos.",
        len(correos_nuevos),
    )

    reporte = procesar_lote(
        inbox_dir=None,
        carpeta_trabajo=carpeta_trabajo,
        correos=correos_nuevos,
    )

    ids_procesados.update(
        correo.email_id
        for correo in correos_nuevos
    )

    guardar_ids_procesados(
        ruta_estado,
        ids_procesados,
    )

    return reporte


def leer_estado_listener(
    ruta_heartbeat: Path,
    max_segundos_sin_ciclo: float,
) -> dict:
    """
    Sprint 8 - #86: estado de la conexión con Gmail para la API y el dashboard.

    ``conectado`` es True solo si el último ciclo terminó bien y es reciente.
    """
    try:
        datos = json.loads(Path(ruta_heartbeat).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "conectado": False,
            "estado": "sin_datos",
            "cuenta": None,
            "ultimo_ciclo": None,
            "segundos_desde_ultimo_ciclo": None,
            "nuevos_ultimo_ciclo": None,
            "procesados_total": None,
            "detalle": "El listener de Gmail no ha completado ningún ciclo.",
        }

    marca = float(datos.get("timestamp", 0))
    antiguedad = max(0.0, time.time() - marca)
    reciente = antiguedad <= max_segundos_sin_ciclo
    estado = datos.get("estado") or "sin_datos"

    detalle = datos.get("detalle")
    if not reciente and estado == "ok":
        detalle = "El listener no reporta actividad reciente."

    return {
        "conectado": estado == "ok" and reciente,
        "estado": estado if reciente else "inactivo",
        "cuenta": datos.get("cuenta"),
        "ultimo_ciclo": datetime.fromtimestamp(marca, timezone.utc).isoformat(),
        "segundos_desde_ultimo_ciclo": round(antiguedad),
        "nuevos_ultimo_ciclo": datos.get("nuevos_ultimo_ciclo"),
        "procesados_total": datos.get("procesados_total"),
        "detalle": detalle,
    }


def ejecutar_listener(
    carpeta_descargas: Path,
    carpeta_trabajo: Path,
    ruta_estado: Path,
    intervalo_segundos: int = 60,
    max_resultados: int | None = None,
    ruta_heartbeat: Path | None = None,
) -> None:
    """
    Mantiene un listener activo consultando Gmail periódicamente.

    El proceso continúa ejecutándose hasta que el usuario
    lo detenga con Ctrl+C.
    """
    logger.info(
        "Listener de Gmail iniciado. Intervalo: %d segundos.",
        intervalo_segundos,
    )

    cuenta = None

    try:
        while True:
            try:
                if cuenta is None:
                    cuenta = obtener_cuenta_gmail()
                    logger.info("Conectado a la bandeja de Gmail de %s.", cuenta)

                reporte = ejecutar_polling_una_vez(
                    carpeta_descargas=carpeta_descargas,
                    carpeta_trabajo=carpeta_trabajo,
                    ruta_estado=ruta_estado,
                    max_resultados=max_resultados,
                )
                if ruta_heartbeat:
                    observability.escribir_heartbeat(
                        ruta_heartbeat,
                        "ok",
                        extra={
                            "cuenta": cuenta,
                            "nuevos_ultimo_ciclo": (
                                reporte["total_correos_en_bandeja"] if reporte else 0
                            ),
                            "procesados_total": len(cargar_ids_procesados(ruta_estado)),
                        },
                    )
            except Exception as exc:
                logger.exception(
                    "Error durante el ciclo de polling de Gmail."
                )
                # Sprint 7 - #66: el listener corre sin supervisión humana.
                observability.alertar(
                    "listener_gmail",
                    f"Falló el ciclo de polling de Gmail: {exc}",
                    clave="listener_gmail",
                )
                if ruta_heartbeat:
                    observability.escribir_heartbeat(
                        ruta_heartbeat,
                        "error",
                        str(exc),
                        extra={"cuenta": cuenta},
                    )

            time.sleep(intervalo_segundos)

    except KeyboardInterrupt:
        logger.info("Listener de Gmail detenido.")