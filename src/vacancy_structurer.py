"""
HU-09: Estructurar la vacante (job description) como input del agente.

Mismo principio de Sprint 1: no se infiere nada que el reclutador no haya
escrito. El "cargo" es la primera línea del texto y los "requisitos" son,
tal cual, las líneas que aparecen bajo el encabezado de requisitos.
"""

import re

ENCABEZADOS_REQUISITOS = {
    "requisitos", "requirements", "requisitos técnicos", "requisitos tecnicos",
}
ENCABEZADOS_CIERRE = {
    "cargo", "puesto", "posición", "posicion", "position", "role", "título", "titulo",
    "beneficios", "benefits", "sobre nosotros", "about us",
}


def _limpiar_item(linea: str) -> str:
    return re.sub(r"^[\-\*•]\s*", "", linea.strip())


def estructurar_vacante(texto: str) -> dict:
    """
    Convierte el texto plano de una vacante en {"cargo": ..., "requisitos": [...]}.
    Si no hay encabezado de requisitos, "requisitos" queda como lista vacía
    (nunca se inventan requisitos que el reclutador no escribió).
    """
    lineas = [linea.strip() for linea in texto.splitlines() if linea.strip()]
    cargo = lineas[0] if lineas else None

    requisitos: list[str] = []
    dentro_de_requisitos = False
    for linea in lineas[1:] if lineas else []:
        normalizada = linea.lower().rstrip(":")
        if normalizada in ENCABEZADOS_REQUISITOS:
            dentro_de_requisitos = True
            continue
        if dentro_de_requisitos:
            if normalizada in ENCABEZADOS_CIERRE:
                break
            requisitos.append(_limpiar_item(linea))

    return {"cargo": cargo, "requisitos": requisitos}
