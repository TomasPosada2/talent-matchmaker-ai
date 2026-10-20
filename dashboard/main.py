
"""
Dashboard de reclutamiento - Talent Matchmaker AI.

Sprint 6:
- Issue #12: Dashboard for recruiters.
- Issue #56: Dashboard login/authentication flow.
- Issue #52: Candidate list with search and filters.
- Issue #54: Job description creation UI.

Ejecución:
    py -m streamlit run dashboard/main.py
"""

import streamlit as st

from dashboard.api_client import (
    consultar_api,
    enviar_api,
    iniciar_sesion,
)
from dashboard.candidate_filters import (
    filtrar_candidatos,
    preparar_tabla,
)


# ---------------------------------------------------------
# Configuración general
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Estado de autenticación
# ---------------------------------------------------------

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
            "Crea y consulta plantillas de vacantes."
        )


# ---------------------------------------------------------
# Candidatos - Issue #52
# ---------------------------------------------------------

elif pagina == "Candidatos":
    st.title("Candidatos")

    st.write(
        "Consulta los perfiles registrados y utiliza "
        "los filtros para encontrar candidatos."
    )

    resultado, error = consultar_api(
        "/profiles",
        st.session_state["access_token"],
    )

    if error:
        st.error(error)

    elif isinstance(resultado, dict):
        perfiles = resultado.get("profiles", [])

        if not isinstance(perfiles, list):
            st.error(
                "El servidor devolvió un formato "
                "de perfiles inválido."
            )
            st.stop()

        st.metric(
            "Total de candidatos registrados",
            len(perfiles),
        )

        st.divider()
        st.subheader("Buscar candidatos")

        col1, col2, col3 = st.columns(3)

        with col1:
            nombre = st.text_input(
                "Nombre",
                placeholder="Ej. María González",
                key="filtro_nombre",
            )

        with col2:
            habilidad = st.text_input(
                "Habilidades",
                placeholder="Ej. Python, Excel, SQL",
                key="filtro_habilidad",
            )

        with col3:
            experiencia = st.text_input(
                "Experiencia",
                placeholder="Ej. ventas, desarrollo, logística",
                key="filtro_experiencia",
            )

        candidatos_filtrados = filtrar_candidatos(
            perfiles,
            nombre=nombre,
            habilidad=habilidad,
            experiencia=experiencia,
        )

        st.divider()
        st.subheader("Resultados")

        col_resultados, col_total = st.columns(2)

        col_resultados.metric(
            "Candidatos encontrados",
            len(candidatos_filtrados),
        )

        col_total.metric(
            "Candidatos disponibles",
            len(perfiles),
        )

        if candidatos_filtrados:
            st.dataframe(
                preparar_tabla(candidatos_filtrados),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                "Los resultados se actualizan "
                "automáticamente al modificar los filtros."
            )

        elif perfiles:
            st.info(
                "No se encontraron candidatos que "
                "coincidan con los filtros seleccionados."
            )

        else:
            st.info(
                "Todavía no hay candidatos registrados "
                "en el sistema."
            )

    else:
        st.warning(
            "No fue posible obtener la lista de candidatos."
        )


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
# Vacantes - Issue #54
# ---------------------------------------------------------

