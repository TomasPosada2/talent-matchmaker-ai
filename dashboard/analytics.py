
"""Panel de analítica del dashboard - Issue #58."""

from collections import Counter

import streamlit as st

from dashboard.api_client import consultar_api
from dashboard.candidate_filters import (
    convertir_a_texto,
    obtener_valor,
)
from dashboard.ranking_view import preparar_ranking
from dashboard.ui_style import encabezado, mostrar_tabla


def calcular_habilidades(perfiles: list[dict]) -> list[dict]:
    """Cuenta habilidades registradas en los perfiles."""
    contador = Counter()

    for perfil in perfiles:
        if not isinstance(perfil, dict):
            continue

        valor = obtener_valor(perfil, "habilidades")

        if isinstance(valor, list):
            habilidades = [
                convertir_a_texto(item).strip()
                for item in valor
            ]
        elif isinstance(valor, str):
            habilidades = [
                item.strip()
                for item in valor.replace(";", ",").split(",")
            ]
        else:
            habilidades = []

        for habilidad in set(habilidades):
            if habilidad:
                contador[habilidad.casefold()] += 1

    return [
        {
            "Habilidad": habilidad,
            "Candidatos": cantidad,
        }
        for habilidad, cantidad in contador.most_common(10)
    ]


def calcular_metricas_ranking(datos: dict) -> dict:
    """Calcula indicadores del último ranking disponible."""
    ranking = preparar_ranking(datos.get("ranking", []))

    if not ranking:
        return {
            "evaluados": 0,
            "promedio": 0,
            "maximo": 0,
        }

    puntajes = [
        candidato["puntaje"]
        for candidato in ranking
    ]

    return {
        "evaluados": len(ranking),
        "promedio": round(sum(puntajes) / len(puntajes), 1),
        "maximo": max(puntajes),
    }


def mostrar_analitica(token: str):
    """Muestra métricas y gráficos de reclutamiento."""
    encabezado(
        "Analítica",
        "Indicadores de candidatos, vacantes y del último ranking.",
    )

    respuesta_perfiles, error_perfiles = consultar_api(
        "/profiles",
        token,
    )

    respuesta_plantillas, error_plantillas = consultar_api(
        "/job-templates",
        token,
    )

    if error_perfiles:
        st.error(error_perfiles)
        return

    if error_plantillas:
        st.error(error_plantillas)
        return

    perfiles = (
        respuesta_perfiles.get("profiles", [])
        if isinstance(respuesta_perfiles, dict)
        else []
    )

    plantillas = (
        respuesta_plantillas.get("templates", [])
        if isinstance(respuesta_plantillas, dict)
        else []
    )

    if not isinstance(perfiles, list):
        st.error("Formato de candidatos inválido.")
        return

    if not isinstance(plantillas, list):
        st.error("Formato de vacantes inválido.")
        return

    st.header("Indicadores generales")

    col1, col2 = st.columns(2)

    col1.metric(
        "Candidatos registrados",
        len(perfiles),
    )

    col2.metric(
        "Plantillas de vacantes",
        len(plantillas),
    )

    st.header("Habilidades más frecuentes")

    habilidades = calcular_habilidades(perfiles)

    if habilidades:
        st.bar_chart(
            habilidades,
            x="Habilidad",
            y="Candidatos",
            horizontal=True,
            sort="-Candidatos",
            x_label="Candidatos",
            y_label="",
        )

        # Alternativa textual del gráfico (WCAG 1.1.1).
        mostrar_tabla(habilidades)
    else:
        st.info(
            "No hay suficientes habilidades "
            "estructuradas para generar el gráfico."
        )

    st.header("Último ranking de la sesión")

    datos = st.session_state.get("ranking_resultado")

    if not isinstance(datos, dict):
        st.info(
            "Todavía no se ha generado un ranking "
            "durante esta sesión."
        )
        return

    metricas = calcular_metricas_ranking(datos)

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Candidatos evaluados",
        metricas["evaluados"],
    )

    col2.metric(
        "Puntaje promedio",
        metricas["promedio"],
    )

    col3.metric(
        "Puntaje máximo",
        metricas["maximo"],
    )

    if datos.get("modo_demostracion"):
        st.warning(
            "Estos resultados corresponden al modo "
            "de demostración gratuita. No son "
            "evaluaciones realizadas por inteligencia artificial."
        )

    ranking = preparar_ranking(
        datos.get("ranking", [])
    )

    if ranking:
        tabla = [
            {
                "Candidato": candidato["email_id"],
                "Puntaje": candidato["puntaje"],
            }
            for candidato in ranking
        ]

        st.bar_chart(
            tabla,
            x="Candidato",
            y="Puntaje",
            sort="-Puntaje",
        )

        # Alternativa textual del gráfico (WCAG 1.1.1).
        mostrar_tabla(tabla)

    st.caption(
        "Los indicadores del ranking corresponden "
        "únicamente a la sesión actual. "
        "No representan un historial de evaluaciones."
    )
