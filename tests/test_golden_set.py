"""
Sprint 4 - Issue #38
Golden-set regression tests for ranking quality.
"""

from src import agent_tools, schema
from src.agent import _agregar_confianza_ranking

from tests.golden_set import (
    ORDEN_ESPERADO,
    PERFILES_GOLDEN,
    RANKING_GOLDEN,
    VACANTE_GOLDEN,
)


def test_golden_set_perfiles_cumplen_schema():
    """
    Todos los candidatos del golden set deben representar
    perfiles válidos del sistema.
    """

    for perfil in PERFILES_GOLDEN:
        es_valido, error = schema.validar_perfil(
            perfil
        )

        assert es_valido, (
            f"Perfil inválido "
            f"{perfil['email_id']}: {error}"
        )


def test_golden_set_requisitos_tienen_resultado_conocido():
    """
    Verifica que la evidencia del dataset realmente produce
    la cobertura esperada para los requisitos de la vacante.
    """

    candidato_fuerte = PERFILES_GOLDEN[0]
    candidato_medio = PERFILES_GOLDEN[1]
    candidato_debil = PERFILES_GOLDEN[2]

    for requisito in VACANTE_GOLDEN["requisitos"]:
        resultado = agent_tools.verificar_evidencia(
            candidato_fuerte,
            requisito,
        )

        assert resultado["tiene_evidencia"] is True

    resultados_medio = {
        requisito: agent_tools.verificar_evidencia(
            candidato_medio,
            requisito,
        )["tiene_evidencia"]
        for requisito in VACANTE_GOLDEN["requisitos"]
    }

    assert resultados_medio == {
        "Python": True,
        "SQL": True,
        "Docker": False,
        "AWS": False,
    }

    for requisito in VACANTE_GOLDEN["requisitos"]:
        resultado = agent_tools.verificar_evidencia(
            candidato_debil,
            requisito,
        )

        assert resultado["tiene_evidencia"] is False


def test_golden_set_preserva_orden_de_calidad():
    """
    Regresión principal:
    candidato fuerte > candidato medio > candidato débil.
    """

    ranking_ordenado = sorted(
        RANKING_GOLDEN,
        key=lambda item: item["puntaje"],
        reverse=True,
    )

    orden_obtenido = [
        item["email_id"]
        for item in ranking_ordenado
    ]

    assert orden_obtenido == ORDEN_ESPERADO


def test_golden_set_confianza_refleja_cobertura():
    """
    #38 + #40:
    La confianza debe disminuir cuando disminuye la
    cobertura de evidencia.
    """

    ranking = _agregar_confianza_ranking(
        RANKING_GOLDEN
    )

    por_email = {
        item["email_id"]: item
        for item in ranking
    }

    assert (
        por_email["candidato_fuerte"]["confianza"]
        == 1.0
    )

    assert (
        por_email["candidato_medio"]["confianza"]
        == 0.5
    )

    assert (
        por_email["candidato_debil"]["confianza"]
        == 0.0
    )

    assert (
        por_email["candidato_fuerte"]["confianza"]
        >
        por_email["candidato_medio"]["confianza"]
        >
        por_email["candidato_debil"]["confianza"]
    )


def test_golden_set_ranking_final_cumple_schema():
    """
    El resultado Golden enriquecido con confidence scoring
    debe cumplir el contrato final del ranking.
    """

    ranking = _agregar_confianza_ranking(
        RANKING_GOLDEN
    )

    es_valido, error = schema.validar_ranking(
        ranking
    )

    assert es_valido, error