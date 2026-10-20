"""
Pantalla de administración - Sprint 7.

- #61: el registro dejó de ser público; aquí un admin crea las cuentas.
- #63: supresión de los datos de un candidato (Ley 1581 de 2012).
"""

import streamlit as st

from dashboard.api_client import consultar_api, eliminar_api, enviar_api
from dashboard.candidate_filters import obtener_valor
from dashboard.ui_style import mostrar_tabla

ROLES = {
    "recruiter": "Recruiter",
    "admin": "Administrador",
}


def _mostrar_usuarios(token: str) -> None:
    st.header("Usuarios")

    resultado, error = consultar_api("/admin/users", token)

    if error:
        st.error(error)
    elif isinstance(resultado, dict):
        usuarios = resultado.get("users", [])
        mostrar_tabla(
            [
                {
                    "Correo": usuario.get("email"),
                    "Rol": ROLES.get(usuario.get("role"), usuario.get("role")),
                    "Creado": str(usuario.get("created_at", ""))[:10],
                }
                for usuario in usuarios
                if isinstance(usuario, dict)
            ]
        )

    st.header("Crear cuenta")

    with st.form("formulario_usuario", clear_on_submit=True):
        correo = st.text_input(
            "Correo electrónico",
            placeholder="recruiter@empresa.com",
        )
        contrasena = st.text_input(
            "Contraseña temporal",
            type="password",
            help="Mínimo 8 caracteres. Compártela por un canal seguro.",
        )
        rol = st.selectbox(
            "Rol",
            options=list(ROLES),
            format_func=ROLES.get,
        )
        crear = st.form_submit_button("Crear cuenta", width="stretch")

    if crear:
        if not correo.strip() or len(contrasena) < 8:
            st.warning(
                "Ingresa un correo y una contraseña "
                "de al menos 8 caracteres."
            )
            return

        respuesta, error = enviar_api(
            "/auth/register",
            {"email": correo.strip(), "password": contrasena, "role": rol},
            token,
        )

        if error:
            st.error(error)
        else:
            st.success(f"Cuenta creada: {respuesta.get('email')}")


def _mostrar_supresion(token: str) -> None:
    st.header("Supresión de datos de un candidato")

    st.write(
        "Atiende una solicitud de supresión (Ley 1581 de 2012): "
        "se borran el perfil y las copias del CV en disco. "
        "Esta acción no se puede deshacer."
    )

    resultado, error = consultar_api("/profiles", token)

    if error:
        st.error(error)
        return

    perfiles = resultado.get("profiles", []) if isinstance(resultado, dict) else []
    opciones = {
        perfil["email_id"]: obtener_valor(perfil, "nombre") or "(sin nombre)"
        for perfil in perfiles
        if isinstance(perfil, dict) and perfil.get("email_id")
    }

    if not opciones:
        st.info("No hay candidatos registrados.")
        return

    email_id = st.selectbox(
        "Candidato",
        options=list(opciones),
        format_func=lambda clave: f"{opciones[clave]} — {clave}",
    )

    confirmar = st.checkbox(
        "Confirmo que el titular solicitó la supresión de sus datos."
    )

    if st.button(
        "Eliminar datos del candidato",
        type="primary",
        disabled=not confirmar,
    ):
        respuesta, error = eliminar_api(f"/profiles/{email_id}", token)

        if error:
            st.error(error)
        else:
            st.success(
                f"Datos de {email_id} eliminados "
                f"(archivos borrados: {respuesta.get('archivos_eliminados', 0)}). "
                "Guarda este mensaje como constancia."
            )


def mostrar_administracion(token: str) -> None:
    st.title("Administración")

    tab_usuarios, tab_supresion = st.tabs(["Usuarios", "Supresión de datos"])

    with tab_usuarios:
        _mostrar_usuarios(token)

    with tab_supresion:
        _mostrar_supresion(token)
