
"""
Dashboard de reclutamiento - Talent Matchmaker AI.

Sprint 6 - Issue #12:
HU-18: Dashboard for recruiters.

Ejecucion:
    py -m streamlit run dashboard/main.py
"""

import streamlit as st

from dashboard.api_client import consultar_api


# ============================================================
# Configuracion de la pagina
# ============================================================

st.set_page_config(
    page_title="Talent Matchmaker AI | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# Estilos visuales
# ============================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    [data-testid="stMetric"] {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
    }

    [data-testid="stSidebar"] {
        background-color: #f8fafc;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# Estado del dashboard
# ============================================================

if "access_token" not in st.session_state:
    st.session_state["access_token"] = None


# ============================================================
# Navegacion lateral
# ============================================================

with st.sidebar:
    st.title("Talent Matchmaker AI")
    st.caption("Recruitment Dashboard")

    st.divider()

    pagina = st.radio(
        "Navegación",
        [
            "Inicio",
            "Candidatos",
            "Rankings",
            "Vacantes",
            "Notificaciones",
        ],
    )

    st.divider()
    st.caption("Sprint 6 · Dashboard v1")


# ============================================================
# Inicio
# ============================================================

if pagina == "Inicio":
    st.title("Panel de reclutamiento")

    st.write(
        "Bienvenido a Talent Matchmaker AI. "
        "Consulta el estado del sistema y accede "
        "a las herramientas de reclutamiento."
    )

    st.subheader("Estado del sistema")

    estado, error = consultar_api("/health")

    if error:
        st.error(error)

    elif estado and estado.get("status") == "ok":
        st.success("API conectada y funcionando.")

    else:
        st.warning(
            "No fue posible confirmar el estado de la API."
        )

    st.divider()

    # Los perfiles requieren autenticacion JWT.
    total_candidatos = None

    if st.session_state["access_token"]:
        perfiles, error_perfiles = consultar_api(
            "/profiles",
            st.session_state["access_token"],
        )

        if not error_perfiles and perfiles:
            total_candidatos = perfiles.get("total")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Candidatos registrados",
        (
            total_candidatos
            if total_candidatos is not None
            else "—"
        ),
    )

    col2.metric(
        "Rankings generados",
        "—",
    )

    col3.metric(
        "Vacantes activas",
        "—",
    )

    st.caption(
        "Los indicadores sin datos se habilitarán "
        "cuando sus funcionalidades estén disponibles. "
        "El acceso a candidatos requiere autenticación."
    )

    st.subheader("Herramientas disponibles")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.info(
            "**Candidatos**\n\n"
            "Consulta y filtra perfiles procesados."
        )

    with c2:
        st.info(
            "**Rankings**\n\n"
            "Compara candidatos con los requisitos "
            "de una vacante."
        )

    with c3:
        st.info(
            "**Vacantes**\n\n"
            "Gestiona descripciones y plantillas "
            "reutilizables."
        )


# ============================================================
# Candidatos
# ============================================================

elif pagina == "Candidatos":
    st.title("Candidatos")

    st.write(
        "Consulta de perfiles registrados en el sistema."
    )

    if not st.session_state["access_token"]:
        st.info(
            "Esta sección requiere autenticación. "
            "El inicio de sesión se implementará "
            "en el Issue #56."
        )

    else:
        resultado, error = consultar_api(
            "/profiles",
            st.session_state["access_token"],
        )

        if error:
            st.error(error)

        elif resultado:
            perfiles = resultado.get("profiles", [])

            st.metric(
                "Total de candidatos",
                len(perfiles),
            )

            if perfiles:
                st.dataframe(
                    perfiles,
                    use_container_width=True,
                )

            else:
                st.info(
                    "No hay candidatos registrados."
                )


# ============================================================
# Rankings
# ============================================================

elif pagina == "Rankings":
    st.title("Rankings")

    st.info(
        "La visualización de rankings y evidencias "
        "se implementará en el Issue #53."
    )


# ============================================================
# Vacantes
# ============================================================

elif pagina == "Vacantes":
    st.title("Vacantes")

    st.info(
        "La interfaz para crear vacantes "
        "se implementará en el Issue #54."
    )


# ============================================================
# Notificaciones
# ============================================================

elif pagina == "Notificaciones":
    st.title("Notificaciones")

    st.info(
        "El centro de notificaciones "
        "se implementará en el Issue #57."
    )
