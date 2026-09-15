"""
HU-12: Agent loop (Thought -> Action -> Observation) con límite de pasos.
HU-13: Ranking final justificado con evidencia citada por candidato.
HU-14: Manejo de errores del agente (tool falla, LLM alucina un requisito).

Sprint 4:
- Migración al Claude Agent SDK.
- #35: Retry/backoff strategy for failing agent tool calls.

Las llamadas a tools de negocio utilizan reintentos con backoff exponencial
para recuperarse de fallos transitorios sin tumbar el agent loop.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    query,
    tool,
)

from . import agent_tools, schema

logger = logging.getLogger("agent")

MAX_PASOS = 8
MODELO = "claude-sonnet-5"
SERVIDOR_MCP = "talent_matchmaker"

# Sprint 4 - Issue #35
MAX_REINTENTOS_TOOL = 3
BACKOFF_INICIAL_SEGUNDOS = 0.25


SYSTEM_PROMPT = """Eres un agente de reclutamiento. Debes rankear candidatos contra
una vacante usando SOLO las tools disponibles.

Nunca afirmes que un candidato cumple un requisito sin haber llamado a la
tool verificar_evidencia para ese requisito y haber recibido
tiene_evidencia=true. Si un requisito no tiene evidencia para un candidato,
decláralo en "requisitos_sin_evidencia"; no lo inventes ni lo omitas.

Cuando termines de evaluar a todos los candidatos relevantes, responde
ÚNICAMENTE con este JSON (sin texto adicional, sin markdown):
{"ranking": [{"email_id": "...", "puntaje": 0-100,
  "justificacion": [{"requisito": "...", "evidencia": "..."}],
  "requisitos_sin_evidencia": ["..."]}]}
