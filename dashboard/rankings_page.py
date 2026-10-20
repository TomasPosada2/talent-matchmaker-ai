
"""Pantalla de rankings y evidencias - Issue #53."""

import streamlit as st

from dashboard.api_client import consultar_api, enviar_api
from dashboard.notifications import crear_notificacion
from dashboard.ranking_view import (
    escapar_markdown,
    preparar_ranking,
    preparar_resumen,
)
from dashboard.ui_style import mostrar_tabla
from src.demo_ranking import generar_ranking_demo


def mostrar_rankings(token: str):
    """Permite generar rankings reales o de demostración."""
    st.title("Rankings")

    st.write(
        "Selecciona una vacante para evaluar candidatos "
        "y consultar las evidencias de cada resultado."
    )

    # -----------------------------------------------------
    # Selección del modo
    # -----------------------------------------------------

    modo = st.radio(
        "Modo de evaluación",
        [
            "Demostración gratuita",
            "Inteligencia artificial (Claude)",
        ],
        index=0,
        key="modo_ranking",
    )

    es_demo = modo == "Demostración gratuita"

    if es_demo:
        st.info(
            "Modo demostración: los resultados se calculan "
            "localmente mediante coincidencias textuales. "
            "No se utiliza inteligencia artificial ni se "
            "generan costos de API. Los puntajes son "
            "orientativos y no deben utilizarse para "
            "decisiones reales de contratación."
        )
    else:
        st.warning(
            "Este modo requiere autenticación y acceso "
            "a Claude. Puede generar costos según tu cuenta."
        )

    # -----------------------------------------------------
    # Consultar plantillas
    # -----------------------------------------------------

    resultado, error = consultar_api(
        "/job-templates",
        token,
    )

    if error:
        st.error(error)
        return

    plantillas = (
        resultado.get("templates", [])
        if isinstance(resultado, dict)
        else []
    )

    if not isinstance(plantillas, list):
        st.error(
            "El servidor devolvió plantillas inválidas."
        )
        return

    plantillas = [
        plantilla
        for plantilla in plantillas
        if isinstance(plantilla, dict)
        and isinstance(plantilla.get("vacante"), dict)
    ]

    if not plantillas:
        st.info(
            "Primero crea una plantilla en la "
            "sección Vacantes."
        )
        return

    opciones = {
        indice: plantilla
        for indice, plantilla in enumerate(plantillas)
    }

    seleccion = st.selectbox(
        "Selecciona una vacante",
        options=list(opciones),
        format_func=lambda indice: (
            opciones[indice].get("nombre")
            or f"Plantilla {indice + 1}"
        ),
    )

    plantilla = opciones[seleccion]
    vacante = plantilla["vacante"]

    st.markdown(
        "**Cargo:** "
        + escapar_markdown(vacante.get("cargo", "Sin especificar"))
    )

    requisitos = vacante.get("requisitos", [])

    if isinstance(requisitos, list):
        st.write("**Requisitos:**")

        for requisito in requisitos:
            st.markdown(f"- {escapar_markdown(requisito)}")

    # -----------------------------------------------------
    # Generación del ranking
    # -----------------------------------------------------

    if st.button(
        "Generar ranking",
        type="primary",
        use_container_width=True,
    ):
        if es_demo:
            with st.spinner(
                "Evaluando candidatos localmente..."
            ):
                respuesta, error_perfiles = consultar_api(
                    "/profiles",
                    token,
                )

                if error_perfiles:
                    st.error(error_perfiles)

                elif not isinstance(respuesta, dict):
                    st.error(
                        "El servidor devolvió una "
                        "respuesta de perfiles inválida."
                    )

                else:
                    perfiles = respuesta.get(
                        "profiles",
                        [],
                    )

                    if not isinstance(perfiles, list):
                        st.error(
                            "El servidor devolvió "
                            "perfiles inválidos."
                        )

                    elif not perfiles:
                        st.warning(
                            "No hay candidatos registrados "
                            "para generar el ranking."
                        )

                    else:
                        datos = generar_ranking_demo(
                            vacante,
                            perfiles,
                        )

                        st.session_state[
                            "ranking_resultado"
                        ] = datos

                        st.session_state[
                            "ranking_plantilla_id"
                        ] = plantilla.get("id")

                        st.session_state[
                            "ranking_modo_resultado"
                        ] = modo

                        st.success(
                            "Ranking de demostración "
                            "generado correctamente."
                        )

                        st.session_state["notificaciones"] = (
                            crear_notificacion(
                                st.session_state.get(
                                    "notificaciones", []
                                ),
                                "Ranking generado",
                                "Se completó un ranking de "
                                "demostración gratuita.",
                                "success",
                            )
                        )

        else:
            with st.spinner(
                "Evaluando candidatos con Claude..."
            ):
                datos, error_ranking = enviar_api(
                    "/rankings",
                    {"vacante": vacante},
                    token,
                )

            if error_ranking:
                st.error(error_ranking)

            elif isinstance(datos, dict):
                st.session_state[
                    "ranking_resultado"
                ] = datos

                st.session_state[
                    "ranking_plantilla_id"
                ] = plantilla.get("id")

                st.session_state[
                    "ranking_modo_resultado"
                ] = modo

                st.success(
                    "Ranking generado correctamente."
                )

                st.session_state["notificaciones"] = (
                    crear_notificacion(
                        st.session_state.get(
                            "notificaciones", []
                        ),
                        "Ranking generado",
                        "Se completó un ranking con Claude.",
                        "success",
                    )
                )

    # -----------------------------------------------------
    # Recuperar resultados de la sesión
    # -----------------------------------------------------

    datos = st.session_state.get(
        "ranking_resultado"
    )

    if not isinstance(datos, dict):
        return

    if (
        st.session_state.get("ranking_plantilla_id")
        != plantilla.get("id")
        or st.session_state.get("ranking_modo_resultado")
        != modo
    ):
        st.info(
            "Genera el ranking para visualizar "
            "los resultados de esta vacante "
            "en el modo seleccionado."
        )
        return

    ranking_original = datos.get(
        "ranking",
        [],
    )

    if not isinstance(ranking_original, list):
        st.error(
            "El servidor devolvió un ranking inválido."
        )
        return

    ranking = preparar_ranking(
        ranking_original
    )

    # -----------------------------------------------------
    # Resumen de resultados
    # -----------------------------------------------------

    st.divider()

    st.header(
        "Resultados del ranking"
    )

    if datos.get("modo_demostracion"):
        st.warning(
            "RESULTADOS SIMULADOS — "
            "Evaluación textual local, sin IA."
        )

    if not ranking:
        st.info(
            "No se encontraron candidatos evaluados."
        )
        return

    st.metric(
        "Candidatos evaluados",
        len(ranking),
    )

    mostrar_tabla(preparar_resumen(ranking))

    # -----------------------------------------------------
    # Evidencias por candidato
    # -----------------------------------------------------

    st.header(
        "Evidencias por candidato"
    )

    for posicion, candidato in enumerate(
        ranking,
        start=1,
    ):
        with st.expander(
            f"#{posicion} — {escapar_markdown(candidato['email_id'])} "
            f"— {candidato['puntaje']} puntos"
        ):
            col1, col2 = st.columns(2)

            col1.metric(
                "Puntaje",
                f"{candidato['puntaje']}/100",
            )

            col2.metric(
                "Confianza",
                (
                    f"{candidato['confianza_porcentaje']}%"
                ),
            )

            st.write(
                "**Explicación de confianza:**"
            )

            st.markdown(
                escapar_markdown(candidato["razon_confianza"])
                or "Sin explicación disponible."
            )

            st.write("**Evidencias:**")

            if candidato["justificacion"]:
                for elemento in candidato[
                    "justificacion"
                ]:
                    if not isinstance(elemento, dict):
                        continue

                    st.markdown(
                        "**Requisito:** "
                        + escapar_markdown(elemento.get("requisito", ""))
                    )

                    st.markdown(
                        "**Evidencia:** "
                        + escapar_markdown(elemento.get("evidencia", ""))
                    )

                    st.divider()

            else:
                st.info(
                    "No hay evidencias registradas."
                )

            st.write(
                "**Requisitos sin evidencia:**"
            )

            if candidato[
                "requisitos_sin_evidencia"
            ]:
                for requisito in candidato[
                    "requisitos_sin_evidencia"
                ]:
                    st.markdown(f"- {escapar_markdown(requisito)}")

            else:
                st.success(
                    "No se registraron requisitos "
                    "sin evidencia textual."
                )

    # -----------------------------------------------------
    # Información adicional
    # -----------------------------------------------------

    if datos.get("modo_demostracion"):
        st.caption(
            "Este ranking se generó localmente. "
            "No se utilizó Claude ni se envió "
            "una notificación por correo."
        )

    elif datos.get("notificacion_enviada"):
        st.caption(
            "La notificación del ranking "
            "fue enviada por correo."
        )

    else:
        st.caption(
            "No se confirmó el envío de "
            "la notificación por correo."
        )
