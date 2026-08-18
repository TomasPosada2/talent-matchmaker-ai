"""
HU-06: Salida en formato JSON validado por esquema.

Define el esquema fijo que debe cumplir el perfil estructurado de un candidato
y expone una función para validar un dict contra ese esquema.
"""

import jsonschema

# Cada campo "extraíble" sigue el mismo patrón: {"valor": ..., "evidencia": ...}
# Si no se encontró información, valor=None y evidencia=None (nunca se inventa).
_CAMPO_CON_EVIDENCIA = {
    "type": "object",
    "properties": {
        "valor": {"type": ["string", "array", "null"]},
        "evidencia": {"type": ["string", "array", "null"]},
    },
    "required": ["valor", "evidencia"],
    "additionalProperties": False,
}

PERFIL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PerfilCandidato",
    "type": "object",
    "properties": {
        "email_id": {"type": "string"},
        "archivo_origen": {"type": "string"},
        "nombre": _CAMPO_CON_EVIDENCIA,
        "contacto": {
            "type": "object",
            "properties": {
                "email": _CAMPO_CON_EVIDENCIA,
                "telefono": _CAMPO_CON_EVIDENCIA,
            },
            "required": ["email", "telefono"],
            "additionalProperties": False,
        },
        "educacion": _CAMPO_CON_EVIDENCIA,
        "experiencia": _CAMPO_CON_EVIDENCIA,
        "habilidades": _CAMPO_CON_EVIDENCIA,
    },
    "required": [
        "email_id",
        "archivo_origen",
        "nombre",
        "contacto",
        "educacion",
        "experiencia",
        "habilidades",
    ],
    "additionalProperties": False,
}


def validar_perfil(perfil: dict) -> tuple[bool, str | None]:
    """
    Valida un perfil contra PERFIL_SCHEMA.
    Retorna (es_valido, mensaje_error). mensaje_error es None si es válido.
    """
    try:
        jsonschema.validate(instance=perfil, schema=PERFIL_SCHEMA)
        return True, None
    except jsonschema.exceptions.ValidationError as e:
        return False, str(e.message)
