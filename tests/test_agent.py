"""
Tests del agente de matching (HU-09 a HU-14).

Sprint 4: el agent loop ahora corre sobre el Claude Agent SDK, que a su vez
depende del binario `claude` (Claude Code CLI) para de verdad hablar con el
modelo. Ese binario no está disponible en este entorno de desarrollo, así
que aquí se prueba lo que sí se puede probar sin él:

  - la lógica de negocio pura (agent_tools, vacancy_structurer, schema)
  - los handlers de las tools del SDK, llamados directamente como las
    funciones async que son (agent.construir_tools), sin pasar por el CLI

El loop completo (agent.rankear_candidatos) queda sin cubrir por pruebas
automatizadas hasta correrlo contra el CLI real — por eso HU-12/13/14 siguen
en QA en el backlog.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent, agent_tools, schema, vacancy_structurer

PERFILES = [
    {
        "email_id": "email_1",
        "nombre": {"valor": "Ana", "evidencia": "Ana"},
        "contacto": {"email": {"valor": "ana@example.com", "evidencia": "ana@example.com"},
                     "telefono": {"valor": None, "evidencia": None}},
        "educacion": {"valor": None, "evidencia": None},
        "experiencia": {"valor": None, "evidencia": None},
        "habilidades": {"valor": "Python, SQL", "evidencia": "Python, SQL"},
    }
]


def _correr(coro):
    return asyncio.run(coro)


def test_estructurar_vacante_extrae_requisitos():
    texto = "Backend Developer\n\nRequisitos:\n- Python\n- SQL\n"
    vacante = vacancy_structurer.estructurar_vacante(texto)
    assert vacante["cargo"] == "Backend Developer"
    assert vacante["requisitos"] == ["Python", "SQL"]


def test_estructurar_vacante_sin_requisitos_no_alucina():
    vacante = vacancy_structurer.estructurar_vacante("Backend Developer\n\nSobre nosotros...")
    assert vacante["requisitos"] == []


def test_consultar_perfiles_filtra_por_email_id():
    resultado = agent_tools.consultar_perfiles(PERFILES, "email_1")
    assert len(resultado) == 1
    assert agent_tools.consultar_perfiles(PERFILES, "no_existe") == []


def test_verificar_evidencia_encuentra_match_real():
    resultado = agent_tools.verificar_evidencia(PERFILES[0], "Python")
    assert resultado["tiene_evidencia"] is True
    assert resultado["evidencia"] == "Python, SQL"


def test_verificar_evidencia_no_alucina_sin_match():
    resultado = agent_tools.verificar_evidencia(PERFILES[0], "Kubernetes")
    assert resultado["tiene_evidencia"] is False
    assert resultado["evidencia"] is None


def test_ranking_sin_justificacion_es_rechazado_por_el_schema():
    ranking_invalido = [{"email_id": "email_1", "puntaje": 80}]
    es_valido, error = schema.validar_ranking(ranking_invalido)
    assert es_valido is False
    assert error is not None


def test_ranking_con_evidencia_es_valido():
    ranking_valido = [{
        "email_id": "email_1",
        "puntaje": 80,
        "justificacion": [{"requisito": "Python", "evidencia": "Python, SQL"}],
        "requisitos_sin_evidencia": [],
    }]
    es_valido, error = schema.validar_ranking(ranking_valido)
    assert es_valido, error


def test_tool_consultar_perfiles_devuelve_formato_mcp():
    tools = agent.construir_tools(PERFILES)
    tool_consultar = next(t for t in tools if t.name == "consultar_perfiles")

    resultado = _correr(tool_consultar.handler({"email_id": "email_1"}))

    assert "content" in resultado
    perfiles_devueltos = json.loads(resultado["content"][0]["text"])
    assert perfiles_devueltos[0]["email_id"] == "email_1"


def test_tool_verificar_evidencia_confirma_match_real():
    tools = agent.construir_tools(PERFILES)
    tool_verificar = next(t for t in tools if t.name == "verificar_evidencia")

    resultado = _correr(tool_verificar.handler({"email_id": "email_1", "requisito": "Python"}))

    cuerpo = json.loads(resultado["content"][0]["text"])
    assert cuerpo["tiene_evidencia"] is True
    assert not resultado.get("is_error")


def test_tool_verificar_evidencia_reporta_error_en_candidato_inexistente():
    """HU-14: si el agente pide evidencia de un candidato que no existe
    (referencia alucinada), la tool debe reportar el error explícitamente
    en vez de devolver una respuesta inventada."""
    tools = agent.construir_tools(PERFILES)
    tool_verificar = next(t for t in tools if t.name == "verificar_evidencia")

    resultado = _correr(tool_verificar.handler({"email_id": "no_existe", "requisito": "Python"}))

    assert resultado.get("is_error") is True


    # ============================================================
# Sprint 4 - Issue #35
# Retry/backoff strategy for failing agent tool calls
# ============================================================

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.agent import _ejecutar_con_reintentos


def test_issue35_reintenta_y_se_recupera():
    """
    Si una tool falla temporalmente, debe reintentarse y
    devolver el resultado cuando un intento posterior funciona.
    """

    intentos = 0

    async def operacion_inestable():
        nonlocal intentos
        intentos += 1

        if intentos < 3:
            raise ConnectionError("Fallo temporal")

        return {"resultado": "ok"}

    async def ejecutar():
        with patch(
            "src.agent.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:

            resultado = await _ejecutar_con_reintentos(
                operacion_inestable,
                "tool_prueba",
                max_intentos=3,
                backoff_inicial=0.25,
            )

            return resultado, mock_sleep

    resultado, mock_sleep = asyncio.run(ejecutar())

    assert resultado == {"resultado": "ok"}
    assert intentos == 3

    assert mock_sleep.await_count == 2

    mock_sleep.assert_any_await(0.25)
    mock_sleep.assert_any_await(0.50)


def test_issue35_no_reintenta_si_funciona_primera_vez():
    """
    Una tool que funciona correctamente no debe introducir
    esperas ni reintentos innecesarios.
    """

    intentos = 0

    async def operacion_correcta():
        nonlocal intentos
        intentos += 1
        return "ok"

    async def ejecutar():
        with patch(
            "src.agent.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:

            resultado = await _ejecutar_con_reintentos(
                operacion_correcta,
                "tool_prueba",
            )

            return resultado, mock_sleep

    resultado, mock_sleep = asyncio.run(ejecutar())

    assert resultado == "ok"
    assert intentos == 1
    mock_sleep.assert_not_awaited()


def test_issue35_falla_despues_del_maximo_de_intentos():
    """
    Si la tool continúa fallando, el sistema debe detenerse
    después del máximo configurado de intentos.
    """

    intentos = 0

    async def operacion_fallida():
        nonlocal intentos
        intentos += 1
        raise ConnectionError("Servicio no disponible")

    async def ejecutar():
        with patch(
            "src.agent.asyncio.sleep",
            new_callable=AsyncMock,
        ) as mock_sleep:

            with pytest.raises(
                ConnectionError,
                match="Servicio no disponible",
            ):
                await _ejecutar_con_reintentos(
                    operacion_fallida,
                    "tool_prueba",
                    max_intentos=3,
                    backoff_inicial=0.25,
                )

            return mock_sleep

    mock_sleep = asyncio.run(ejecutar())

    assert intentos == 3

    # Hay espera después de los dos primeros fallos,
    # pero no después del último.
    assert mock_sleep.await_count == 2
    mock_sleep.assert_any_await(0.25)
    mock_sleep.assert_any_await(0.50)


def test_issue35_valida_numero_de_intentos():
    """
    La configuración no debe permitir cero intentos.
    """

    async def operacion():
        return "ok"

    with pytest.raises(
        ValueError,
        match="max_intentos debe ser al menos 1",
    ):
        asyncio.run(
            _ejecutar_con_reintentos(
                operacion,
                "tool_prueba",
                max_intentos=0,
            )
        )
