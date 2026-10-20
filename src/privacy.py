"""
Sprint 7 - Issue #63: manejo de datos personales (PII) de candidatos.

- Enmascarado de correos antes de escribirlos en logs.
- Supresión de los archivos de un candidato (derecho de supresión,
  Ley 1581 de 2012 - Habeas Data).
- Purga de archivos más antiguos que el periodo de retención.

La supresión en base de datos vive en profile_repository; este módulo
se encarga de las copias en disco (adjuntos originales y descargas de Gmail).
"""

import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger("privacy")

ROOT_DIR = Path(__file__).resolve().parents[1]
RETENCION_DIAS_POR_DEFECTO = 180

# Subcarpetas de la carpeta de trabajo que contienen CVs originales.
SUBCARPETAS_CON_CVS = ("adjuntos_extraidos", "gmail")


def obtener_carpeta_trabajo() -> Path:
    return Path(os.getenv("DATA_DIR", ROOT_DIR / "data" / "salida"))


def obtener_retencion_dias() -> int:
    valor = os.getenv("RETENTION_DAYS", str(RETENCION_DIAS_POR_DEFECTO))
    dias = int(valor)
    if dias < 1:
        raise ValueError("RETENTION_DAYS debe ser un entero positivo.")
    return dias


def enmascarar_email(email: str | None) -> str:
    """'maria.torres@empresa.com' -> 'm***@empresa.com'."""
    if not email or "@" not in email:
        return "***"
    usuario, dominio = email.rsplit("@", 1)
    return f"{usuario[:1]}***@{dominio}"


def eliminar_archivos_candidato(
    email_id: str,
    carpeta_trabajo: Path | None = None,
) -> int:
    """
    Borra del disco los archivos asociados a un candidato.

    Devuelve cuántos archivos o carpetas se eliminaron.
    """
    if not email_id or Path(email_id).name != email_id:
        raise ValueError(f"email_id no válido: {email_id!r}")

    carpeta_trabajo = Path(carpeta_trabajo or obtener_carpeta_trabajo())
    eliminados = 0

    adjuntos = carpeta_trabajo / "adjuntos_extraidos"
    if adjuntos.is_dir():
        for archivo in adjuntos.glob(f"{email_id}__*"):
            archivo.unlink(missing_ok=True)
            eliminados += 1

    carpeta_gmail = carpeta_trabajo / "gmail" / email_id
    if carpeta_gmail.is_dir():
        shutil.rmtree(carpeta_gmail)
        eliminados += 1

    return eliminados


def purgar_archivos_antiguos(
    dias: int,
    carpeta_trabajo: Path | None = None,
    ahora: float | None = None,
) -> int:
    """
    Elimina CVs en disco con más de ``dias`` de antigüedad.

    Devuelve cuántos archivos o carpetas se eliminaron.
    """
    carpeta_trabajo = Path(carpeta_trabajo or obtener_carpeta_trabajo())
    limite = (ahora if ahora is not None else time.time()) - dias * 86400
    eliminados = 0

    for nombre in SUBCARPETAS_CON_CVS:
        subcarpeta = carpeta_trabajo / nombre
        if not subcarpeta.is_dir():
            continue

        for ruta in subcarpeta.iterdir():
            if ruta.stat().st_mtime >= limite:
                continue
            if ruta.is_dir():
                shutil.rmtree(ruta)
            else:
                ruta.unlink(missing_ok=True)
            eliminados += 1

    logger.info(
        "Purga de archivos: %d elementos con más de %d días eliminados.",
        eliminados,
        dias,
    )
    return eliminados
