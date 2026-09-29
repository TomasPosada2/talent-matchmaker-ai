"""
Sprint 5 - Issue #44.

Polling de Gmail para detectar correos nuevos sin necesidad
de ejecutar manualmente el pipeline en cada ocasión.
"""

import json
import logging
from pathlib import Path

from .gmail_inbox import obtener_correos_gmail
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
    max_resultados: int = 50,
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

def ejecutar_listener(
    carpeta_descargas: Path,
    carpeta_trabajo: Path,
    ruta_estado: Path,
    intervalo_segundos: int = 60,
    max_resultados: int = 50,
) -> None:
    """
    Mantiene un listener activo consultando Gmail periódicamente.

    El proceso continúa ejecutándose hasta que el usuario
    lo detenga con Ctrl+C.
    """
    import time

    logger.info(
        "Listener de Gmail iniciado. Intervalo: %d segundos.",
        intervalo_segundos,
    )

    try:
        while True:
            try:
                ejecutar_polling_una_vez(
                    carpeta_descargas=carpeta_descargas,
                    carpeta_trabajo=carpeta_trabajo,
                    ruta_estado=ruta_estado,
                    max_resultados=max_resultados,
                )
            except Exception:
                logger.exception(
                    "Error durante el ciclo de polling de Gmail."
                )

            time.sleep(intervalo_segundos)

    except KeyboardInterrupt:
        logger.info("Listener de Gmail detenido.")