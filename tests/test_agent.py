"""
Tests del agente de ranking.

Incluye:
- HU-13: validación del ranking con evidencia.
- Sprint 4 #35: retry/backoff de tools.
- Sprint 4 #36: token usage y cost tracking.
- Sprint 4 #37: structured logging.
- Sprint 4 #40: confidence scoring por decisión de ranking.
"""

import asyncio
import json
import logging
from types import SimpleNamespace

import pytest

from src import schema
from src.agent import (
    ResultadoAgente,
    _agregar_confianza_ranking,
    _calcular_confianza_decision,
    _ejecutar_con_reintentos,
    _extraer_metricas_llm,
    _registrar_metricas_llm,
    _registrar_paso_agente,
)


# ============================================================
# HU-13
# Validación del ranking con evidencia
# ============================================================

def test_ranking_sin_justificacion_es_invalido():
    ranking_invalido = [
        {
            "email_id": "email_1",
            "puntaje": 80,
        }
    ]

    es_valido, error = schema.validar_ranking(
        ranking_invalido
    )

    assert not es_valido
    assert error is not None


def test_ranking_con_evidencia_es_valido():
    ranking_valido = [
        {
            "email_id": "email_1",
            "puntaje": 80,
            "confianza": 1.0,
            "razon_confianza": (
                "Confianza alta: la mayoría de los requisitos "
                "evaluados cuenta con evidencia verificable."
            ),
            "justificacion": [
                {
                    "requisito": "Python",
                    "evidencia": "Python, SQL",
                }
            ],
            "requisitos_sin_evidencia": [],
        }
    ]

    es_valido, error = schema.validar_ranking(
        ranking_valido
    )

    assert es_valido, error


def test_ranking_puntaje_fuera_de_rango_es_invalido():
    ranking_invalido = [
        {
            "email_id": "email_1",
            "puntaje": 120,
            "confianza": 1.0,
            "razon_confianza": (
                "Existe evidencia verificable."
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

    es_valido, error = schema.validar_ranking(
        ranking_invalido
    )

    assert not es_valido
    assert error is not None


# ============================================================
# Sprint 4 - Issue #35
# Retry/backoff strategy
# ============================================================

def test_retry_tool_funciona_en_primer_intento():
    llamadas = 0

    async def operacion():
        nonlocal llamadas
        llamadas += 1
        return "ok"

    resultado = asyncio.run(
        _ejecutar_con_reintentos(
            operacion,
            "tool_prueba",
            max_intentos=3,
            backoff_inicial=0,
        )
    )

    assert resultado == "ok"
    assert llamadas == 1


def test_retry_tool_reintenta_tras_error():
    llamadas = 0

    async def operacion():
        nonlocal llamadas
        llamadas += 1

        if llamadas < 3:
            raise RuntimeError(
                "fallo temporal"
            )

        return "recuperado"

    resultado = asyncio.run(
        _ejecutar_con_reintentos(
            operacion,
            "tool_prueba",
            max_intentos=3,
            backoff_inicial=0,
        )
    )

    assert resultado == "recuperado"
    assert llamadas == 3


def test_retry_tool_lanza_error_tras_maximo_intentos():
    llamadas = 0

    async def operacion():
        nonlocal llamadas
        llamadas += 1
        raise RuntimeError(
            "fallo permanente"
        )

    with pytest.raises(
        RuntimeError,
        match="fallo permanente",
    ):
        asyncio.run(
            _ejecutar_con_reintentos(
                operacion,
                "tool_prueba",
                max_intentos=3,
                backoff_inicial=0,
            )
        )

    assert llamadas == 3


def test_retry_tool_rechaza_cero_intentos():
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
                backoff_inicial=0,
            )
        )


# ============================================================
# Sprint 4 - Issue #37
# Structured logging
# ============================================================

def test_logging_thought_estructurado(caplog):
    with caplog.at_level(
        logging.INFO,
        logger="agent",
    ):
        evento = _registrar_paso_agente(
            "thought",
            contenido="Analizando candidato",
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "thought"
    assert evento["contenido"] == "Analizando candidato"

    registro = json.loads(
        caplog.records[-1].message
    )

    assert registro["evento"] == "agent_step"
    assert registro["tipo"] == "thought"


def test_logging_action_estructurado(caplog):
    with caplog.at_level(
        logging.INFO,
        logger="agent",
    ):
        evento = _registrar_paso_agente(
            "accion",
            tool="verificar_evidencia",
            argumentos={
                "email_id": "email_1",
                "requisito": "Python",
            },
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "accion"
    assert evento["tool"] == "verificar_evidencia"

    assert evento["argumentos"] == {
        "email_id": "email_1",
        "requisito": "Python",
    }

    registro = json.loads(
        caplog.records[-1].message
    )

    assert registro["tipo"] == "accion"
    assert registro["tool"] == "verificar_evidencia"


def test_logging_observation_estructurado(caplog):
    with caplog.at_level(
        logging.INFO,
        logger="agent",
    ):
        evento = _registrar_paso_agente(
            "observacion",
            contenido="Evidencia encontrada",
            es_error=False,
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "observacion"
    assert evento["es_error"] is False

    registro = json.loads(
        caplog.records[-1].message
    )

    assert registro["tipo"] == "observacion"
    assert registro["es_error"] is False


def test_logging_observation_error_estructurado(caplog):
    with caplog.at_level(
        logging.INFO,
        logger="agent",
    ):
        evento = _registrar_paso_agente(
            "observacion",
            contenido="Error de tool",
            es_error=True,
        )

    assert evento["evento"] == "agent_step"
    assert evento["tipo"] == "observacion"
    assert evento["es_error"] is True

    registro = json.loads(
        caplog.records[-1].message
    )

    assert registro["evento"] == "agent_step"
    assert registro["tipo"] == "observacion"
    assert registro["es_error"] is True


# ============================================================
# Sprint 4 - Issue #36
# Token usage and cost tracking
# ============================================================

def test_issue36_extrae_tokens_y_costo():
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

    metricas = _extraer_metricas_llm(
        mensaje
    )

    assert metricas["usage"]["input_tokens"] == 1200
    assert metricas["usage"]["output_tokens"] == 350
    assert metricas["total_cost_usd"] == 0.0125
    assert metricas["num_turns"] == 4
    assert metricas["duration_api_ms"] == 1850


def test_issue36_maneja_usage_vacio():
    mensaje = SimpleNamespace(
        usage=None,
        total_cost_usd=None,
        model_usage=None,
        num_turns=1,
        duration_api_ms=500,
    )

    metricas = _extraer_metricas_llm(
        mensaje
    )

    assert metricas["usage"] == {}
    assert metricas["model_usage"] == {}
    assert metricas["total_cost_usd"] is None
    assert metricas["num_turns"] == 1
    assert metricas["duration_api_ms"] == 500


def test_issue36_registra_metricas_como_json(caplog):
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

    with caplog.at_level(
        logging.INFO,
        logger="agent",
    ):
        _registrar_metricas_llm(
            metricas
        )

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


# ============================================================
# Sprint 4 - Issue #40
# Confidence scoring per ranking decision
# ============================================================

def test_issue40_confianza_total_con_toda_la_evidencia():
    item = {
        "email_id": "email_1",
        "puntaje": 95,
        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "5 años usando Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "Experiencia con PostgreSQL",
            },
            {
                "requisito": "AWS",
                "evidencia": "AWS Solutions Architect",
            },
            {
                "requisito": "Docker",
                "evidencia": "Docker y Kubernetes",
            },
        ],
        "requisitos_sin_evidencia": [],
    }

    confianza, razon = _calcular_confianza_decision(
        item
    )

    assert confianza == 1.0
    assert "Confianza alta" in razon


def test_issue40_confianza_075():
    item = {
        "email_id": "email_1",
        "puntaje": 80,
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
        ],
        "requisitos_sin_evidencia": [
            "AWS",
        ],
    }

    confianza, razon = _calcular_confianza_decision(
        item
    )

    assert confianza == 0.75
    assert "Confianza media" in razon


def test_issue40_confianza_05():
    item = {
        "email_id": "email_1",
        "puntaje": 60,
        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "SQL",
            },
        ],
        "requisitos_sin_evidencia": [
            "AWS",
            "Docker",
        ],
    }

    confianza, razon = _calcular_confianza_decision(
        item
    )

    assert confianza == 0.5
    assert "Confianza media" in razon


