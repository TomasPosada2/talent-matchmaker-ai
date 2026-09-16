"""
HU-03: Extracción de texto crudo del CV.

Extrae el texto completo de PDF o DOCX, conservando el orden de las
secciones/párrafos.

Sprint 4:
HU-15: soporte OCR para CVs PDF escaneados como imagen.

Si un PDF no contiene una capa de texto utilizable, el extractor intenta
recuperar el contenido mediante OCR con Tesseract.
"""

import logging
import shutil
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
    lineas: list[str]
    procesable: bool
    motivo: str | None = None


def _iter_bloques(doc: Document):
    """
    BUG-01: iterar doc.paragraphs y doc.tables por separado pierde la
    posición real de las tablas en el documento.

    Se recorre el XML del cuerpo en orden para intercalar párrafos y
    tablas tal como aparecen realmente en el CV.
    """
    for hijo in doc.element.body.iterchildren():
        if hijo.tag == qn("w:p"):
            yield Paragraph(hijo, doc)

        elif hijo.tag == qn("w:tbl"):
            yield Table(hijo, doc)


def _extraer_docx(ruta: Path) -> list[str]:
    """Extrae texto de un archivo DOCX conservando el orden."""

    doc = Document(ruta)
    lineas = []

    for bloque in _iter_bloques(doc):
        if isinstance(bloque, Paragraph):
            texto = bloque.text.strip()

            if texto:
                lineas.append(texto)

        else:
            for fila in bloque.rows:
                for celda in fila.cells:
                    texto_celda = celda.text.strip()

                    if texto_celda:
                        lineas.append(texto_celda)

    return lineas


def _extraer_pdf(ruta: Path) -> list[str]:
    """
    Intenta extraer primero la capa de texto normal del PDF.
    """

    lineas = []

    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            texto_pagina = pagina.extract_text() or ""

            for linea in texto_pagina.split("\n"):
                linea = linea.strip()

                if linea:
                    lineas.append(linea)

    return lineas


def _configurar_tesseract():
    """
    Localiza Tesseract.

    Primero intenta encontrarlo en PATH. En Windows también comprueba
    la ubicación de instalación habitual.
    """

    import pytesseract

    ejecutable = shutil.which("tesseract")

    if ejecutable:
        pytesseract.pytesseract.tesseract_cmd = ejecutable
        return

    ruta_windows = Path(
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if ruta_windows.exists():
        pytesseract.pytesseract.tesseract_cmd = str(ruta_windows)
        return

    raise RuntimeError(
        "Tesseract OCR no está instalado o no se pudo localizar."
    )


def _extraer_pdf_con_ocr(ruta: Path) -> list[str]:
    """
    HU-15: convierte cada página del PDF escaneado en una imagen
    y utiliza Tesseract OCR para recuperar su contenido.
    """

    try:
        import fitz
        import pytesseract
        from PIL import Image

    except ImportError as exc:
        raise RuntimeError(
            "Las dependencias de OCR no están instaladas."
        ) from exc

    _configurar_tesseract()

    lineas = []

    documento = fitz.open(ruta)

    try:
        for pagina in documento:
            # Renderizar a mayor resolución mejora el reconocimiento OCR.
            matriz = fitz.Matrix(2, 2)

            pixmap = pagina.get_pixmap(
                matrix=matriz,
                alpha=False,
            )

            imagen = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            # Actualmente el proyecto garantiza el paquete de idioma inglés.
            texto_ocr = pytesseract.image_to_string(
                imagen,
                lang="eng",
            )

            for linea in texto_ocr.splitlines():
                linea = linea.strip()

                if linea:
                    lineas.append(linea)

    finally:
        documento.close()

    return lineas


def extraer_texto(
    email_id: str,
    ruta_archivo: Path,
) -> TextoExtraido:
    """
    Extrae el contenido textual de un CV.

    DOCX:
        extracción estructurada normal.

    PDF:
        1. intenta extraer la capa de texto.
        2. si no encuentra texto, intenta OCR.
    """

    extension = ruta_archivo.suffix.lower()

    try:
        if extension == ".docx":
            lineas = _extraer_docx(ruta_archivo)

        elif extension == ".pdf":
            lineas = _extraer_pdf(ruta_archivo)

            # HU-15:
            # Si el PDF no contiene texto, probablemente se trata de
            # un documento escaneado. Intentamos OCR automáticamente.
            if not lineas:
                logger.info(
                    "[%s] PDF sin capa de texto. Intentando OCR.",
                    email_id,
                )

                try:
                    lineas = _extraer_pdf_con_ocr(ruta_archivo)

                except Exception as error_ocr:
                    logger.error(
                        "[%s] error durante OCR: %s",
                        email_id,
                        error_ocr,
                    )

                    return TextoExtraido(
                        email_id,
                        "",
                        [],
                        False,
                        f"No se pudo procesar el PDF mediante OCR: "
                        f"{error_ocr}",
                    )

        else:
            return TextoExtraido(
                email_id,
                "",
                [],
                False,
                (
                    "Extensión no soportada para extracción "
                    f"de texto: {extension}"
                ),
            )

    except Exception as e:
        logger.error(
            "[%s] error extrayendo texto: %s",
            email_id,
            e,
        )

        return TextoExtraido(
            email_id,
            "",
            [],
            False,
            f"Error al leer el archivo: {e}",
        )

    if not lineas:
        return TextoExtraido(
            email_id,
            "",
            [],
            False,
            (
                "No se pudo extraer texto legible del CV, "
                "incluyendo el intento mediante OCR."
            ),
        )

    texto_completo = "\n".join(lineas)

    return TextoExtraido(
        email_id,
        texto_completo,
        lineas,
        True,
    )