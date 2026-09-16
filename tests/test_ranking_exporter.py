"""
Sprint 4 - Issue #42
Tests para exportación de ranking a CSV y PDF.
"""

import csv

from src.ranking_exporter import (
    _normalizar_ranking,
    exportar_ranking,
    exportar_ranking_csv,
    exportar_ranking_pdf,
)


RANKING_PRUEBA = [
    {
        "email_id": "candidato_medio",
        "puntaje": 60,
        "confianza": 0.5,
        "razon_confianza": (
            "Confianza media: existe evidencia para parte "
            "de los requisitos."
        ),
        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "Experiencia con Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "Experiencia con SQL",
            },
        ],
        "requisitos_sin_evidencia": [
            "Docker",
            "AWS",
        ],
    },
    {
        "email_id": "candidato_fuerte",
        "puntaje": 95,
        "confianza": 1.0,
        "razon_confianza": (
            "Confianza alta: la mayoría de los requisitos "
            "evaluados cuenta con evidencia verificable."
        ),
        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "SQL",
            },
            {
                "requisito": "Docker",
                "evidencia": "Docker",
            },
            {
                "requisito": "AWS",
                "evidencia": "AWS",
            },
        ],
        "requisitos_sin_evidencia": [],
    },
    {
        "email_id": "candidato_debil",
        "puntaje": 20,
        "confianza": 0.0,
        "razon_confianza": (
            "Confianza baja: una parte importante de los "
            "requisitos evaluados no cuenta con evidencia."
        ),
        "justificacion": [],
        "requisitos_sin_evidencia": [
            "Python",
            "SQL",
            "Docker",
            "AWS",
        ],
    },
]


# ============================================================
# Caso 1
# Ordenar ranking antes de exportar
# ============================================================

def test_issue42_normaliza_ranking_por_puntaje():
    ranking_ordenado = _normalizar_ranking(
        RANKING_PRUEBA
    )

    assert [
        item["email_id"]
        for item in ranking_ordenado
    ] == [
        "candidato_fuerte",
        "candidato_medio",
        "candidato_debil",
    ]

    assert [
        item["puntaje"]
        for item in ranking_ordenado
    ] == [
        95,
        60,
        20,
    ]


# ============================================================
# Caso 2
# La normalización no modifica el ranking original
# ============================================================

def test_issue42_no_modifica_ranking_original():
    ranking_original = [
        dict(item)
        for item in RANKING_PRUEBA
    ]

    _normalizar_ranking(
        RANKING_PRUEBA
    )

    assert (
        RANKING_PRUEBA
        == ranking_original
    )


# ============================================================
# Caso 3
# Crear CSV
# ============================================================

def test_issue42_exporta_csv(tmp_path):
    ruta = tmp_path / "ranking.csv"

    resultado = exportar_ranking_csv(
        RANKING_PRUEBA,
        ruta,
    )

    assert resultado == ruta
    assert ruta.exists()
    assert ruta.stat().st_size > 0

    with ruta.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        filas = list(
            csv.DictReader(
                archivo
            )
        )

    assert len(filas) == 3

    assert (
        filas[0]["email_id"]
        == "candidato_fuerte"
    )

    assert (
        filas[0]["posicion"]
        == "1"
    )

    assert (
        filas[0]["puntaje"]
        == "95"
    )

    assert (
        filas[1]["email_id"]
        == "candidato_medio"
    )

    assert (
        filas[2]["email_id"]
        == "candidato_debil"
    )


# ============================================================
# Caso 4
# CSV conserva evidencia y requisitos faltantes
# ============================================================

def test_issue42_csv_incluye_detalle_evidencia(
    tmp_path,
):
    ruta = tmp_path / "ranking_detalle.csv"

    exportar_ranking_csv(
        RANKING_PRUEBA,
        ruta,
    )

    with ruta.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        filas = list(
            csv.DictReader(
                archivo
            )
        )

    candidato_medio = next(
        fila
        for fila in filas
        if fila["email_id"]
        == "candidato_medio"
    )

    assert (
        "Python"
        in candidato_medio["justificacion"]
    )

    assert (
        "Experiencia con Python"
        in candidato_medio["justificacion"]
    )

    assert (
        "Docker"
        in candidato_medio[
            "requisitos_sin_evidencia"
        ]
    )

    assert (
        "AWS"
        in candidato_medio[
            "requisitos_sin_evidencia"
        ]
    )


# ============================================================
# Caso 5
# Crear PDF real
# ============================================================

def test_issue42_exporta_pdf(tmp_path):
    ruta = tmp_path / "ranking.pdf"

    resultado = exportar_ranking_pdf(
        RANKING_PRUEBA,
        ruta,
        titulo="Backend Python Developer",
    )

    assert resultado == ruta
    assert ruta.exists()
    assert ruta.stat().st_size > 0

    contenido = ruta.read_bytes()

    # Todo PDF válido comienza con esta firma.
    assert contenido.startswith(
        b"%PDF"
    )


# ============================================================
# Caso 6
# Exportación conjunta CSV + PDF
# ============================================================

def test_issue42_exporta_csv_y_pdf(
    tmp_path,
):
    resultado = exportar_ranking(
        RANKING_PRUEBA,
        tmp_path,
        nombre_base="backend_python",
        titulo="Backend Python Developer",
    )

    assert set(
        resultado.keys()
    ) == {
        "csv",
        "pdf",
    }

    assert (
        resultado["csv"]
        == tmp_path / "backend_python.csv"
    )

    assert (
        resultado["pdf"]
        == tmp_path / "backend_python.pdf"
    )

    assert resultado["csv"].exists()
    assert resultado["pdf"].exists()

    assert (
        resultado["csv"].stat().st_size
        > 0
    )

    assert (
        resultado["pdf"].stat().st_size
        > 0
    )


# ============================================================
# Caso 7
# Exportar ranking vacío
# ============================================================

def test_issue42_exporta_ranking_vacio(
    tmp_path,
):
    resultado = exportar_ranking(
        [],
        tmp_path,
        nombre_base="ranking_vacio",
    )

    assert resultado["csv"].exists()
    assert resultado["pdf"].exists()

    with resultado["csv"].open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as archivo:

        filas = list(
            csv.DictReader(
                archivo
            )
        )

    assert filas == []

    contenido_pdf = (
        resultado["pdf"].read_bytes()
    )

    assert contenido_pdf.startswith(
        b"%PDF"
    )