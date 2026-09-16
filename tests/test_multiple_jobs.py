"""
Sprint 4 - Issue #41
Tests para múltiples job descriptions en una sola ejecución.
"""

from unittest.mock import patch

from src.agent import (
    ResultadoAgente,
    rankear_multiples_vacantes,
)


def _resultado_exitoso(
    email_id: str = "candidato_1",
) -> ResultadoAgente:
    """
    Genera un resultado controlado sin llamar realmente
    al modelo LLM.
    """

    ranking = [
        {
            "email_id": email_id,
            "puntaje": 90,
            "confianza": 1.0,
            "razon_confianza": (
                "Confianza alta: la mayoría de los requisitos "
                "evaluados cuenta con evidencia verificable."
            ),
            "justificacion": [
                {
                    "requisito": "Python",
                    "evidencia": "Python",
                }
            ],
            "requisitos_sin_evidencia": [],
        }
    ]

    return ResultadoAgente(
        ranking=ranking,
        pasos=[],
        error=None,
        metricas={
            "total_cost_usd": 0.01,
        },
    )


# ============================================================
# Caso 1
# Procesar varias vacantes
# ============================================================

def test_issue41_procesa_multiples_vacantes():
    vacantes = [
        {
            "vacante_id": "backend",
            "titulo": "Backend Developer",
            "requisitos": ["Python"],
        },
        {
            "vacante_id": "data",
            "titulo": "Data Engineer",
            "requisitos": ["SQL"],
        },
    ]

    perfiles = [
        {
            "email_id": "candidato_1",
        }
    ]

    with patch(
        "src.agent.rankear_candidatos",
        side_effect=[
            _resultado_exitoso(),
            _resultado_exitoso(),
        ],
    ) as mock_rankear:

        resultado = rankear_multiples_vacantes(
            vacantes,
            perfiles,
        )

    assert mock_rankear.call_count == 2

    assert resultado["total_vacantes"] == 2
    assert resultado["procesadas_exitosamente"] == 2
    assert resultado["fallidas"] == 0

    assert len(
        resultado["resultados"]
    ) == 2

    assert (
        resultado["resultados"][0]["vacante_id"]
        == "backend"
    )

    assert (
        resultado["resultados"][1]["vacante_id"]
        == "data"
    )


# ============================================================
# Caso 2
# Mantener rankings independientes
# ============================================================

def test_issue41_mantiene_rankings_independientes():
    vacantes = [
        {
            "vacante_id": "backend",
            "titulo": "Backend Developer",
        },
        {
            "vacante_id": "frontend",
            "titulo": "Frontend Developer",
        },
    ]

    resultado_backend = _resultado_exitoso(
        "candidato_backend"
    )

    resultado_frontend = _resultado_exitoso(
        "candidato_frontend"
    )

    with patch(
        "src.agent.rankear_candidatos",
        side_effect=[
            resultado_backend,
            resultado_frontend,
        ],
    ):
        resultado = rankear_multiples_vacantes(
            vacantes,
            [],
        )

    ranking_backend = (
        resultado["resultados"][0]["ranking"]
    )

    ranking_frontend = (
        resultado["resultados"][1]["ranking"]
    )

    assert (
        ranking_backend[0]["email_id"]
        == "candidato_backend"
    )

    assert (
        ranking_frontend[0]["email_id"]
        == "candidato_frontend"
    )


# ============================================================
# Caso 3
# Una vacante puede fallar sin detener las demás
# ============================================================

def test_issue41_error_en_una_vacante_no_detiene_lote():
    vacantes = [
        {
            "vacante_id": "backend",
            "titulo": "Backend Developer",
        },
        {
            "vacante_id": "data",
            "titulo": "Data Engineer",
        },
        {
            "vacante_id": "frontend",
            "titulo": "Frontend Developer",
        },
    ]

    with patch(
        "src.agent.rankear_candidatos",
        side_effect=[
            _resultado_exitoso(
                "backend_candidate"
            ),
            RuntimeError(
                "fallo simulado"
            ),
            _resultado_exitoso(
                "frontend_candidate"
            ),
        ],
    ):

        resultado = rankear_multiples_vacantes(
            vacantes,
            [],
        )

    assert resultado["total_vacantes"] == 3
    assert resultado["procesadas_exitosamente"] == 2
    assert resultado["fallidas"] == 1

    assert (
        resultado["resultados"][0]["error"]
        is None
    )

    assert (
        resultado["resultados"][1]["ranking"]
        is None
    )

    assert (
        "fallo simulado"
        in resultado["resultados"][1]["error"]
    )

    assert (
        resultado["resultados"][2]["error"]
        is None
    )


# ============================================================
# Caso 4
# Generar ID cuando la vacante no tiene identificador
# ============================================================

def test_issue41_genera_id_automatico():
    vacantes = [
        {
            "titulo": "Backend Developer",
        },
        {
            "titulo": "Data Engineer",
        },
    ]

    with patch(
        "src.agent.rankear_candidatos",
        side_effect=[
            _resultado_exitoso(),
            _resultado_exitoso(),
        ],
    ):

        resultado = rankear_multiples_vacantes(
            vacantes,
            [],
        )

    assert (
        resultado["resultados"][0]["vacante_id"]
        == "vacante_1"
    )

    assert (
        resultado["resultados"][1]["vacante_id"]
        == "vacante_2"
    )


# ============================================================
# Caso 5
# Lista vacía
# ============================================================

def test_issue41_lista_vacantes_vacia():
    with patch(
        "src.agent.rankear_candidatos"
    ) as mock_rankear:

        resultado = rankear_multiples_vacantes(
            [],
            [],
        )

    mock_rankear.assert_not_called()

    assert resultado == {
        "resultados": [],
        "total_vacantes": 0,
        "procesadas_exitosamente": 0,
        "fallidas": 0,
    }


# ============================================================
# Caso 6
# Error controlado retornado por ResultadoAgente
# ============================================================

def test_issue41_cuenta_resultado_con_error_como_fallido():
    vacantes = [
        {
            "vacante_id": "backend",
            "titulo": "Backend Developer",
        }
    ]

    resultado_con_error = ResultadoAgente(
        ranking=None,
        pasos=[],
        error="Respuesta final inválida",
        metricas={
            "total_cost_usd": 0.005,
        },
    )

    with patch(
        "src.agent.rankear_candidatos",
        return_value=resultado_con_error,
    ):

        resultado = rankear_multiples_vacantes(
            vacantes,
            [],
        )

    assert resultado["total_vacantes"] == 1
    assert resultado["procesadas_exitosamente"] == 0
    assert resultado["fallidas"] == 1

    detalle = resultado["resultados"][0]

    assert detalle["ranking"] is None
    assert (
        detalle["error"]
        == "Respuesta final inválida"
    )

    assert (
        detalle["metricas"]["total_cost_usd"]
        == 0.005
    )