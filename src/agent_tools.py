"""
HU-10: Tool para consultar los perfiles estructurados del Sprint 1.
HU-11: Tool para verificar si un requisito tiene evidencia real en un perfil.

Estas son las únicas dos formas en que el agente puede tocar los datos de los
candidatos: nunca lee el CV crudo directamente, y nunca afirma un match sin
pasar por verificar_evidencia (principio anti-alucinación de todo el producto).
"""

import json
from pathlib import Path

_CAMPOS_EVIDENCIABLES = ["educacion", "experiencia", "habilidades"]


def cargar_perfiles(ruta_perfiles: Path) -> list[dict]:
    with open(ruta_perfiles, "r", encoding="utf-8") as f:
        return json.load(f)


def consultar_perfiles(perfiles: list[dict], email_id: str | None = None) -> list[dict]:
    """HU-10: lista todos los perfiles, o filtra a un candidato por email_id."""
    if email_id is None:
        return perfiles
    return [p for p in perfiles if p["email_id"] == email_id]


def verificar_evidencia(perfil: dict, requisito: str) -> dict:
    """
    HU-11: busca el requisito en la evidencia textual del perfil (no en el
    texto completo del CV, solo en lo que ya quedó trazado en Sprint 1).
    Si ninguna palabra clave del requisito aparece en algún campo con
    evidencia, se reporta tiene_evidencia=False explícitamente en vez de
    dejar que el agente asuma un match.
    """
    palabras_clave = [p.lower() for p in requisito.split() if len(p) > 2]

    for campo in _CAMPOS_EVIDENCIABLES:
        evidencia = (perfil.get(campo) or {}).get("evidencia")
        if not evidencia:
            continue
        evidencia_lower = evidencia.lower()
        coincidencias = [p for p in palabras_clave if p in evidencia_lower]
        if coincidencias:
            return {
                "tiene_evidencia": True,
                "campo": campo,
                "evidencia": evidencia,
                "palabras_encontradas": coincidencias,
            }

    return {"tiene_evidencia": False, "campo": None, "evidencia": None, "palabras_encontradas": []}
