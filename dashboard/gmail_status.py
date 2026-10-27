"""Estado de la conexión con Gmail en el dashboard - Sprint 8, issue #86."""

import streamlit as st

from dashboard.api_client import consultar_api


def _hace(segundos: int | None) -> str:
    if segundos is None:
        return "hace un momento"
    if segundos < 90:
        return "hace un momento"
    if segundos < 3600:
        return f"hace {round(segundos / 60)} min"
    return f"hace {round(segundos / 3600)} h"


def describir_estado_gmail(estado: dict | None) -> tuple[str, str]:
    """
    Convierte la respuesta de GET /gmail/status en (nivel, mensaje).

    nivel es "ok", "aviso" o "error", para elegir cómo mostrarlo.
    """
    if not isinstance(estado, dict):
        return "aviso", "No fue posible consultar el estado de Gmail."

    if estado.get("conectado"):
        cuenta = estado.get("cuenta") or "cuenta sin identificar"
        nuevos = estado.get("nuevos_ultimo_ciclo") or 0
        total = estado.get("procesados_total") or 0
        return "ok", (
            f"Gmail conectado: {cuenta}. Última revisión "
            f"{_hace(estado.get('segundos_desde_ultimo_ciclo'))}; "
            f"{nuevos} correos nuevos en esa revisión, {total} procesados en total."
        )

    if estado.get("estado") == "error":
        return "error", (
            "La última revisión de Gmail falló: "
            f"{estado.get('detalle') or 'error desconocido'}. "
            "Un administrador debe revisar la conexión."
        )

    if estado.get("estado") == "inactivo":
        return "aviso", (
            "El lector de Gmail no reporta actividad desde "
            f"{_hace(estado.get('segundos_desde_ultimo_ciclo'))}. "
            "Puede estar detenido."
        )

    return "aviso", (
        "Gmail no está conectado: los CVs no llegan automáticamente. "
        "Un administrador puede conectarlo siguiendo docs/runbook.md, sección 3."
    )


def mostrar_estado_gmail(token: str) -> None:
    estado, error = consultar_api("/gmail/status", token)

    if error:
        st.warning(f"No fue posible consultar el estado de Gmail. {error}")
        return

    nivel, mensaje = describir_estado_gmail(estado)

    if nivel == "ok":
        st.success(mensaje)
    elif nivel == "error":
        st.error(mensaje)
    else:
        st.warning(mensaje)
