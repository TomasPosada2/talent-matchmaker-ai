"""
Sprint 4 - Issue #42
Export ranking results to CSV and PDF.
"""

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _normalizar_ranking(
    ranking: list[dict],
) -> list[dict]:
    """
    Normaliza y ordena el ranking por puntaje descendente.

    No modifica la lista original.
    """

    return sorted(
        [dict(item) for item in ranking],
        key=lambda item: item.get("puntaje", 0),
        reverse=True,
    )


def _texto_justificacion(
    justificacion: list[dict] | None,
) -> str:
    """
    Convierte la justificación estructurada a texto legible.
    """

    if not justificacion:
        return ""

    partes = []

    for item in justificacion:
        requisito = str(
            item.get("requisito", "")
        )

        evidencia = str(
            item.get("evidencia", "")
        )

        partes.append(
            f"{requisito}: {evidencia}"
        )

    return " | ".join(partes)


def _texto_sin_evidencia(
    requisitos: list[str] | None,
) -> str:
    """
    Convierte los requisitos sin evidencia a texto.
    """

    if not requisitos:
        return ""

    return ", ".join(
        str(requisito)
        for requisito in requisitos
    )


def exportar_ranking_csv(
    ranking: list[dict],
    ruta_salida: str | Path,
) -> Path:
    """
    Exporta un ranking a CSV.

    Columnas:
    - posición
    - email_id
    - puntaje
    - confianza
    - razon_confianza
    - justificacion
    - requisitos_sin_evidencia
    """

    ruta = Path(ruta_salida)

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ranking_ordenado = _normalizar_ranking(
        ranking
    )

    columnas = [
        "posicion",
        "email_id",
        "puntaje",
        "confianza",
        "razon_confianza",
        "justificacion",
        "requisitos_sin_evidencia",
    ]

    with ruta.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        writer = csv.DictWriter(
            archivo,
            fieldnames=columnas,
        )

        writer.writeheader()

        for posicion, item in enumerate(
            ranking_ordenado,
            start=1,
        ):

            writer.writerow(
                {
                    "posicion": posicion,
                    "email_id": item.get(
                        "email_id",
                        "",
                    ),
                    "puntaje": item.get(
                        "puntaje",
                        "",
                    ),
                    "confianza": item.get(
                        "confianza",
                        "",
                    ),
                    "razon_confianza": item.get(
                        "razon_confianza",
                        "",
                    ),
                    "justificacion": (
                        _texto_justificacion(
                            item.get(
                                "justificacion"
                            )
                        )
                    ),
                    "requisitos_sin_evidencia": (
                        _texto_sin_evidencia(
                            item.get(
                                "requisitos_sin_evidencia"
                            )
                        )
                    ),
                }
            )

    return ruta