elif pagina == "Vacantes":
    st.title("Vacantes")

    st.write(
        "Crea descripciones estructuradas de vacantes "
        "y guarda plantillas para reutilizarlas."
    )

    tab_crear, tab_consultar = st.tabs(
        ["Crear vacante", "Plantillas guardadas"]
    )

    # -----------------------------------------------------
    # Crear vacante
    # -----------------------------------------------------

    with tab_crear:
        st.subheader("Nueva plantilla de vacante")

        with st.form("formulario_vacante", clear_on_submit=True):
            nombre_plantilla = st.text_input(
                "Nombre de la plantilla",
                placeholder="Ej. Analista de datos - Medellín",
            )

            cargo = st.text_input(
                "Cargo",
                placeholder="Ej. Analista de datos",
            )

            requisitos_texto = st.text_area(
                "Requisitos del cargo",
                placeholder=(
                    "Escribe un requisito por línea:\n"
                    "Experiencia en Python\n"
                    "Conocimiento de SQL\n"
                    "Manejo de Power BI"
                ),
                height=180,
            )

            st.caption(
                "Cada línea se guardará como un requisito "
                "independiente. No se agregarán requisitos "
                "que no hayas escrito."
            )

            guardar = st.form_submit_button(
                "Guardar plantilla",
                use_container_width=True,
            )

        if guardar:
            nombre_limpio = nombre_plantilla.strip()
            cargo_limpio = cargo.strip()

            requisitos = [
                linea.strip()
                for linea in requisitos_texto.splitlines()
                if linea.strip()
            ]

            if not nombre_limpio:
                st.warning(
                    "Debes ingresar un nombre para la plantilla."
                )

            elif not cargo_limpio:
                st.warning(
                    "Debes indicar el cargo de la vacante."
                )

            elif not requisitos:
                st.warning(
                    "Debes ingresar al menos un requisito."
                )

            else:
                datos = {
                    "nombre": nombre_limpio,
                    "vacante": {
                        "cargo": cargo_limpio,
                        "requisitos": requisitos,
                    },
                }

                with st.spinner("Guardando plantilla..."):
                    respuesta, error = enviar_api(
                        "/job-templates",
                        datos,
                        st.session_state["access_token"],
                    )

                if error:
                    st.error(error)

                elif respuesta:
                    st.success(
                        "La plantilla de vacante "
                        "se guardó correctamente."
                    )

                    st.json(respuesta)

                else:
                    st.warning(
                        "El servidor no confirmó "
                        "el guardado de la plantilla."
                    )

    # -----------------------------------------------------
    # Consultar plantillas
    # -----------------------------------------------------

    with tab_consultar:
        st.subheader("Plantillas guardadas")

        if st.button(
            "Actualizar lista",
            key="actualizar_plantillas",
        ):
            st.rerun()

        resultado, error = consultar_api(
            "/job-templates",
            st.session_state["access_token"],
        )

        if error:
            st.error(error)

        elif isinstance(resultado, dict):
            plantillas = resultado.get("templates", [])

            if not isinstance(plantillas, list):
                st.error(
                    "El servidor devolvió un formato "
                    "de plantillas inválido."
                )

            else:
                st.metric(
                    "Plantillas registradas",
                    len(plantillas),
                )

                if not plantillas:
                    st.info(
                        "Todavía no tienes plantillas "
                        "de vacantes guardadas."
                    )

                else:
                    for plantilla in plantillas:
                        if not isinstance(plantilla, dict):
                            continue

                        nombre = plantilla.get(
                            "nombre",
                            "Plantilla sin nombre",
                        )

                        identificador = plantilla.get("id")
                        vacante = plantilla.get("vacante") or {}

                        if not isinstance(vacante, dict):
                            vacante = {}

                        cargo_guardado = vacante.get(
                            "cargo",
                            "No especificado",
                        )

                        requisitos_guardados = vacante.get(
                            "requisitos",
                            [],
                        )

                        if not isinstance(requisitos_guardados, list):
                            requisitos_guardados = []

                        with st.expander(
                            f"{nombre} — {cargo_guardado}"
                        ):
                            st.write(
                                f"**ID:** {identificador}"
                            )

                            st.write(
                                f"**Cargo:** {cargo_guardado}"
                            )

                            st.write("**Requisitos:**")

                            if requisitos_guardados:
                                for requisito in requisitos_guardados:
                                    st.write(f"- {requisito}")
                            else:
                                st.caption(
                                    "Sin requisitos registrados."
                                )

        else:
            st.warning(
                "No fue posible consultar las plantillas."
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
