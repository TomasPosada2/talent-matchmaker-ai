
"""Pruebas de búsqueda y filtros de candidatos - Issue #52."""

from dashboard.candidate_filters import (
    convertir_a_texto,
    filtrar_candidatos,
    preparar_tabla,
)


def crear_perfil(nombre, habilidades, experiencia):
    return {
        "email_id": f"{nombre.lower().replace(' ', '_')}_001",
        "archivo_origen": "cv.pdf",
        "nombre": {
            "valor": nombre,
            "evidencia": nombre,
        },
        "contacto": {
            "email": {
                "valor": "candidato@example.com",
                "evidencia": None,
            },
            "telefono": {
                "valor": None,
                "evidencia": None,
            },
        },
        "educacion": {
            "valor": "Ingeniería",
            "evidencia": None,
        },
        "experiencia": {
            "valor": experiencia,
            "evidencia": None,
        },
        "habilidades": {
            "valor": habilidades,
            "evidencia": None,
        },
    }


PERFILES = [
    crear_perfil(
        "Ana García",
        ["Python", "SQL"],
        "Desarrollo de software",
    ),
    crear_perfil(
        "Carlos López",
        ["Excel", "Power BI"],
        "Análisis financiero",
    ),
    crear_perfil(
        "María Torres",
        ["Python", "Excel"],
        "Análisis de datos",
    ),
]


def test_sin_filtros_devuelve_todos():
    assert len(filtrar_candidatos(PERFILES)) == 3


def test_filtrar_por_nombre():
    resultado = filtrar_candidatos(
        PERFILES,
        nombre="ana",
    )
    assert len(resultado) == 1
    assert resultado[0]["nombre"]["valor"] == "Ana García"


def test_filtrar_por_habilidad():
    resultado = filtrar_candidatos(
        PERFILES,
        habilidad="python",
    )
    assert len(resultado) == 2


def test_filtrar_por_experiencia():
    resultado = filtrar_candidatos(
        PERFILES,
        experiencia="financiero",
    )
    assert len(resultado) == 1


def test_combinar_filtros():
    resultado = filtrar_candidatos(
        PERFILES,
        habilidad="excel",
        experiencia="datos",
    )
    assert len(resultado) == 1
    assert resultado[0]["nombre"]["valor"] == "María Torres"


def test_busqueda_sin_coincidencias():
    assert filtrar_candidatos(
        PERFILES,
        habilidad="Java",
    ) == []


def test_valores_vacios():
    perfil = crear_perfil(
        "Sin Datos",
        None,
        None,
    )
    assert len(filtrar_candidatos([perfil])) == 1
    assert filtrar_candidatos(
        [perfil],
        habilidad="python",
    ) == []


def test_convertir_lista_a_texto():
    assert convertir_a_texto(
        ["Python", "SQL"]
    ) == "Python, SQL"


def test_preparar_tabla():
    tabla = preparar_tabla(PERFILES)

    assert len(tabla) == 3
    assert tabla[0]["Nombre"] == "Ana García"
    assert tabla[0]["Habilidades"] == "Python, SQL"
    assert tabla[0]["Correo"] == "candidato@example.com"


def test_filtros_no_modifican_datos_originales():
    original = PERFILES[0]["habilidades"]["valor"].copy()

    filtrar_candidatos(
        PERFILES,
        habilidad="python",
    )

    assert PERFILES[0]["habilidades"]["valor"] == original
