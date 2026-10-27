"""
Pantalla de rankings y evidencias - Issue #53.

Sprint 8 - #89: cada candidato es una tarjeta con su nombre, barra de
puntaje, confianza y, al desplegarla, un chip por requisito (cumple / sin
evidencia) con la cita del CV.
"""

import streamlit as st

from dashboard.api_client import consultar_api, enviar_api
from dashboard.notifications import crear_notificacion
from dashboard.ranking_view import (
    escapar_markdown,
    preparar_ranking,
    preparar_resumen,
    requisitos_html,
    tarjeta_candidato_html,
)
from dashboard.ui_style import chip, encabezado, fila_de_chips, mostrar_tabla
from src.demo_ranking import generar_ranking_demo

MODO_DEMO = "Demostración gratuita"
MODO_IA = "Inteligencia artificial (Claude)"


def _nombres_por_id(perfiles: list) -> dict:
    nombres = {}
    for perfil in perfiles:
        if isinstance(perfil, dict):
            nombre = (perfil.get("nombre") or {}).get("valor")
            nombres[perfil.get("email_id")] = nombre
    return nombres


def _notificar(texto: str) -> None:
    st.session_state["notificaciones"] = crear_notificacion(
        st.session_state.get("notificaciones", []),
        "Ranking generado",
        texto,
        "success",
    )


def _generar(modo: str, vacante: dict, plantilla: dict, token: str) -> None:
    if modo == MODO_DEMO:
        with st.spinner("Evaluando candidatos localmente..."):
            respuesta, error = consultar_api("/profiles", token)

        perfiles = respuesta.get("profiles", []) if isinstance(respuesta, dict) else None

        if error:
            st.error(error)
            return
        if not isinstance(perfiles, list):
            st.error("El servidor devolvió perfiles inválidos.")
            return
        if not perfiles:
            st.warning("No hay candidatos registrados para generar el ranking.")
            return

        datos = generar_ranking_demo(vacante, perfiles)
        _notificar("Se completó un ranking de demostración gratuita.")

    else:
        with st.spinner(
            "Claude está evaluando a los candidatos. Puede tardar un par de minutos..."
        ):
            # El ranking con IA tarda ~1-2 min (#75): se espera hasta 5 min.
            datos, error = enviar_api(
                "/rankings", {"vacante": vacante}, token, timeout=300
            )

        if error:
            st.error(error)
            return
        if not isinstance(datos, dict):
            st.error("El servidor devolvió un ranking inválido.")
            return

        _notificar("Se completó un ranking con Claude.")

    st.session_state["ranking_resultado"] = datos
    st.session_state["ranking_plantilla_id"] = plantilla.get("id")
    st.session_state["ranking_modo_resultado"] = modo


def mostrar_rankings(token: str):
    """Permite generar rankings reales o de demostración."""
    encabezado(
        "Rankings",
        "Compara a los candidatos con los requisitos de una vacante.",
    )

    resultado, error = consultar_api("/job-templates", token)

    if error:
        st.error(error)
        return

    plantillas = [
        plantilla
        for plantilla in (
            resultado.get("templates", []) if isinstance(resultado, dict) else []
        )
        if isinstance(plantilla, dict) and isinstance(plantilla.get("vacante"), dict)
    ]

    if not plantillas:
        st.info("Primero crea una plantilla en la sección Vacantes.")
        return

    # -----------------------------------------------------
    # Configuración del ranking
    # -----------------------------------------------------

    with st.container(border=True):
        col_vacante, col_modo = st.columns([3, 2])

        with col_vacante:
            seleccion = st.selectbox(
                "Vacante",
                options=list(range(len(plantillas))),
                format_func=lambda i: (
                    plantillas[i].get("nombre") or f"Plantilla {i + 1}"
                ),
            )

        with col_modo:
            modo = st.radio(
                "Modo de evaluación",
                [MODO_DEMO, MODO_IA],
                index=0,
                key="modo_ranking",
                horizontal=True,
            )

        plantilla = plantillas[seleccion]
        vacante = plantilla["vacante"]
        requisitos = vacante.get("requisitos", [])

        fila_de_chips(
            [chip(str(vacante.get("cargo", "Sin cargo")), "primario", "💼")]
            + [chip(str(r), "neutro") for r in requisitos if isinstance(r, str)]
        )

        st.caption(
            "Modo demostración: coincidencia textual local, sin IA y sin costo; "
            "orientativo, no para decisiones reales."
            if modo == MODO_DEMO
            else "Modo IA: Claude verifica cada requisito contra la evidencia del CV. "
            "Tarda unos minutos y genera costo de API."
        )

        if st.button(
            "Generar ranking",
            type="primary",
            icon=":material/play_arrow:",
        ):
            _generar(modo, vacante, plantilla, token)

    # -----------------------------------------------------
    # Resultados de la sesión
    # -----------------------------------------------------

    datos = st.session_state.get("ranking_resultado")

    if not isinstance(datos, dict):
        return

    if (
        st.session_state.get("ranking_plantilla_id") != plantilla.get("id")
        or st.session_state.get("ranking_modo_resultado") != modo
    ):
        st.info(
            "Genera el ranking para ver los resultados de esta vacante "
            "en el modo seleccionado."
        )
        return

    ranking_original = datos.get("ranking", [])

    if not isinstance(ranking_original, list):
        st.error("El servidor devolvió un ranking inválido.")
        return

    ranking = preparar_ranking(ranking_original)

    st.header("Resultados")

    if datos.get("modo_demostracion"):
        st.warning(
            "Resultados simulados: evaluación textual local, sin IA."
        )

    if not ranking:
        st.info("No se encontraron candidatos evaluados.")
        return

    perfiles, _ = consultar_api("/profiles", token)
    nombres = _nombres_por_id(
        perfiles.get("profiles", []) if isinstance(perfiles, dict) else []
    )

    fila_de_chips([
        chip(f"{len(ranking)} candidatos evaluados", "primario"),
        chip(
            f"{sum(1 for c in ranking if not c['requisitos_sin_evidencia'])} cumplen todo",
            "ok",
        ),
    ])

    for posicion, candidato in enumerate(ranking, start=1):
        nombre = nombres.get(candidato["email_id"])

        with st.container(border=True):
            st.markdown(
                tarjeta_candidato_html(posicion, candidato, nombre),
                unsafe_allow_html=True,
            )

            with st.expander(
                f"Ver evidencia de {escapar_markdown(nombre or candidato['email_id'])}"
            ):
                st.markdown(requisitos_html(candidato), unsafe_allow_html=True)
                if candidato["razon_confianza"]:
                    st.caption(escapar_markdown(candidato["razon_confianza"]))

    with st.expander("Ver resumen en tabla"):
        mostrar_tabla(preparar_resumen(ranking))

    if datos.get("modo_demostracion"):
        st.caption(
            "Este ranking se generó localmente: no se usó Claude "
            "ni se envió notificación por correo."
        )
    elif datos.get("notificacion_enviada"):
        st.caption("La notificación del ranking se envió por correo.")
    else:
        st.caption("No se confirmó el envío de la notificación por correo.")
