
"""Preparación de resultados de ranking para el dashboard."""

import re
from collections.abc import Mapping

# Caracteres con significado en el Markdown de Streamlit (incluye $ de LaTeX
# y : de los emojis/colores con nombre).
_MARKDOWN_ESPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$:])")


def escapar_markdown(texto) -> str:
    """
    Neutraliza el Markdown en texto que proviene de un CV o del LLM.

    Sprint 7 - #61 (A03 Injection): sin esto, un CV con
    ``![x](https://sitio-externo/pixel)`` o ``[clic](https://phishing)``
    se renderizaba como imagen o enlace en la vista del recruiter.
    """
    return _MARKDOWN_ESPECIAL.sub(r"\\\1", str(texto))


def preparar_ranking(ranking: list) -> list[dict]:
    """Ordena los candidatos por puntaje y prepara sus datos."""
    candidatos = []

    for item in ranking:
        if not isinstance(item, Mapping):
            continue

        puntaje = item.get("puntaje", 0)
        confianza = item.get("confianza", 0)

        if not isinstance(puntaje, (int, float)) or isinstance(
            puntaje, bool
        ):
            puntaje = 0

        if not isinstance(confianza, (int, float)) or isinstance(
            confianza, bool
        ):
            confianza = 0

        justificacion = item.get("justificacion") or []
        sin_evidencia = item.get("requisitos_sin_evidencia") or []

        candidatos.append(
            {
                "email_id": str(item.get("email_id", "")),
                "puntaje": puntaje,
                "confianza": confianza,
                "confianza_porcentaje": round(confianza * 100),
                "razon_confianza": str(
                    item.get("razon_confianza") or ""
                ),
                "justificacion": (
                    justificacion
                    if isinstance(justificacion, list)
                    else []
                ),
                "requisitos_sin_evidencia": (
                    sin_evidencia
                    if isinstance(sin_evidencia, list)
                    else []
                ),
            }
        )

    return sorted(
        candidatos,
        key=lambda candidato: candidato["puntaje"],
        reverse=True,
    )


def preparar_resumen(ranking: list[dict]) -> list[dict]:
    """Prepara una tabla resumida de candidatos evaluados."""
    return [
        {
            "Candidato": candidato["email_id"],
            "Puntaje": candidato["puntaje"],
            "Confianza (%)": candidato["confianza_porcentaje"],
            "Requisitos sin evidencia": len(
                candidato["requisitos_sin_evidencia"]
            ),
        }
        for candidato in ranking
    ]
