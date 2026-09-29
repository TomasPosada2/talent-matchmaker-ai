"""
Orquesta el pipeline completo de procesamiento de candidatos.

Sprint 1:
    HU-01 detectar_correo -> HU-02 extraer_adjunto -> HU-03 extraer_texto
    -> HU-04/HU-05 estructurar_perfil -> HU-06 validar_perfil.

Sprint 5 - Issue #46:
    Los perfiles procesados correctamente se persisten en PostgreSQL
    en lugar de almacenarse en perfiles.json.

Sprint 5 - Issue #11:
    El pipeline puede recibir correos provenientes de Gmail manteniendo
    compatibilidad con la bandeja local utilizada por las pruebas.

Sprint 5 - Issue #45:
    Los adjuntos se escanean contra malware antes de entrar al pipeline
    de extracción de texto.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from . import (
    attachment_handler,
    email_detector,
    malware_scanner,
    profile_repository,
    profile_structurer,
    schema,
    text_extractor,
)

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


def procesar_correo(
    correo: email_detector.CorreoDetectado,
    carpeta_trabajo: Path,
) -> ResultadoProcesamiento:
    if correo.estado == "ignorado_sin_adjunto":
        return ResultadoProcesamiento(
            correo.email_id,
            "ignorado",
            correo.motivo,
        )

    if correo.estado == "descartado_formato_no_soportado":
        return ResultadoProcesamiento(
            correo.email_id,
            "descartado",
            correo.motivo,
        )

    # HU-02: extraer y validar el adjunto
    adjunto = attachment_handler.extraer_adjunto(
        correo.email_id,
        correo.adjunto_valido,
        carpeta_trabajo / "adjuntos_extraidos",
    )

    if not adjunto.valido:
        logger.warning(
            "[%s] adjunto inválido: %s",
            correo.email_id,
            adjunto.motivo,
        )
        return ResultadoProcesamiento(
            correo.email_id,
            "error",
            adjunto.motivo,
        )

    # Sprint 5 - Issue #45:
    # Escanear el adjunto antes de permitir la extracción de texto.
    try:
        malware_scanner.validar_archivo_seguro(
            adjunto.ruta_extraida
        )
    except (ValueError, RuntimeError, FileNotFoundError) as e:
        logger.warning(
            "[%s] adjunto bloqueado por seguridad: %s",
            correo.email_id,
            e,
        )
        return ResultadoProcesamiento(
            correo.email_id,
            "error",
            f"Escaneo de seguridad fallido: {e}",
        )

    # HU-03: extraer texto
    texto = text_extractor.extraer_texto(
        correo.email_id,
        adjunto.ruta_extraida,
    )

    if not texto.procesable:
        logger.warning(
            "[%s] texto no procesable: %s",
            correo.email_id,
            texto.motivo,
        )
        return ResultadoProcesamiento(
            correo.email_id,
            "error",
            texto.motivo,
        )

    # HU-04/HU-05: estructurar perfil con evidencia
    try:
        perfil = profile_structurer.estructurar_perfil(
            email_id=correo.email_id,
            archivo_origen=adjunto.ruta_extraida.name,
            texto_completo=texto.texto_completo,
            lineas=texto.lineas,
        )
    except Exception as e:
        logger.error(
            "[%s] error estructurando perfil: %s",
            correo.email_id,
            e,
        )
        return ResultadoProcesamiento(
            correo.email_id,
            "error",
            f"Error estructurando perfil: {e}",
        )

    # HU-06: validar contra el schema
    es_valido, error_schema = schema.validar_perfil(perfil)

    if not es_valido:
        logger.error(
            "[%s] perfil inválido contra schema: %s",
            correo.email_id,
            error_schema,
        )
        return ResultadoProcesamiento(
            correo.email_id,
            "error",
            f"Perfil inválido: {error_schema}",
        )

    return ResultadoProcesamiento(
        correo.email_id,
        "exito",
        perfil=perfil,
    )


def procesar_lote(
    inbox_dir: Path | None,
    carpeta_trabajo: Path,
    correos: list[email_detector.CorreoDetectado] | None = None,
) -> dict:
    """
    Procesa todos los correos de una bandeja.

    Si se proporciona ``correos``, procesa directamente esa lista.
    Esto permite utilizar correos obtenidos desde Gmail.

    Si ``correos`` es None, mantiene el comportamiento anterior y
    escanea ``inbox_dir``.

    Sprint 5 #46:
    Los perfiles válidos se almacenan en PostgreSQL.
    El reporte operativo del lote continúa guardándose como JSON.
    """
    carpeta_trabajo = Path(carpeta_trabajo)
    carpeta_trabajo.mkdir(parents=True, exist_ok=True)

    if correos is None:
        if inbox_dir is None:
            raise ValueError(
                "Debe proporcionarse inbox_dir o una lista de correos."
            )

        inbox_dir = Path(inbox_dir)
        correos = email_detector.escanear_bandeja(inbox_dir)

    resultados = [
        procesar_correo(correo, carpeta_trabajo)
        for correo in correos
    ]

    candidatos = [
        resultado
        for resultado in resultados
        if resultado.estado in ("exito", "error")
    ]

    exitosos = [
        resultado
        for resultado in resultados
        if resultado.estado == "exito"
    ]

    fallidos = [
        resultado
        for resultado in resultados
        if resultado.estado == "error"
    ]

    ignorados = [
        resultado
        for resultado in resultados
        if resultado.estado == "ignorado"
    ]

    descartados = [
        resultado
        for resultado in resultados
        if resultado.estado == "descartado"
    ]

    tasa_exito = (
        len(exitosos) / len(candidatos)
        if candidatos
        else 0.0
    )

    reporte = {
        "total_correos_en_bandeja": len(resultados),
        "candidatos_a_procesar": len(candidatos),
        "procesados_exitosamente": len(exitosos),
        "fallidos": len(fallidos),
        "ignorados_sin_adjunto": len(ignorados),
        "descartados_formato_no_soportado": len(descartados),
        "tasa_exito": round(tasa_exito, 4),
        "detalle_fallidos": [
            {
                "email_id": resultado.email_id,
                "motivo": resultado.motivo,
            }
            for resultado in fallidos
        ],
        "perfiles": [
            resultado.perfil
            for resultado in exitosos
        ],
    }

    # Sprint 5 - Issue #46
    # Persistencia relacional de perfiles.
    profile_repository.crear_tablas()

    for resultado in exitosos:
        try:
            profile_repository.guardar_perfil(
                resultado.perfil
            )
        except Exception as e:
            logger.error(
                "[%s] error guardando perfil en PostgreSQL: %s",
                resultado.email_id,
                e,
            )
            raise

    # El reporte operativo continúa siendo un artefacto JSON.
    with open(
        carpeta_trabajo / "reporte_lote.json",
        "w",
        encoding="utf-8",
    ) as archivo_reporte:
        json.dump(
            reporte,
            archivo_reporte,
            ensure_ascii=False,
            indent=2,
        )

    logger.info(
        "Lote procesado: %d/%d exitosos (tasa=%.1f%%), "
        "%d fallidos, %d ignorados, %d descartados",
        len(exitosos),
        len(candidatos),
        tasa_exito * 100,
        len(fallidos),
        len(ignorados),
        len(descartados),
    )

    return reporte