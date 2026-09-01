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
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

logger = logging.getLogger("text_extractor")


@dataclass
class TextoExtraido:
    email_id: str
    texto_completo: str
    lineas: list[str]  # texto dividido por línea/párrafo, en orden original
    procesable: bool
    motivo: str | None = None


def _iter_bloques(doc: Document):
    """
    BUG-01: iterar doc.paragraphs y doc.tables por separado pierde la posición
    real de las tablas en el documento (siempre quedan al final). Se recorre
    el XML del cuerpo en orden para intercalar párrafos y tablas tal como
    aparecen realmente en el CV.
    """
    for hijo in doc.element.body.iterchildren():
        if hijo.tag == qn("w:p"):
            yield Paragraph(hijo, doc)
        elif hijo.tag == qn("w:tbl"):
            yield Table(hijo, doc)


def _extraer_docx(ruta: Path) -> list[str]:
    doc = Document(ruta)
    lineas = []
    for bloque in _iter_bloques(doc):
        if isinstance(bloque, Paragraph):
            texto = bloque.text.strip()
            if texto:
                lineas.append(texto)
        else:  # Table
            for fila in bloque.rows:
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