def exportar_ranking_pdf(
    ranking: list[dict],
    ruta_salida: str | Path,
    titulo: str = "Ranking de candidatos",
) -> Path:
    """
    Exporta el ranking a un reporte PDF.
    """

    ruta = Path(ruta_salida)

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ranking_ordenado = _normalizar_ranking(
        ranking
    )

    documento = SimpleDocTemplate(
        str(ruta),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    estilos = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "RankingTitle",
        parent=estilos["Title"],
        alignment=TA_CENTER,
        spaceAfter=16,
    )

    estilo_normal = estilos["BodyText"]

    elementos = [
        Paragraph(
            titulo,
            estilo_titulo,
        ),
        Paragraph(
            (
                f"Total de candidatos evaluados: "
                f"{len(ranking_ordenado)}"
            ),
            estilo_normal,
        ),
        Spacer(
            1,
            0.5 * cm,
        ),
    ]

    tabla_datos = [
        [
            "Pos.",
            "Candidato",
            "Puntaje",
            "Confianza",
        ]
    ]

    for posicion, item in enumerate(
        ranking_ordenado,
        start=1,
    ):

        confianza = item.get(
            "confianza",
            "",
        )

        if isinstance(
            confianza,
            (int, float),
        ):
            confianza_texto = (
                f"{confianza * 100:.1f}%"
            )
        else:
            confianza_texto = str(
                confianza
            )

        tabla_datos.append(
            [
                str(posicion),
                str(
                    item.get(
                        "email_id",
                        "",
                    )
                ),
                str(
                    item.get(
                        "puntaje",
                        "",
                    )
                ),
                confianza_texto,
            ]
        )

    tabla = Table(
        tabla_datos,
        colWidths=[
            1.5 * cm,
            8.5 * cm,
            3 * cm,
            3 * cm,
        ],
        repeatRows=1,
    )

    tabla.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.lightgrey,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.black,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (0, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (2, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    8,
                ),
            ]
        )
    )

    elementos.append(
        tabla
    )

    elementos.append(
        Spacer(
            1,
            0.8 * cm,
        )
    )

    # ========================================================
    # Detalle de cada candidato
    # ========================================================

    for posicion, item in enumerate(
        ranking_ordenado,
        start=1,
    ):

        email_id = str(
            item.get(
                "email_id",
                "",
            )
        )

        puntaje = item.get(
            "puntaje",
            "",
        )

        confianza = item.get(
            "confianza",
            "",
        )

        razon_confianza = str(
            item.get(
                "razon_confianza",
                "",
            )
        )

        justificacion = (
            _texto_justificacion(
                item.get(
                    "justificacion"
                )
            )
        )

        sin_evidencia = (
            _texto_sin_evidencia(
                item.get(
                    "requisitos_sin_evidencia"
                )
            )
        )

        elementos.append(
            Paragraph(
                (
                    f"<b>{posicion}. "
                    f"{email_id}</b>"
                ),
                estilos["Heading3"],
            )
        )

        elementos.append(
            Paragraph(
                f"<b>Puntaje:</b> {puntaje}",
                estilo_normal,
            )
        )

        if isinstance(
            confianza,
            (int, float),
        ):
            confianza_detalle = (
                f"{confianza * 100:.1f}%"
            )
        else:
            confianza_detalle = str(
                confianza
            )

        elementos.append(
            Paragraph(
                (
                    "<b>Confianza:</b> "
                    f"{confianza_detalle}"
                ),
                estilo_normal,
            )
        )

        if razon_confianza:
            elementos.append(
                Paragraph(
                    (
                        "<b>Razón de confianza:</b> "
                        f"{razon_confianza}"
                    ),
                    estilo_normal,
                )
            )

        elementos.append(
            Paragraph(
                (
                    "<b>Evidencia:</b> "
                    f"{justificacion or 'Sin evidencia registrada'}"
                ),
                estilo_normal,
            )
        )

        elementos.append(
            Paragraph(
                (
                    "<b>Requisitos sin evidencia:</b> "
                    f"{sin_evidencia or 'Ninguno'}"
                ),
                estilo_normal,
            )
        )

        elementos.append(
            Spacer(
                1,
                0.5 * cm,
            )
        )

    documento.build(
        elementos
    )

    return ruta


def exportar_ranking(
    ranking: list[dict],
    carpeta_salida: str | Path,
    nombre_base: str = "ranking",
    titulo: str = "Ranking de candidatos",
) -> dict:
    """
    Exporta simultáneamente el ranking a CSV y PDF.
    """

    carpeta = Path(
        carpeta_salida
    )

    carpeta.mkdir(
        parents=True,
        exist_ok=True,
    )

    ruta_csv = exportar_ranking_csv(
        ranking,
        carpeta / f"{nombre_base}.csv",
    )

    ruta_pdf = exportar_ranking_pdf(
        ranking,
        carpeta / f"{nombre_base}.pdf",
        titulo=titulo,
    )

    return {
        "csv": ruta_csv,
        "pdf": ruta_pdf,
    }