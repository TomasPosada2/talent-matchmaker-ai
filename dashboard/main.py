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

Sprint 8:
- Issue #87: asistente flotante.
- Issue #89: rediseño visual (tema en .streamlit/config.toml).

Ejecución:
    py -m streamlit run dashboard/main.py
"""

import html

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
from dashboard.gmail_status import chip_estado_gmail
from dashboard.notifications import (
    contar_no_leidas,
    crear_notificacion,
    limpiar_notificaciones,
    marcar_todas_leidas,
)
from dashboard.ranking_view import escapar_markdown
from dashboard.rankings_page import mostrar_rankings
from dashboard.ui_style import (
    acceso_html,
    aplicar_estilos,
    chip,
    encabezado,
    fila_de_chips,
    mostrar_tabla,
)

# ---------------------------------------------------------
# Configuración general
# ---------------------------------------------------------

st.set_page_config(
    page_title="Talent Matchmaker AI",
    page_icon="🎯",
    layout="wide",
    # "auto": abierto en escritorio, plegado en el celular (#60).
    initial_sidebar_state="auto",
)

aplicar_estilos()

# Íconos de Material Symbols para el menú (Streamlit los dibuja en el label).
ICONOS_MENU = {
    "Inicio": ":material/home:",
    "Candidatos": ":material/group:",
    "Rankings": ":material/leaderboard:",
    "Vacantes": ":material/work:",
    "Analítica": ":material/insights:",
    "Notificaciones": ":material/notifications:",
    "Administración": ":material/admin_panel_settings:",
}

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
        "pagina_actual",
    ):
        st.session_state.pop(clave, None)


def ir_a(pagina: str) -> None:
    """Callback de los accesos rápidos: cambia la sección del menú."""
    st.session_state["pagina_actual"] = pagina


def mostrar_login():
    """Muestra el formulario de autenticación."""
    _, centro, _ = st.columns([1, 1.15, 1])

    with centro:
        st.markdown(
            '<div class="tm-login-marca">'
            '<div class="tm-marca-logo" aria-hidden="true">TM</div>'
            "<h1>Talent Matchmaker AI</h1>"
            "<p>Preselección de candidatos con evidencia verificable</p>"
            "</div>",
            unsafe_allow_html=True,
        )

        with st.form("formulario_login"):
            st.header("Iniciar sesión")

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
                type="primary",
                width="stretch",
            )

        st.caption(
            "¿No tienes cuenta? Pídesela a un administrador del sistema."
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

correo_usuario = st.session_state["recruiter_email"] or ""
rol_usuario = (
    "Administrador"
    if st.session_state["recruiter_role"] == "admin"
    else "Recruiter"
)
pendientes = contar_no_leidas(st.session_state["notificaciones"])

with st.sidebar:
    st.markdown(
        '<div class="tm-marca">'
        '<div class="tm-marca-logo" aria-hidden="true">TM</div>'
        "<div><div class=\"tm-marca-nombre\">Talent Matchmaker</div>"
        '<div class="tm-marca-sub">Reclutamiento con evidencia</div></div>'
        "</div>"
        '<div class="tm-usuario">'
        f'<div class="tm-avatar" aria-hidden="true">{html.escape(correo_usuario[:2].upper())}</div>'
        f'<div style="min-width:0"><div class="tm-usuario-correo">{html.escape(correo_usuario)}</div>'
        f'<div class="tm-usuario-rol">{rol_usuario}</div></div>'
        "</div>"
        '<p class="tm-seccion-menu">Menú</p>',
        unsafe_allow_html=True,
    )

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

    if st.session_state.get("pagina_actual") not in paginas:
        st.session_state["pagina_actual"] = "Inicio"

    def etiqueta_menu(nombre: str) -> str:
        etiqueta = f"{ICONOS_MENU[nombre]} {nombre}"
        if nombre == "Notificaciones" and pendientes:
            etiqueta += f" ({pendientes})"
        return etiqueta

    pagina = st.radio(
        "Navegación",
        paginas,
        key="pagina_actual",
        format_func=etiqueta_menu,
        label_visibility="collapsed",
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

    if st.button(
        "Cerrar sesión",
        icon=":material/logout:",
        width="stretch",
    ):
        cerrar_sesion()
        st.rerun()

    st.caption("Talent Matchmaker AI · v1.2")


# ---------------------------------------------------------
# Inicio
# ---------------------------------------------------------

if pagina == "Inicio":
    nombre_saludo = correo_usuario.split("@")[0] if correo_usuario else ""
    encabezado(
        f"Hola, {nombre_saludo}" if nombre_saludo else "Panel de reclutamiento",
        "Este es el estado de tu proceso de reclutamiento.",
    )

    estado, error = consultar_api("/health")
    estado_gmail, _ = consultar_api(
        "/gmail/status",
        st.session_state["access_token"],
    )

    if error:
        chip_api = chip("API sin conexión", "error", "●")
    elif estado and estado.get("status") == "ok":
        chip_api = chip("API conectada", "ok", "●")
    else:
        chip_api = chip("Estado de la API desconocido", "aviso", "●")

    fila_de_chips([chip_api, chip_estado_gmail(estado_gmail)])

    perfiles, error_perfiles = consultar_api(
        "/profiles",
        st.session_state["access_token"],
    )
    plantillas, _ = consultar_api(
        "/job-templates",
        st.session_state["access_token"],
    )

    total_candidatos = (
        perfiles.get("total")
        if not error_perfiles and isinstance(perfiles, dict)
        else None
    )
    total_vacantes = (
        plantillas.get("total") if isinstance(plantillas, dict) else None
    )

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Candidatos",
        total_candidatos if total_candidatos is not None else "—",
    )
    col2.metric(
        "Vacantes",
        total_vacantes if total_vacantes is not None else "—",
    )
    col3.metric("Notificaciones sin leer", pendientes)

    if error_perfiles:
        st.warning(
            "No fue posible consultar los candidatos. "
            "Verifica que tu sesión siga siendo válida."
        )

    st.header("Accesos rápidos")

    accesos = [
        ("Candidatos", "Busca y filtra los perfiles de los CVs.", "👥"),
        ("Rankings", "Compara candidatos contra una vacante.", "🏆"),
        ("Vacantes", "Crea plantillas con cargo y requisitos.", "💼"),
    ]

    for columna, (destino, descripcion, icono) in zip(
        st.columns(3), accesos, strict=True
    ):
        with columna, st.container(border=True):
            st.markdown(
                acceso_html(destino, descripcion, icono),
                unsafe_allow_html=True,
            )
            st.button(
                f"Abrir {destino.lower()}",
                key=f"ir_{destino}",
                on_click=ir_a,
                args=(destino,),
                icon=":material/arrow_forward:",
                width="stretch",
            )


# ---------------------------------------------------------
# Candidatos - Issue #52
# ---------------------------------------------------------

elif pagina == "Candidatos":
    encabezado(
        "Candidatos",
        "Perfiles extraídos de las hojas de vida, con su evidencia.",
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

        with st.container(border=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                nombre = st.text_input(
                    "Nombre",
                    placeholder="Ej. María González",
                    key="filtro_nombre",
                    icon=":material/person_search:",
                )

            with col2:
                habilidad = st.text_input(
                    "Habilidades",
                    placeholder="Ej. Python, Excel, SQL",
                    key="filtro_habilidad",
                    icon=":material/psychology:",
                )

            with col3:
                experiencia = st.text_input(
                    "Experiencia",
                    placeholder="Ej. ventas, desarrollo",
                    key="filtro_experiencia",
                    icon=":material/work_history:",
                )

        candidatos_filtrados = filtrar_candidatos(
            perfiles,
            nombre=nombre,
            habilidad=habilidad,
            experiencia=experiencia,
        )

        fila_de_chips([
            chip(
                f"{len(candidatos_filtrados)} de {len(perfiles)} candidatos",
                "primario",
            ),
        ])

        if candidatos_filtrados:
            mostrar_tabla(preparar_tabla(candidatos_filtrados))

        elif perfiles:
            st.info(
                "No se encontraron candidatos que "
                "coincidan con los filtros seleccionados."
            )

        else:
            st.info(
                "Todavía no hay candidatos registrados. "
                "Llegarán solos cuando Gmail esté conectado."
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
    encabezado(
        "Vacantes",
        "Plantillas con el cargo y los requisitos contra los que se rankea.",
    )

    tab_crear, tab_consultar = st.tabs(
        [":material/add: Crear vacante", ":material/list: Plantillas guardadas"]
    )

    with tab_crear:
        with st.form("formulario_vacante", clear_on_submit=True):
            st.header("Nueva plantilla")

            col_nombre, col_cargo = st.columns(2)

            nombre_plantilla = col_nombre.text_input(
                "Nombre de la plantilla",
                placeholder="Ej. Analista de datos - Medellín",
            )

            cargo = col_cargo.text_input(
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
                height=160,
            )

            st.caption(
                "Cada línea se guardará como un requisito "
                "independiente. No se agregarán requisitos "
                "que no hayas escrito."
            )

            guardar = st.form_submit_button(
                "Guardar plantilla",
                type="primary",
                icon=":material/save:",
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
                        f"Se guardó la plantilla «{nombre_limpio}» "
                        f"con {len(requisitos)} requisitos."
                    )

                    st.session_state["notificaciones"] = (
                        crear_notificacion(
                            st.session_state["notificaciones"],
                            "Vacante creada",
                            f"Se guardó la plantilla: {nombre_limpio}",
                            "success",
                        )
                    )

                else:
                    st.warning(
                        "El servidor no confirmó "
                        "el guardado de la plantilla."
                    )

    with tab_consultar:
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

            elif not plantillas:
                st.info(
                    "Todavía no tienes plantillas "
                    "de vacantes guardadas."
                )

            else:
                fila_de_chips([
                    chip(f"{len(plantillas)} plantillas", "primario"),
                ])

                for plantilla in plantillas:
                    if not isinstance(plantilla, dict):
                        continue

                    vacante = plantilla.get("vacante") or {}
                    if not isinstance(vacante, dict):
                        vacante = {}

                    requisitos_guardados = vacante.get("requisitos", [])
                    if not isinstance(requisitos_guardados, list):
                        requisitos_guardados = []

                    with st.container(border=True):
                        st.markdown(
                            f"**{escapar_markdown(plantilla.get('nombre', 'Plantilla sin nombre'))}**  \n"
                            f"Cargo: {escapar_markdown(vacante.get('cargo', 'No especificado'))}"
                        )
                        if requisitos_guardados:
                            fila_de_chips([
                                chip(str(requisito), "neutro")
                                for requisito in requisitos_guardados
                            ])
                        else:
                            st.caption("Sin requisitos registrados.")

        else:
            st.warning(
                "No fue posible consultar las plantillas."
            )


# ---------------------------------------------------------
# Analítica, Administración y Notificaciones
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
    encabezado(
        "Notificaciones",
        "Eventos de esta sesión: vacantes creadas, rankings generados.",
    )

    notificaciones = st.session_state["notificaciones"]

    col_estado, col_leer, col_limpiar = st.columns([2, 1, 1])
    with col_estado:
        fila_de_chips([chip(f"{pendientes} sin leer", "primario")])
    with col_leer:
        if st.button(
            "Marcar como leídas",
            icon=":material/done_all:",
            width="stretch",
            disabled=not pendientes,
        ):
            st.session_state["notificaciones"] = (
                marcar_todas_leidas(notificaciones)
            )
            st.rerun()
    with col_limpiar:
        if st.button(
            "Limpiar",
            icon=":material/delete_sweep:",
            width="stretch",
            disabled=not notificaciones,
        ):
            st.session_state["notificaciones"] = (
                limpiar_notificaciones()
            )
            st.rerun()

    if not notificaciones:
        st.info("No hay notificaciones en esta sesión.")
    else:
        for notificacion in notificaciones:
            with st.container(border=True):
                estado_chip = (
                    chip("Leída", "neutro")
                    if notificacion["leida"]
                    else chip("Nueva", "primario")
                )
                st.markdown(
                    f"**{html.escape(notificacion['titulo'])}** &nbsp; {estado_chip}",
                    unsafe_allow_html=True,
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
