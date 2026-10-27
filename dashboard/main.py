
"""
Dashboard de reclutamiento - Talent Matchmaker AI.

Sprint 6:
- Issue #12: Dashboard for recruiters.
- Issue #56: Dashboard login/authentication flow.
- Issue #52: Candidate list with search and filters.
- Issue #54: Job description creation UI.
- Issue #53: Ranking results and evidence drill-down.

Sprint 7:
- Issue #59: accesibilidad (tablas accesibles, idioma, títulos, mensajes).
- Issues #61/#63: administración de cuentas y supresión de datos.

Ejecución:
    py -m streamlit run dashboard/main.py
"""

import streamlit as st

from dashboard.admin_page import mostrar_administracion
from dashboard.analytics import mostrar_analitica
from dashboard.api_client import (
    consultar_api,
    enviar_api,
    iniciar_sesion,
)
from dashboard.assistant_page import mostrar_asistente_flotante
from dashboard.candidate_filters import (
    filtrar_candidatos,
    preparar_tabla,
)
from dashboard.gmail_status import mostrar_estado_gmail
from dashboard.notifications import (
    contar_no_leidas,
    crear_notificacion,
    limpiar_notificaciones,
    marcar_todas_leidas,
)
from dashboard.rankings_page import mostrar_rankings
from dashboard.ui_style import aplicar_estilos, mostrar_tabla

# ---------------------------------------------------------
# Configuración general
# ---------------------------------------------------------

st.set_page_config(
    page_title="Talent Matchmaker AI | Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

aplicar_estilos()

# ---------------------------------------------------------
# Estado de autenticación
# ---------------------------------------------------------

if "notificaciones" not in st.session_state:
    st.session_state["notificaciones"] = []

if "access_token" not in st.session_state:
    st.session_state["access_token"] = None

if "recruiter_email" not in st.session_state:
    st.session_state["recruiter_email"] = None

if "recruiter_role" not in st.session_state:
    st.session_state["recruiter_role"] = None


def cerrar_sesion():
    """Elimina los datos de autenticación de la sesión actual."""
    st.session_state["access_token"] = None
    st.session_state["recruiter_email"] = None
    st.session_state["recruiter_role"] = None
    st.session_state["notificaciones"] = []
    st.session_state.pop("ranking_resultado", None)
    st.session_state.pop("ranking_plantilla_id", None)
    for clave in (
        "chat_historial",
        "asistente_abierto",
        "asistente_pendiente",
        "asistente_error",
    ):
        st.session_state.pop(clave, None)


def mostrar_login():
    """Muestra el formulario de autenticación."""
    st.title("Talent Matchmaker AI")
    st.header("Iniciar sesión")

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
                width="stretch",
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

            usuario, _ = consultar_api("/auth/me", token)
            st.session_state["recruiter_role"] = (
                usuario.get("role") if isinstance(usuario, dict) else None
            )

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

    paginas = [
        "Inicio",
        "Candidatos",
        "Rankings",
        "Vacantes",
        "Analítica",
        "Notificaciones",
    ]

    if st.session_state["recruiter_role"] == "admin":
        paginas.append("Administración")

    pagina = st.radio("Navegación", paginas)

    pendientes = contar_no_leidas(
        st.session_state["notificaciones"]
    )
    if pendientes:
        st.caption(
            f"Notificaciones pendientes: {pendientes}"
        )

    st.divider()

    st.toggle(
        "Tablas accesibles",
        key="tablas_accesibles",
        help=(
            "Muestra las tablas como HTML simple, "
            "compatible con lectores de pantalla."
        ),
    )

    st.divider()

    if st.button(
        "Cerrar sesión",
        width="stretch",
    ):
        cerrar_sesion()
        st.rerun()

    st.caption("Dashboard v1.1")


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

    st.header("Estado del sistema")

    estado, error = consultar_api("/health")

    if error:
        st.error(error)

    elif estado and estado.get("status") == "ok":
        st.success("API conectada y funcionando.")

    else:
        st.warning(
            "No fue posible confirmar el estado de la API."
        )

    mostrar_estado_gmail(st.session_state["access_token"])

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

    plantillas, _ = consultar_api(
        "/job-templates",
        st.session_state["access_token"],
    )

    total_vacantes = (
        plantillas.get("total")
        if isinstance(plantillas, dict)
        else None
    )

    col2.metric(
        "Vacantes guardadas",
        total_vacantes if total_vacantes is not None else "—",
    )
    col3.metric(
        "Notificaciones sin leer",
        contar_no_leidas(st.session_state["notificaciones"]),
    )

    if error_perfiles:
        st.warning(
            "No fue posible consultar los candidatos. "
            "Verifica que tu sesión siga siendo válida."
        )

    st.header("Herramientas disponibles")

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
        st.header("Buscar candidatos")

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
        st.header("Resultados")

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
            mostrar_tabla(preparar_tabla(candidatos_filtrados))

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
# Rankings - Issue #53
# ---------------------------------------------------------

elif pagina == "Rankings":
    mostrar_rankings(
        st.session_state["access_token"]
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

    with tab_crear:
        st.header("Nueva plantilla de vacante")

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
                width="stretch",
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

                    st.session_state["notificaciones"] = (
                        crear_notificacion(
                            st.session_state["notificaciones"],
                            "Vacante creada",
                            f"Se guardó la plantilla: {nombre_limpio}",
                            "success",
                        )
                    )

                    st.json(respuesta)

                else:
                    st.warning(
                        "El servidor no confirmó "
                        "el guardado de la plantilla."
                    )

    with tab_consultar:
        st.header("Plantillas guardadas")

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

elif pagina == "Analítica":
    mostrar_analitica(
        st.session_state["access_token"]
    )

elif pagina == "Administración":
    mostrar_administracion(
        st.session_state["access_token"]
    )

elif pagina == "Notificaciones":
    st.title("Notificaciones")
    st.write("Consulta los eventos de esta sesión.")

    notificaciones = st.session_state["notificaciones"]
    pendientes = contar_no_leidas(notificaciones)
    st.metric("Sin leer", pendientes)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Marcar todas como leídas"):
            st.session_state["notificaciones"] = (
                marcar_todas_leidas(notificaciones)
            )
            st.rerun()
    with col2:
        if st.button("Limpiar notificaciones"):
            st.session_state["notificaciones"] = (
                limpiar_notificaciones()
            )
            st.rerun()

    if not notificaciones:
        st.info("No hay notificaciones en esta sesión.")
    else:
        for notificacion in notificaciones:
            estado = (
                "Leída" if notificacion["leida"] else "Sin leer"
            )
            with st.container(border=True):
                st.write(
                    f"**{notificacion['titulo']}** "
                    f"— {estado}"
                )
                st.caption(notificacion["fecha"])
                st.write(notificacion["mensaje"])


# ---------------------------------------------------------
# Asistente flotante - Issue #87
# Se dibuja al final para que la sección actual aparezca primero.
# ---------------------------------------------------------

mostrar_asistente_flotante(
    st.session_state["access_token"]
)
