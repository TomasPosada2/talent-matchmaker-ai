
"""Preparación de resultados de ranking para el dashboard."""

import html
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


# ============================================================
# Sprint 8 - #89: tarjetas de candidato del ranking
# Todo texto del CV o del LLM pasa por html.escape (#61).
# ============================================================

def tarjeta_candidato_html(posicion: int, candidato: dict, nombre: str | None) -> str:
    """Encabezado de la tarjeta: posición, nombre, barra de puntaje y confianza."""
    puntaje = max(0, min(100, float(candidato.get("puntaje") or 0)))
    nombre_visible = html.escape(nombre or "Candidato sin nombre")
    identificador = html.escape(str(candidato.get("email_id", "")))
    confianza = candidato.get("confianza_porcentaje", 0)

    return (
        '<div class="tm-candidato">'
        f'<div class="tm-posicion">{posicion}</div>'
        '<div class="tm-candidato-info">'
        f'<div class="tm-candidato-nombre">{nombre_visible}</div>'
        f'<div class="tm-candidato-id">{identificador} · confianza {confianza}%</div>'
        f'<div class="tm-barra" role="img" aria-label="Puntaje {puntaje:g} de 100">'
        f'<span style="width:{puntaje:g}%"></span></div>'
        "</div>"
        f'<div class="tm-puntaje">{puntaje:g}<small>de 100</small></div>'
        "</div>"
    )


def requisitos_html(candidato: dict) -> str:
    """Una fila por requisito: chip Cumple con la cita del CV, o Sin evidencia."""
    filas = []

    for elemento in candidato.get("justificacion") or []:
        if not isinstance(elemento, dict):
            continue
        filas.append(
            '<div class="tm-requisito">'
            '<div class="tm-requisito-titulo">'
            '<span class="tm-chip tm-chip-ok">✓ Cumple</span>'
            f"{html.escape(str(elemento.get('requisito', '')))}</div>"
            f'<p class="tm-cita">“{html.escape(str(elemento.get("evidencia", "")))}”</p>'
            "</div>"
        )

    for requisito in candidato.get("requisitos_sin_evidencia") or []:
        filas.append(
            '<div class="tm-requisito">'
            '<div class="tm-requisito-titulo">'
            '<span class="tm-chip tm-chip-aviso">✕ Sin evidencia</span>'
            f"{html.escape(str(requisito))}</div>"
            "</div>"
        )

    return "".join(filas) or "<p>No hay evidencias registradas.</p>"
