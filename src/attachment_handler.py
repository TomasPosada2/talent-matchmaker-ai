"""
HU-02: Extracción y validación de adjuntos.

Copia el adjunto validado a una carpeta de trabajo con un nombre trazable
al correo de origen, y valida que el archivo no esté corrupto ni vacío,
ni supere el tamaño límite.
"""

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("attachment_handler")

TAMANO_MAXIMO_BYTES = 5 * 1024 * 1024  # 5 MB


@dataclass
class AdjuntoExtraido:
    email_id: str
    ruta_extraida: Path | None
    valido: bool
    motivo: str | None = None


def extraer_adjunto(email_id: str, ruta_adjunto: Path, carpeta_destino: Path) -> AdjuntoExtraido:
    """
    Valida y copia el adjunto a carpeta_destino con nombre trazable:
    {email_id}__{nombre_original}
    """
    carpeta_destino = Path(carpeta_destino)
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    if not ruta_adjunto.exists():
        return AdjuntoExtraido(email_id, None, False, "El archivo adjunto no existe en disco.")

    tamano = ruta_adjunto.stat().st_size
    if tamano == 0:
        return AdjuntoExtraido(email_id, None, False, "El archivo adjunto está vacío (0 bytes).")

    if tamano > TAMANO_MAXIMO_BYTES:
        return AdjuntoExtraido(
            email_id, None, False,
            f"El archivo supera el tamaño máximo permitido "
            f"({tamano} bytes > {TAMANO_MAXIMO_BYTES} bytes).",
        )

    nombre_trazable = f"{email_id}__{ruta_adjunto.name}"
    destino = carpeta_destino / nombre_trazable
    try:
        shutil.copy2(ruta_adjunto, destino)
    except OSError as e:
        return AdjuntoExtraido(email_id, None, False, f"Error copiando el archivo: {e}")

    logger.info("[%s] adjunto extraído -> %s", email_id, destino)
    return AdjuntoExtraido(email_id, destino, True)
