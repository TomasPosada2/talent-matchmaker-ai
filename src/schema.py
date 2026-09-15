"""
HU-06: Salida en formato JSON validado por esquema.

Define el esquema fijo que debe cumplir el perfil estructurado de un candidato
y expone una función para validar un dict contra ese esquema.

Sprint 4:
- #40: Confidence scoring per ranking decision.
"""

import jsonschema


# ============================================================
# Schema de perfiles
# ============================================================

# Cada campo "extraíble" sigue el mismo patrón:
# {"valor": ..., "evidencia": ...}
#
# Si no se encontró información:
# valor=None y evidencia=None.
# Nunca se inventa información.

_CAMPO_CON_EVIDENCIA = {
    "type": "object",
    "properties": {
        "valor": {
            "type": [
                "string",
                "array",
                "null",
            ]
        },
        "evidencia": {
            "type": [
                "string",
                "array",
                "null",
            ]
        },
    },
    "required": [
        "valor",
        "evidencia",
    ],
    "additionalProperties": False,
}


PERFIL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "PerfilCandidato",
    "type": "object",
    "properties": {
        "email_id": {
            "type": "string"
        },
        "archivo_origen": {
            "type": "string"
        },
        "nombre": _CAMPO_CON_EVIDENCIA,
        "contacto": {
            "type": "object",
            "properties": {
                "email": _CAMPO_CON_EVIDENCIA,
                "telefono": _CAMPO_CON_EVIDENCIA,
            },
            "required": [
                "email",
                "telefono",
            ],
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


def validar_perfil(
    perfil: dict,
) -> tuple[bool, str | None]:
    """
    Valida un perfil contra PERFIL_SCHEMA.

    Retorna:
        (es_valido, mensaje_error)

    mensaje_error es None si el perfil es válido.
    """

    try:
        jsonschema.validate(
            instance=perfil,
            schema=PERFIL_SCHEMA,
        )

        return True, None

    except jsonschema.exceptions.ValidationError as e:
        return False, str(
            e.message
        )


# ============================================================
# Schema del ranking
# HU-13 + Sprint 4 #40
# ============================================================

# HU-13:
# El ranking debe incluir evidencia citada para cada requisito
# atribuido al candidato.

_JUSTIFICACION_ITEM = {
    "type": "object",
    "properties": {
        "requisito": {
            "type": "string"
        },
        "evidencia": {
            "type": "string"
        },
    },
    "required": [
        "requisito",
        "evidencia",
    ],
    "additionalProperties": False,
}


RANKING_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "email_id": {
            "type": "string"
        },

        # Calidad del match candidato-vacante
        "puntaje": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
        },

        # Sprint 4 - Issue #40
        #
        # Confianza en la decisión del ranking.
        #
        # 0.0 = evidencia insuficiente / decisión muy incierta
        # 1.0 = evidencia completa / decisión altamente sustentada
        "confianza": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },

        # Explicación breve de por qué la decisión tiene
        # ese nivel de confianza.
        "razon_confianza": {
            "type": "string",
            "minLength": 1,
        },

        "justificacion": {
            "type": "array",
            "items": _JUSTIFICACION_ITEM,
        },

        "requisitos_sin_evidencia": {
            "type": "array",
            "items": {
                "type": "string"
            },
        },
    },

    "required": [
        "email_id",
        "puntaje",
        "confianza",
        "razon_confianza",
        "justificacion",
        "requisitos_sin_evidencia",
    ],

    "additionalProperties": False,
}


RANKING_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "RankingCandidatos",
    "type": "array",
    "items": RANKING_ITEM_SCHEMA,
}


def validar_ranking(
    ranking: list,
) -> tuple[bool, str | None]:
    """
    Valida el ranking final del agente contra RANKING_SCHEMA.

    Sprint 4 #40:
    Cada decisión debe contener además:
    - confianza entre 0 y 1;
    - razon_confianza no vacía.
    """

    try:
        jsonschema.validate(
            instance=ranking,
            schema=RANKING_SCHEMA,
        )

        return True, None

    except jsonschema.exceptions.ValidationError as e:
        return False, str(
            e.message
        )