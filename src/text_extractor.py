"""
HU-03: Extracción de texto crudo del CV.

Extrae el texto completo de PDF o DOCX, conservando el orden de las
secciones/párrafos. También detecta el caso "PDF escaneado sin texto"
(HU-08) para marcarlo como no procesable en este sprint (sin OCR).
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from docx import Document

logger = logging.getLogger("text_extractor")


@dataclass
class TextoExtraido:
    email_id: str
    texto_completo: str
    lineas: list[str]  # texto dividido por línea/párrafo, en orden original
    procesable: bool
    motivo: str | None = None


def _extraer_docx(ruta: Path) -> list[str]:
    doc = Document(ruta)
    lineas = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    # Incluir texto de tablas, si las hay (algunos CVs usan tablas para layout)
    for tabla in doc.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                texto_celda = celda.text.strip()
                if texto_celda:
                    lineas.append(texto_celda)
    return lineas


def _extraer_pdf(ruta: Path) -> list[str]:
    lineas = []
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text() or ""
            for linea in texto_pagina.split("\n"):
                linea = linea.strip()
                if linea:
                    lineas.append(linea)
    return lineas


def extraer_texto(email_id: str, ruta_archivo: Path) -> TextoExtraido:
    extension = ruta_archivo.suffix.lower()
    try:
        if extension == ".docx":
            lineas = _extraer_docx(ruta_archivo)
        elif extension == ".pdf":
            lineas = _extraer_pdf(ruta_archivo)
        else:
            return TextoExtraido(
                email_id, "", [], False,
                f"Extensión no soportada para extracción de texto: {extension}",
            )
    except Exception as e:  # archivo corrupto, formato inesperado, etc.
        logger.error("[%s] error extrayendo texto: %s", email_id, e)
        return TextoExtraido(email_id, "", [], False, f"Error al leer el archivo: {e}")

    if not lineas:
        # HU-08: probablemente un PDF escaneado (imagen) sin capa de texto.
        return TextoExtraido(
            email_id, "", [], False,
            "No se pudo extraer texto legible (posible CV escaneado como imagen). "
            "No procesable en este sprint: sin OCR.",
        )

    texto_completo = "\n".join(lineas)
    return TextoExtraido(email_id, texto_completo, lineas, True)
