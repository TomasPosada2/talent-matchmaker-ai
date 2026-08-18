"""
Orquesta el pipeline completo del Sprint 1:

    HU-01 detectar_correo -> HU-02 extraer_adjunto -> HU-03 extraer_texto
    -> HU-04/HU-05 estructurar_perfil -> HU-06 validar_perfil

HU-07: procesar_lote corre esto sobre todos los correos de la bandeja simulada
       y reporta la tasa de éxito.
HU-08: cada etapa captura sus propios errores; un CV que falla no detiene el
       resto del lote, y todo queda registrado en el log / reporte.
"""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

from . import email_detector, attachment_handler, text_extractor, profile_structurer, schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline")


@dataclass
class ResultadoProcesamiento:
    email_id: str
    estado: str  # "exito" | "ignorado" | "descartado" | "error"
    motivo: str | None = None
    perfil: dict | None = None


def procesar_correo(correo: email_detector.CorreoDetectado, carpeta_trabajo: Path) -> ResultadoProcesamiento:
    if correo.estado == "ignorado_sin_adjunto":
        return ResultadoProcesamiento(correo.email_id, "ignorado", correo.motivo)

    if correo.estado == "descartado_formato_no_soportado":
        return ResultadoProcesamiento(correo.email_id, "descartado", correo.motivo)

    # HU-02: extraer y validar el adjunto
    adjunto = attachment_handler.extraer_adjunto(
        correo.email_id, correo.adjunto_valido, carpeta_trabajo / "adjuntos_extraidos"
    )
    if not adjunto.valido:
        logger.warning("[%s] adjunto inválido: %s", correo.email_id, adjunto.motivo)
        return ResultadoProcesamiento(correo.email_id, "error", adjunto.motivo)

    # HU-03: extraer texto
    texto = text_extractor.extraer_texto(correo.email_id, adjunto.ruta_extraida)
    if not texto.procesable:
        logger.warning("[%s] texto no procesable: %s", correo.email_id, texto.motivo)
        return ResultadoProcesamiento(correo.email_id, "error", texto.motivo)

    # HU-04/HU-05: estructurar perfil con evidencia
    try:
        perfil = profile_structurer.estructurar_perfil(
            email_id=correo.email_id,
            archivo_origen=adjunto.ruta_extraida.name,
            texto_completo=texto.texto_completo,
            lineas=texto.lineas,
        )
    except Exception as e:
        logger.error("[%s] error estructurando perfil: %s", correo.email_id, e)
        return ResultadoProcesamiento(correo.email_id, "error", f"Error estructurando perfil: {e}")

    # HU-06: validar contra el schema
    es_valido, error_schema = schema.validar_perfil(perfil)
    if not es_valido:
        logger.error("[%s] JSON inválido contra schema: %s", correo.email_id, error_schema)
        return ResultadoProcesamiento(correo.email_id, "error", f"JSON inválido: {error_schema}")

    return ResultadoProcesamiento(correo.email_id, "exito", perfil=perfil)


def procesar_lote(inbox_dir: Path, carpeta_trabajo: Path) -> dict:
    """
    HU-07: corre el pipeline completo sobre todos los correos de la bandeja
    simulada y devuelve un reporte con la tasa de éxito y los casos fallidos.
    """
    inbox_dir = Path(inbox_dir)
    carpeta_trabajo = Path(carpeta_trabajo)
    carpeta_trabajo.mkdir(parents=True, exist_ok=True)

    correos = email_detector.escanear_bandeja(inbox_dir)
    resultados = [procesar_correo(c, carpeta_trabajo) for c in correos]

    candidatos = [r for r in resultados if r.estado in ("exito", "error")]
    exitosos = [r for r in resultados if r.estado == "exito"]
    fallidos = [r for r in resultados if r.estado == "error"]
    ignorados = [r for r in resultados if r.estado == "ignorado"]
    descartados = [r for r in resultados if r.estado == "descartado"]

    tasa_exito = (len(exitosos) / len(candidatos)) if candidatos else 0.0

    reporte = {
        "total_correos_en_bandeja": len(resultados),
        "candidatos_a_procesar": len(candidatos),
        "procesados_exitosamente": len(exitosos),
        "fallidos": len(fallidos),
        "ignorados_sin_adjunto": len(ignorados),
        "descartados_formato_no_soportado": len(descartados),
        "tasa_exito": round(tasa_exito, 4),
        "detalle_fallidos": [
            {"email_id": r.email_id, "motivo": r.motivo} for r in fallidos
        ],
        "perfiles": [r.perfil for r in exitosos],
    }

    # Persistir resultados en la carpeta de trabajo
    with open(carpeta_trabajo / "reporte_lote.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    with open(carpeta_trabajo / "perfiles.json", "w", encoding="utf-8") as f:
        json.dump(reporte["perfiles"], f, ensure_ascii=False, indent=2)

    logger.info(
        "Lote procesado: %d/%d exitosos (tasa=%.1f%%), %d fallidos, %d ignorados, %d descartados",
        len(exitosos), len(candidatos), tasa_exito * 100,
        len(fallidos), len(ignorados), len(descartados),
    )

    return reporte
