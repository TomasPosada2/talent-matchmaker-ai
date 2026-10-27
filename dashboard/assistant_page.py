"""Página del asistente (chatbot) - Sprint 8, issue #87."""

import re

import streamlit as st

from dashboard.api_client import consultar_api, preguntar_asistente
from dashboard.ranking_view import escapar_markdown

MAX_MENSAJES = 20
MAX_CARACTERES = 2000

EJEMPLOS = [
    "¿Quién sabe Python y SQL?",
    "¿Cuáles son las habilidades más comunes?",
    "¿Qué candidatos no tienen experiencia registrada?",
    "¿Cómo creo una vacante?",
]

_IMAGEN = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_ENLACE = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def limpiar_markdown_respuesta(texto: str) -> str:
    """
    Deja el formato (negritas, listas) pero quita imágenes y enlaces.

    La respuesta puede citar texto de un CV: un CV con
    ``![x](https://externo/pixel)`` no debe cargar nada ni mostrar enlaces
    (misma regla que #61). El signo $ se escapa para que no se lea como
    fórmula.
    """
    texto = _IMAGEN.sub(lambda m: f"[imagen omitida: {m.group(1)}]", texto)
    texto = _ENLACE.sub(r"\1", texto)
    return texto.replace("$", "\\$")


def _mostrar_mensaje(mensaje: dict) -> None:
    if mensaje["rol"] == "usuario":
        with st.chat_message("user"):
            st.markdown(escapar_markdown(mensaje["texto"]))
    else:
        with st.chat_message("assistant"):
            st.markdown(limpiar_markdown_respuesta(mensaje["texto"]))


def mostrar_asistente(token: str) -> None:
    st.title("Asistente")
    st.write(
        "Pregunta por los candidatos y las vacantes registrados. "
        "Las respuestas se basan solo en los datos del sistema y "
        "citan la evidencia de cada CV."
    )

    estado, error = consultar_api("/chat/status", token)

    if error:
        st.error(error)
        return

    if not isinstance(estado, dict) or not estado.get("disponible"):
        st.info(
            "El asistente todavía no está activado. Un administrador debe "
            "definir ANTHROPIC_API_KEY en el archivo .env y reiniciar el "
            "sistema (docs/runbook.md)."
        )
        return

    historial = st.session_state.setdefault("chat_historial", [])

    col_info, col_boton = st.columns([3, 1])
    col_info.caption(
        f"Preguntas disponibles hoy: {estado.get('preguntas_restantes_hoy', '—')}"
    )
    if col_boton.button("Nueva conversación", disabled=not historial):
        st.session_state["chat_historial"] = []
        st.rerun()

    if not historial:
        st.caption("Ejemplos: " + " · ".join(EJEMPLOS))

    for mensaje in historial:
        _mostrar_mensaje(mensaje)

    pregunta = st.chat_input(
        "Escribe tu pregunta",
        max_chars=MAX_CARACTERES,
    )

    if not pregunta or not pregunta.strip():
        return

    historial.append({"rol": "usuario", "texto": pregunta.strip()})
    _mostrar_mensaje(historial[-1])

    with st.chat_message("assistant"):
        with st.spinner("Consultando los datos..."):
            datos, error = preguntar_asistente(historial[-MAX_MENSAJES:], token)

        if error:
            # La pregunta sin respuesta sale del historial para poder reintentar.
            historial.pop()
            st.error(error)
            return

        respuesta = datos.get("respuesta") or "No encontré una respuesta."
        st.markdown(limpiar_markdown_respuesta(respuesta))

    historial.append({"rol": "asistente", "texto": respuesta})
