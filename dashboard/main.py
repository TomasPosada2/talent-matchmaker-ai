
"""
Dashboard de reclutamiento - Talent Matchmaker AI.

Sprint 6:
- Issue #12: Dashboard for recruiters.
- Issue #56: Dashboard login/authentication flow.

Ejecución:
    py -m streamlit run dashboard/main.py
"""

import streamlit as st

from dashboard.api_client import consultar_api, iniciar_sesion


st.set_page_config(
    page_title="Talent Matchmaker AI | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

if "recruiter_email" not in st.session_state:
    st.session_state["recruiter_email"] = None


def cerrar_sesion():
    """Elimina los datos de autenticación de la sesión actual."""
    st.session_state["access_token"] = None
    st.session_state["recruiter_email"] = None


def mostrar_login():
    """Muestra el formulario de autenticación."""
    st.title("Talent Matchmaker AI")
    st.subheader("Iniciar sesión")
    st.write(
        "Ingresa tus credenciales para acceder "
        "al panel de reclutamiento."
    )

    izquierda, centro, derecha = st.columns([1, 2, 1])

    with centro:
        with st.form("formulario_login"):
            correo = st.text_input(
                "Correo electrónico",
                placeholder="recruiter@empresa.com",
            )

            contrasena = st.text_input(
                "Contraseña",
                type="password",
            )

            enviar = st.form_submit_button(
                "Iniciar sesión",
                use_container_width=True,
            )

        if enviar:
            if not correo.strip() or not contrasena:
                st.warning(
                    "Debes ingresar tu correo y contraseña."
                )
                return

            with st.spinner("Verificando credenciales..."):
                datos, error = iniciar_sesion(
                    correo.strip(),
                    contrasena,
                )

            if error:
                st.error(error)
                return

            token = (
                datos.get("access_token")
                if isinstance(datos, dict)
                else None
            )

            if not token:
                st.error(
                    "El servidor no devolvió un token válido."
                )
                return

            st.session_state["access_token"] = token
            st.session_state["recruiter_email"] = correo.strip()

            st.rerun()


# ---------------------------------------------------------
# Control de acceso
# ---------------------------------------------------------

if not st.session_state["access_token"]:
    mostrar_login()
    st.stop()


# ---------------------------------------------------------
# Menú lateral
# ---------------------------------------------------------

with st.sidebar:
    st.title("Talent Matchmaker AI")
    st.caption("Recruitment Dashboard")
    st.divider()

    st.caption("Sesión iniciada")
    st.write(st.session_state["recruiter_email"])

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

    if st.button(
        "Cerrar sesión",
        use_container_width=True,
    ):
        cerrar_sesion()
        st.rerun()

    st.caption("Sprint 6 · Dashboard v1")


# ---------------------------------------------------------
# Inicio
# ---------------------------------------------------------

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

    perfiles, error_perfiles = consultar_api(
        "/profiles",
        st.session_state["access_token"],
    )

    total_candidatos = None

    if not error_perfiles and isinstance(perfiles, dict):
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

    col2.metric("Rankings generados", "—")
    col3.metric("Vacantes activas", "—")

    if error_perfiles:
        st.warning(
            "No fue posible consultar los candidatos. "
            "Verifica que tu sesión siga siendo válida."
        )

    st.caption(
        "Los indicadores sin datos se habilitarán "
        "cuando sus funcionalidades estén disponibles."
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


# ---------------------------------------------------------
# Candidatos
# ---------------------------------------------------------

elif pagina == "Candidatos":
    st.title("Candidatos")
    st.write(
        "Consulta de perfiles registrados en el sistema."
    )

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
            st.info("No hay candidatos registrados.")


# ---------------------------------------------------------
# Rankings
# ---------------------------------------------------------

elif pagina == "Rankings":
    st.title("Rankings")
    st.info(
        "La visualización de rankings y evidencias "
        "se implementará en el Issue #53."
    )


# ---------------------------------------------------------
# Vacantes
# ---------------------------------------------------------

elif pagina == "Vacantes":
    st.title("Vacantes")
    st.info(
        "La interfaz para crear vacantes "
        "se implementará en el Issue #54."
    )


# ---------------------------------------------------------
# Notificaciones
# ---------------------------------------------------------

elif pagina == "Notificaciones":
    st.title("Notificaciones")
    st.info(
        "El centro de notificaciones "
        "se implementará en el Issue #57."
    )
