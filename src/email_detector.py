"""
HU-01: Detección de correos con CV adjunto.

Simula una bandeja de entrada como una carpeta local donde cada subcarpeta
representa un correo:

    inbox_simulado/
        email_001/
            metadata.json   -> {"from": "...", "subject": "...", "date": "...",
                                 "attachments": ["cv_juan.pdf"]}
            cv_juan.pdf
        email_002/
            metadata.json   -> {"attachments": []}
        ...

Esto reemplaza la conexión real a Gmail/IMAP para el Sprint 1, manteniendo la
misma interfaz (un email_detector real solo cambiaría cómo se listan los
correos, no el resto del pipeline).
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("email_detector")

FORMATOS_SOPORTADOS = {".pdf", ".docx"}


@dataclass
class CorreoDetectado:
    email_id: str
    ruta_carpeta: Path
    remitente: str | None
    asunto: str | None
    adjunto_valido: Path | None  # None si no hay adjunto procesable
    estado: str  # "candidato_a_procesar" | "ignorado_sin_adjunto" | "descartado_formato_no_soportado"
    motivo: str | None = None


def _cargar_metadata(carpeta_email: Path) -> dict:
    metadata_path = carpeta_email / "metadata.json"
    if not metadata_path.exists():
        return {}
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("metadata.json ilegible en %s: %s", carpeta_email, e)
        return {}


def detectar_correo(carpeta_email: Path) -> CorreoDetectado:
    """Evalúa un único 'correo' (carpeta) y decide si es candidato a procesar."""
    email_id = carpeta_email.name
    metadata = _cargar_metadata(carpeta_email)
    remitente = metadata.get("from")
    asunto = metadata.get("subject")
    adjuntos = metadata.get("attachments", [])

    if not adjuntos:
        return CorreoDetectado(
            email_id=email_id,
            ruta_carpeta=carpeta_email,
            remitente=remitente,
            asunto=asunto,
            adjunto_valido=None,
            estado="ignorado_sin_adjunto",
            motivo="El correo no tiene archivos adjuntos.",
        )

    # Tomamos el primer adjunto con formato soportado; si ninguno califica,
    # se descarta el correo completo (regla simple para el MVP del Sprint 1).
    for nombre_archivo in adjuntos:
        ruta_adjunto = carpeta_email / nombre_archivo
        extension = ruta_adjunto.suffix.lower()
        if extension in FORMATOS_SOPORTADOS and ruta_adjunto.exists():
            return CorreoDetectado(
                email_id=email_id,
                ruta_carpeta=carpeta_email,
                remitente=remitente,
                asunto=asunto,
                adjunto_valido=ruta_adjunto,
                estado="candidato_a_procesar",
            )

    extensiones_encontradas = [Path(a).suffix.lower() for a in adjuntos]
    return CorreoDetectado(
        email_id=email_id,
        ruta_carpeta=carpeta_email,
        remitente=remitente,
        asunto=asunto,
        adjunto_valido=None,
        estado="descartado_formato_no_soportado",
        motivo=f"Formatos no soportados: {extensiones_encontradas}. "
        f"Soportados: {sorted(FORMATOS_SOPORTADOS)}",
    )


def escanear_bandeja(inbox_dir: Path) -> list[CorreoDetectado]:
    """Escanea todas las subcarpetas de la bandeja simulada y clasifica cada correo."""
    inbox_dir = Path(inbox_dir)
    if not inbox_dir.exists():
        raise FileNotFoundError(f"No existe la bandeja simulada: {inbox_dir}")

    resultados = []
    for carpeta in sorted(p for p in inbox_dir.iterdir() if p.is_dir()):
        resultado = detectar_correo(carpeta)
        resultados.append(resultado)
        logger.info("[%s] %s", resultado.email_id, resultado.estado)
    return resultados