def test_issue40_confianza_cero_sin_requisitos():
    item = {
        "email_id": "email_1",
        "puntaje": 0,
        "justificacion": [],
        "requisitos_sin_evidencia": [],
    }

    confianza, razon = _calcular_confianza_decision(
        item
    )

    assert confianza == 0.0
    assert "No existen requisitos evaluados" in razon


def test_issue40_agrega_confianza_al_ranking():
    ranking = [
        {
            "email_id": "email_1",
            "puntaje": 75,
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
            ],
            "requisitos_sin_evidencia": [
                "AWS",
            ],
        }
    ]

    resultado = _agregar_confianza_ranking(
        ranking
    )

    assert len(resultado) == 1
    assert resultado[0]["confianza"] == 0.75
    assert "razon_confianza" in resultado[0]


def test_issue40_no_modifica_ranking_original():
    ranking = [
        {
            "email_id": "email_1",
            "puntaje": 90,
            "justificacion": [
                {
                    "requisito": "Python",
                    "evidencia": "Python",
                }
            ],
            "requisitos_sin_evidencia": [],
        }
    ]

    resultado = _agregar_confianza_ranking(
        ranking
    )

    assert "confianza" not in ranking[0]
    assert "razon_confianza" not in ranking[0]

    assert resultado[0]["confianza"] == 1.0
    assert "razon_confianza" in resultado[0]


def test_issue40_schema_rechaza_confianza_fuera_de_rango():
    ranking_invalido = [
        {
            "email_id": "email_1",
            "puntaje": 80,
            "confianza": 1.5,
            "razon_confianza": (
                "Valor deliberadamente inválido para el test."
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

    es_valido, error = schema.validar_ranking(
        ranking_invalido
    )

    assert not es_valido
    assert error is not None