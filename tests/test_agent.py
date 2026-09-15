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
import logging
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


# ============================================================
# Sprint 4 - Issue #37
# Structured logging of Thought / Action / Observation
# ============================================================

import json
import logging

from src.agent import _registrar_paso_agente


def test_issue37_registra_thought_como_json(caplog):
    """
    Un Thought debe generar un log JSON estructurado.
    """

    with caplog.at_level(logging.INFO, logger="agent"):
        evento = _registrar_paso_agente(
            "thought",
            contenido="Analizando requisitos de la vacante",
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "thought"
    assert evento["contenido"] == "Analizando requisitos de la vacante"

    registro = json.loads(caplog.records[-1].message)

    assert registro["evento"] == "agent_step"
    assert registro["tipo"] == "thought"
    assert registro["contenido"] == "Analizando requisitos de la vacante"


def test_issue37_registra_action_con_tool_y_argumentos(caplog):
    """
    Una Action debe registrar la tool utilizada y sus argumentos.
    """

    argumentos = {
        "email_id": "candidato-01",
        "requisito": "Python",
    }

    with caplog.at_level(logging.INFO, logger="agent"):
        evento = _registrar_paso_agente(
            "accion",
            tool="verificar_evidencia",
            argumentos=argumentos,
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "accion"
    assert evento["tool"] == "verificar_evidencia"
    assert evento["argumentos"] == argumentos

    registro = json.loads(caplog.records[-1].message)

    assert registro["tipo"] == "accion"
    assert registro["tool"] == "verificar_evidencia"
    assert registro["argumentos"] == argumentos


def test_issue37_registra_observacion(caplog):
    """
    Una Observation debe registrar el contenido recibido
    y si representa o no un error.
    """

    with caplog.at_level(logging.INFO, logger="agent"):
        evento = _registrar_paso_agente(
            "observacion",
            contenido={
                "tiene_evidencia": True,
                "campo": "habilidades",
            },
            es_error=False,
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "observacion"
    assert evento["es_error"] is False

    registro = json.loads(caplog.records[-1].message)

    assert registro["tipo"] == "observacion"
    assert registro["es_error"] is False


def test_issue37_registra_observacion_con_error(caplog):
    """
    Una Observation fallida debe quedar explícitamente
    identificada como error en el log.
    """

    with caplog.at_level(logging.INFO, logger="agent"):
        evento = _registrar_paso_agente(
            "observacion",
            contenido="Tool temporalmente no disponible",
            es_error=True,
        )

    assert evento["tipo"] == "observacion"
    assert evento["es_error"] is True

    registro = json.loads(caplog.records[-1].message)

    assert registro["evento"] == "agent_step"
    assert registro["tipo"] == "observacion"
    assert registro["es_error"] is True


    # ============================================================
# Sprint 4 - Issue #36
# Token usage and cost tracking for LLM calls
# ============================================================

from types import SimpleNamespace

from src.agent import (
    _extraer_metricas_llm,
    _registrar_metricas_llm,
)


def test_issue36_extrae_tokens_y_costo():
    """
    Debe extraer usage y costo directamente del ResultMessage
    reportado por Claude Agent SDK.
    """

    mensaje = SimpleNamespace(
        usage={
            "input_tokens": 1200,
            "output_tokens": 350,
        },
        total_cost_usd=0.0125,
        model_usage={},
        num_turns=4,
        duration_api_ms=1850,
    )

    metricas = _extraer_metricas_llm(mensaje)

    assert metricas["usage"]["input_tokens"] == 1200
    assert metricas["usage"]["output_tokens"] == 350
    assert metricas["total_cost_usd"] == 0.0125
    assert metricas["num_turns"] == 4
    assert metricas["duration_api_ms"] == 1850


def test_issue36_maneja_usage_vacio():
    """
    Si el SDK no devuelve usage o model_usage,
    el tracking debe seguir funcionando.
    """

    mensaje = SimpleNamespace(
        usage=None,
        total_cost_usd=None,
        model_usage=None,
        num_turns=1,
        duration_api_ms=500,
    )

    metricas = _extraer_metricas_llm(mensaje)

    assert metricas["usage"] == {}
    assert metricas["model_usage"] == {}
    assert metricas["total_cost_usd"] is None
    assert metricas["num_turns"] == 1


def test_issue36_registra_metricas_como_json(caplog):
    """
    Las métricas deben quedar registradas como un evento
    JSON estructurado llm_usage.
    """

    metricas = {
        "usage": {
            "input_tokens": 800,
            "output_tokens": 200,
        },
        "total_cost_usd": 0.008,
        "model_usage": {},
        "num_turns": 3,
        "duration_api_ms": 1200,
    }

    with caplog.at_level(logging.INFO, logger="agent"):
        _registrar_metricas_llm(metricas)

    registro = json.loads(
        caplog.records[-1].message
    )

    assert registro["evento"] == "llm_usage"
    assert registro["usage"]["input_tokens"] == 800
    assert registro["usage"]["output_tokens"] == 200
    assert registro["total_cost_usd"] == 0.008
    assert registro["num_turns"] == 3
    assert registro["duration_api_ms"] == 1200


def test_issue36_resultado_agente_conserva_metricas():
    """
    ResultadoAgente debe exponer las métricas sin romper
    la interfaz existente de ranking, pasos y error.
    """

    from src.agent import ResultadoAgente

    metricas = {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
        },
        "total_cost_usd": 0.001,
    }

    resultado = ResultadoAgente(
        ranking=[],
        pasos=[],
        metricas=metricas,
    )

    assert resultado.ranking == []
    assert resultado.pasos == []
    assert resultado.error is None
    assert resultado.metricas == metricas