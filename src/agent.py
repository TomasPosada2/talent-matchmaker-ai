"""
HU-12: Agent loop (Thought -> Action -> Observation) con límite de pasos.
HU-13: Ranking final justificado con evidencia citada por candidato.
HU-14: Manejo de errores del agente (tool falla, LLM alucina un requisito).

Sprint 4: migrado del loop escrito a mano al Claude Agent SDK (framework
oficial de Anthropic, mismo proveedor que ya usábamos vía API). El SDK
maneja el loop Thought/Action/Observation, el despacho de tools y el límite
de turnos; este módulo solo expone las dos tools de negocio (agent_tools.py)
como un servidor MCP en proceso e interpreta la respuesta final.
"""

import asyncio
import json
import logging

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
    def __init__(self, ranking: list[dict] | None, pasos: list[dict], error: str | None = None):
        self.ranking = ranking
        self.pasos = pasos
        self.error = error


def construir_tools(perfiles: list[dict]) -> list:
    """
    Expone agent_tools.py como tools del Claude Agent SDK, cerrando sobre los
    perfiles del batch actual. El agente nunca lee el CV crudo: solo puede
    tocar los datos a través de estas dos tools.

    Devuelve la lista de SdkMcpTool sin envolverla en un servidor MCP para
    poder probar cada handler directamente (ver tests/test_agent.py) sin
    necesitar el binario `claude` instalado.
    """

    @tool(
        "consultar_perfiles",
        "Lista los candidatos disponibles, o consulta uno por email_id.",
        {"email_id": str},
    )
    async def herramienta_consultar_perfiles(args: dict) -> dict:
        resultado = agent_tools.consultar_perfiles(perfiles, args.get("email_id") or None)
        return {"content": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]}

    @tool(
        "verificar_evidencia",
        (
            "Verifica si un requisito de la vacante tiene evidencia textual real "
            "en el perfil de un candidato. Nunca asumas que un candidato cumple "
            "un requisito sin llamar a esta tool primero."
        ),
        {"email_id": str, "requisito": str},
    )
    async def herramienta_verificar_evidencia(args: dict) -> dict:
        candidatos = agent_tools.consultar_perfiles(perfiles, args.get("email_id"))
        if not candidatos:
            # HU-14: el agente pidió evidencia de un candidato que no existe
            # (referencia alucinada) -> se reporta como error de tool, nunca
            # se inventa una respuesta.
            return {
                "content": [{"type": "text", "text": f"Error: no existe el candidato '{args.get('email_id')}'."}],
                "is_error": True,
            }
        resultado = agent_tools.verificar_evidencia(candidatos[0], args.get("requisito", ""))
        return {"content": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]}

    return [herramienta_consultar_perfiles, herramienta_verificar_evidencia]


async def rankear_candidatos_async(vacante: dict, perfiles: list[dict]) -> ResultadoAgente:
    """
    Corre el agent loop vía Claude Agent SDK: el SDK decide cuándo pensar,
    cuándo llamar una tool y cuándo entregar la respuesta final, hasta
    MAX_PASOS turnos. Cualquier fallo (SDK/CLI no disponible, error de red,
    JSON final inválido, ranking que no pasa el schema) se captura y se
    reporta en ResultadoAgente.error en vez de tumbar el proceso completo
    (mismo principio de HU-08 aplicado al agente).
    """
    opciones = ClaudeAgentOptions(
        model=MODELO,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={SERVIDOR_MCP: create_sdk_mcp_server(name=SERVIDOR_MCP, tools=construir_tools(perfiles))},
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
            prompt=f"Vacante: {json.dumps(vacante, ensure_ascii=False)}",
            options=opciones,
        ):
            if isinstance(mensaje, AssistantMessage):
                for bloque in mensaje.content:
                    if isinstance(bloque, TextBlock):
                        pasos.append({"tipo": "thought", "contenido": bloque.text})
                        texto_final = bloque.text
                    elif isinstance(bloque, ToolUseBlock):
                        pasos.append({"tipo": "accion", "tool": bloque.name, "argumentos": bloque.input})
            elif isinstance(mensaje, UserMessage) and isinstance(mensaje.content, list):
                for bloque in mensaje.content:
                    if isinstance(bloque, ToolResultBlock):
                        pasos.append({
                            "tipo": "observacion",
                            "contenido": bloque.content,
                            "es_error": bool(bloque.is_error),
                        })
            elif isinstance(mensaje, ResultMessage):
                if mensaje.result:
                    texto_final = mensaje.result
                if mensaje.is_error:
                    logger.error("El agente terminó con error: %s", mensaje.result)
                    return ResultadoAgente(None, pasos, f"Error del agente: {mensaje.result}")
    except Exception as e:
        # Incluye el caso de este entorno de desarrollo: el binario `claude`
        # (el framework corre sobre el Claude Code CLI) no está instalado.
        logger.error("Error corriendo el agent loop (Claude Agent SDK): %s", e)
        return ResultadoAgente(None, pasos, f"Error del framework: {e}")

    try:
        respuesta_final = json.loads(texto_final)
        ranking = respuesta_final.get("ranking")
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error("El agente no devolvió JSON válido como respuesta final: %s", e)
        return ResultadoAgente(None, pasos, f"Respuesta final inválida: {e}")

    es_valido, error_schema = schema.validar_ranking(ranking or [])
    if not es_valido:
        logger.error("Ranking inválido contra el schema: %s", error_schema)
        return ResultadoAgente(None, pasos, f"Ranking inválido: {error_schema}")

    return ResultadoAgente(ranking, pasos)


def rankear_candidatos(vacante: dict, perfiles: list[dict]) -> ResultadoAgente:
    """Wrapper síncrono para llamadores no-async (tests, app.py, run_batch.py)."""
    return asyncio.run(rankear_candidatos_async(vacante, perfiles))
