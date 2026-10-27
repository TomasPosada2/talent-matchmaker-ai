"""
Asistente flotante (chatbot) - Sprint 8, issue #87.

Un botón fijo abajo a la derecha abre un panel de chat que queda visible
mientras el recruiter navega por las demás secciones. El panel no es un
popover porque esos se cierran al hacer clic fuera (por ejemplo, en el
menú); aquí abrir o cerrar depende solo del botón, y la conversación se
conserva en la sesión al cambiar de página.

Streamlit no tiene un widget flotante: los contenedores llevan una ``key``
y el CSS fija su posición (Streamlit les agrega la clase ``st-key-<key>``).
"""

import re

import streamlit as st

from dashboard.api_client import consultar_api, preguntar_asistente
from dashboard.ranking_view import escapar_markdown

MAX_MENSAJES = 20
MAX_CARACTERES = 2000

EJEMPLOS = [
    "¿Quién sabe Python y SQL?",
    "¿Cuáles son las habilidades más comunes?",
    "¿Cómo creo una vacante?",
]

_IMAGEN = re.compile(r"!\[([^\]]*)\]\([^)]*\)")
_ENLACE = re.compile(r"\[([^\]]+)\]\([^)]*\)")

_COLORES = {
    "light": {"fondo": "#ffffff", "borde": "#cbd5e1", "sombra": "rgba(15, 23, 42, 0.18)"},
    "dark": {"fondo": "#1e2330", "borde": "#475569", "sombra": "rgba(0, 0, 0, 0.45)"},
}

_ESTILOS = """
<style>
.st-key-asistente_boton {{
    position: fixed;
    right: 24px;
    bottom: 24px;
    width: auto !important;
    z-index: 999991;
}}
.st-key-asistente_boton button {{
    border-radius: 999px;
    padding: 0.6rem 1.2rem;
    box-shadow: 0 6px 18px {sombra};
}}
.st-key-asistente_panel {{
    position: fixed;
    right: 24px;
    bottom: 88px;
    width: min(420px, calc(100vw - 48px)) !important;
    max-height: calc(100vh - 120px);
    overflow-y: auto;
    z-index: 999990;
    background: {fondo};
    border: 1px solid {borde};
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 12px 32px {sombra};
}}
@media (max-width: 640px) {{
    .st-key-asistente_boton {{ right: 16px; bottom: 16px; }}
    .st-key-asistente_panel {{
        right: 16px;
        left: 16px;
        bottom: 80px;
        width: auto !important;
    }}
}}
</style>
"""


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


def _tema() -> str:
    try:
        tipo = st.context.theme.type
    except AttributeError:
        tipo = None
    return tipo if tipo in _COLORES else "light"


def _alternar_panel() -> None:
    st.session_state["asistente_abierto"] = not st.session_state.get(
        "asistente_abierto", False
    )


def _encolar_pregunta() -> None:
    """Callback del formulario: corre antes de dibujar la página."""
    texto = (st.session_state.get("asistente_pregunta") or "").strip()
    if not texto or st.session_state.get("asistente_pendiente"):
        return

    st.session_state.setdefault("chat_historial", []).append(
        {"rol": "usuario", "texto": texto[:MAX_CARACTERES]}
    )
    st.session_state["asistente_pendiente"] = True
    st.session_state.pop("asistente_error", None)


def _nueva_conversacion() -> None:
    st.session_state["chat_historial"] = []
    st.session_state.pop("asistente_error", None)


def _mostrar_mensaje(mensaje: dict) -> None:
    if mensaje["rol"] == "usuario":
        with st.chat_message("user"):
            st.markdown(escapar_markdown(mensaje["texto"]))
    else:
        with st.chat_message("assistant"):
            st.markdown(limpiar_markdown_respuesta(mensaje["texto"]))


def _responder_pendiente(historial: list[dict], token: str) -> None:
    with st.chat_message("assistant"):
        with st.spinner("Consultando los datos..."):
            datos, error = preguntar_asistente(historial[-MAX_MENSAJES:], token)

    st.session_state["asistente_pendiente"] = False

    if error:
        # La pregunta sin respuesta sale del historial para poder reintentar.
        pregunta = historial.pop()
        st.session_state["asistente_error"] = (
            f"{error} (Pregunta: «{pregunta['texto'][:80]}»)"
        )
        st.rerun()

    respuesta = (datos or {}).get("respuesta") or "No encontré una respuesta."
    historial.append({"rol": "asistente", "texto": respuesta})
    st.rerun()


def _contenido_panel(token: str) -> None:
    st.markdown("**Asistente**")

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

    st.caption(
        "Responde solo con los datos del sistema y cita la evidencia de cada CV. "
        f"Preguntas disponibles hoy: {estado.get('preguntas_restantes_hoy', '—')}."
    )

    historial = st.session_state.setdefault("chat_historial", [])

    with st.container(height=340, border=False, autoscroll=True):
        if not historial:
            st.caption("Ejemplos: " + " · ".join(EJEMPLOS))

        for mensaje in historial:
            _mostrar_mensaje(mensaje)

        if st.session_state.get("asistente_pendiente"):
            _responder_pendiente(historial, token)

    if st.session_state.get("asistente_error"):
        st.error(st.session_state["asistente_error"])

    with st.form("formulario_asistente", clear_on_submit=True, border=False):
        st.text_input(
            "Tu pregunta",
            key="asistente_pregunta",
            max_chars=MAX_CARACTERES,
            placeholder="Escribe tu pregunta",
            label_visibility="collapsed",
        )
        col_enviar, col_nueva = st.columns(2)
        col_enviar.form_submit_button(
            "Enviar",
            key="asistente_enviar",
            type="primary",
            on_click=_encolar_pregunta,
            width="stretch",
        )
        col_nueva.form_submit_button(
            "Nueva conversación",
            key="asistente_nueva",
            on_click=_nueva_conversacion,
            disabled=not historial,
            width="stretch",
        )


def mostrar_asistente_flotante(token: str) -> None:
    """Dibuja el botón flotante y, si está abierto, el panel de chat."""
    st.markdown(_ESTILOS.format(**_COLORES[_tema()]), unsafe_allow_html=True)

    abierto = st.session_state.get("asistente_abierto", False)

    if abierto:
        with st.container(key="asistente_panel"):
            _contenido_panel(token)

    with st.container(key="asistente_boton"):
        st.button(
            "✕ Cerrar asistente" if abierto else "💬 Asistente",
            key="asistente_toggle",
            on_click=_alternar_panel,
            help="Pregunta por los candidatos y las vacantes sin salir de esta página.",
        )