"""


class ResultadoAgente:
    def __init__(
        self,
        ranking: list[dict] | None,
        pasos: list[dict],
        error: str | None = None,
    ):
        self.ranking = ranking
        self.pasos = pasos
        self.error = error


async def _ejecutar_con_reintentos(
    operacion: Callable[[], Awaitable[Any] | Any],
    nombre_tool: str,
    max_intentos: int = MAX_REINTENTOS_TOOL,
    backoff_inicial: float = BACKOFF_INICIAL_SEGUNDOS,
) -> Any:
    """
    Sprint 4 - Issue #35.

    Ejecuta una operación y reintenta automáticamente cuando ocurre
    una excepción.

    El tiempo de espera crece exponencialmente:

        intento 1 falla -> espera 0.25 s
        intento 2 falla -> espera 0.50 s
        intento 3 falla -> propaga el error

    Los resultados válidos, incluso aquellos que representan un error
    lógico de negocio, no se reintentan. Solo se reintentan excepciones.
    """

    if max_intentos < 1:
        raise ValueError("max_intentos debe ser al menos 1")

    ultimo_error: Exception | None = None

    for intento in range(1, max_intentos + 1):
        try:
            resultado = operacion()

            if isinstance(resultado, Awaitable):
                resultado = await resultado

            if intento > 1:
                logger.info(
                    "Tool '%s' recuperada correctamente en intento %d/%d.",
                    nombre_tool,
                    intento,
                    max_intentos,
                )

            return resultado

        except Exception as error:
            ultimo_error = error

            logger.warning(
                "Tool '%s' falló en intento %d/%d: %s",
                nombre_tool,
                intento,
                max_intentos,
                error,
            )

            if intento >= max_intentos:
                break

            espera = backoff_inicial * (2 ** (intento - 1))

            logger.info(
                "Reintentando tool '%s' en %.2f segundos.",
                nombre_tool,
                espera,
            )

            await asyncio.sleep(espera)

    logger.error(
        "Tool '%s' falló después de %d intentos.",
        nombre_tool,
        max_intentos,
    )

    assert ultimo_error is not None
    raise ultimo_error


def construir_tools(perfiles: list[dict]) -> list:
    """
    Expone agent_tools.py como tools del Claude Agent SDK, cerrando sobre los
    perfiles del batch actual.

    Sprint 4 #35:
    las llamadas a las funciones de negocio están protegidas por retry con
    backoff exponencial ante excepciones transitorias.
    """

    @tool(
        "consultar_perfiles",
        "Lista los candidatos disponibles, o consulta uno por email_id.",
        {"email_id": str},
    )
    async def herramienta_consultar_perfiles(args: dict) -> dict:
        try:
            resultado = await _ejecutar_con_reintentos(
                lambda: agent_tools.consultar_perfiles(
                    perfiles,
                    args.get("email_id") or None,
                ),
                "consultar_perfiles",
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            resultado,
                            ensure_ascii=False,
                        ),
                    }
                ]
            }

        except Exception as error:
            logger.error(
                "Error definitivo en consultar_perfiles: %s",
                error,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Error: la tool consultar_perfiles "
                            f"falló después de {MAX_REINTENTOS_TOOL} "
                            f"intentos: {error}"
                        ),
                    }
                ],
                "is_error": True,
            }

    @tool(
        "verificar_evidencia",
        (
            "Verifica si un requisito de la vacante tiene evidencia textual "
            "real en el perfil de un candidato. Nunca asumas que un candidato "
            "cumple un requisito sin llamar a esta tool primero."
        ),
        {"email_id": str, "requisito": str},
    )
    async def herramienta_verificar_evidencia(args: dict) -> dict:
        try:
            candidatos = await _ejecutar_con_reintentos(
                lambda: agent_tools.consultar_perfiles(
                    perfiles,
                    args.get("email_id"),
                ),
                "consultar_perfiles",
            )

        except Exception as error:
            logger.error(
                "Error definitivo consultando candidato: %s",
                error,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Error: no se pudo consultar el candidato "
                            f"después de {MAX_REINTENTOS_TOOL} intentos: "
                            f"{error}"
                        ),
                    }
                ],
                "is_error": True,
            }

        if not candidatos:
            # HU-14:
            # Una referencia a un candidato inexistente es un error lógico,
            # no un fallo transitorio. Por tanto NO debe reintentarse.
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Error: no existe el candidato "
                            f"'{args.get('email_id')}'."
                        ),
                    }
                ],
                "is_error": True,
            }

        try:
            resultado = await _ejecutar_con_reintentos(
                lambda: agent_tools.verificar_evidencia(
                    candidatos[0],
                    args.get("requisito", ""),
                ),
                "verificar_evidencia",
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            resultado,
                            ensure_ascii=False,
                        ),
                    }
                ]
            }

        except Exception as error:
            logger.error(
                "Error definitivo en verificar_evidencia: %s",
                error,
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Error: la tool verificar_evidencia "
                            f"falló después de {MAX_REINTENTOS_TOOL} "
                            f"intentos: {error}"
                        ),
                    }
                ],
                "is_error": True,
            }


    return [
        herramienta_consultar_perfiles,
        herramienta_verificar_evidencia,
    ]


async def rankear_candidatos_async(
    vacante: dict,
    perfiles: list[dict],
) -> ResultadoAgente:
    """
    Corre el agent loop vía Claude Agent SDK.

    El SDK decide cuándo pensar, cuándo llamar una tool y cuándo entregar
    la respuesta final, hasta MAX_PASOS turnos.

    Los fallos del framework, red, JSON inválido o ranking inválido se
    capturan y se reportan mediante ResultadoAgente.error.
    """

    opciones = ClaudeAgentOptions(
        model=MODELO,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={
            SERVIDOR_MCP: create_sdk_mcp_server(
                name=SERVIDOR_MCP,
                tools=construir_tools(perfiles),
            )
        },
        allowed_tools=[
            f"mcp__{SERVIDOR_MCP}__consultar_perfiles",
            f"mcp__{SERVIDOR_MCP}__verificar_evidencia",
        ],
        max_turns=MAX_PASOS,
        permission_mode="bypassPermissions",
    )

    pasos: list[dict] = []
    texto_final = ""

    try:
        async for mensaje in query(
            prompt=(
                "Vacante: "
                f"{json.dumps(vacante, ensure_ascii=False)}"
            ),
            options=opciones,
        ):
            if isinstance(mensaje, AssistantMessage):
                for bloque in mensaje.content:
                    if isinstance(bloque, TextBlock):
                        pasos.append(
                            {
                                "tipo": "thought",
                                "contenido": bloque.text,
                            }
                        )
                        texto_final = bloque.text

                    elif isinstance(bloque, ToolUseBlock):
                        pasos.append(
                            {
                                "tipo": "accion",
                                "tool": bloque.name,
                                "argumentos": bloque.input,
                            }
                        )

            elif (
                isinstance(mensaje, UserMessage)
                and isinstance(mensaje.content, list)
            ):
                for bloque in mensaje.content:
                    if isinstance(bloque, ToolResultBlock):
                        pasos.append(
                            {
                                "tipo": "observacion",
                                "contenido": bloque.content,
                                "es_error": bool(
                                    bloque.is_error
                                ),
                            }
                        )

            elif isinstance(mensaje, ResultMessage):
                if mensaje.result:
                    texto_final = mensaje.result

                if mensaje.is_error:
                    logger.error(
                        "El agente terminó con error: %s",
                        mensaje.result,
                    )

                    return ResultadoAgente(
                        None,
                        pasos,
                        f"Error del agente: {mensaje.result}",
                    )

    except Exception as e:
        logger.error(
            "Error corriendo el agent loop "
            "(Claude Agent SDK): %s",
            e,
        )

        return ResultadoAgente(
            None,
            pasos,
            f"Error del framework: {e}",
        )

    try:
        respuesta_final = json.loads(texto_final)
        ranking = respuesta_final.get("ranking")

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(
            "El agente no devolvió JSON válido "
            "como respuesta final: %s",
            e,
        )

        return ResultadoAgente(
            None,
            pasos,
            f"Respuesta final inválida: {e}",
        )

    es_valido, error_schema = schema.validar_ranking(
        ranking or []
    )

    if not es_valido:
        logger.error(
            "Ranking inválido contra el schema: %s",
            error_schema,
        )

        return ResultadoAgente(
            None,
            pasos,
            f"Ranking inválido: {error_schema}",
        )

    return ResultadoAgente(
        ranking,
        pasos,
    )


def rankear_candidatos(
    vacante: dict,
    perfiles: list[dict],
) -> ResultadoAgente:
    """
    Wrapper síncrono para llamadores no-async
    (tests, app.py, run_batch.py).
    """
    return asyncio.run(
        rankear_candidatos_async(
            vacante,
            perfiles,
        )
    )