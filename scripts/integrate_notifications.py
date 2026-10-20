
"""Integra las notificaciones del Issue #57 en el dashboard."""

from pathlib import Path


MAIN = Path("dashboard/main.py")
RANKINGS = Path("dashboard/rankings_page.py")


def reemplazar_una_vez(texto, anterior, nuevo, archivo):
    cantidad = texto.count(anterior)

    if cantidad != 1:
        raise RuntimeError(
            f"{archivo}: se esperaban 1 coincidencia "
            f"y se encontraron {cantidad}: {anterior[:65]!r}"
        )

    return texto.replace(anterior, nuevo, 1)


def actualizar_main(texto):
    texto = reemplazar_una_vez(
        texto,
        "from dashboard.rankings_page import mostrar_rankings",
        (
            "from dashboard.rankings_page import mostrar_rankings\n"
            "from dashboard.notifications import (\n"
            "    crear_notificacion,\n"
            "    contar_no_leidas,\n"
            "    marcar_todas_leidas,\n"
            "    limpiar_notificaciones,\n"
            ")"
        ),
        MAIN,
    )

    texto = reemplazar_una_vez(
        texto,
        'if "access_token" not in st.session_state:',
        (
            'if "notificaciones" not in st.session_state:\n'
            '    st.session_state["notificaciones"] = []\n\n'
            'if "access_token" not in st.session_state:'
        ),
        MAIN,
    )

    texto = reemplazar_una_vez(
        texto,
        '    st.session_state.pop("ranking_resultado", None)',
        (
            '    st.session_state["notificaciones"] = []\n'
            '    st.session_state.pop("ranking_resultado", None)'
        ),
        MAIN,
    )

    texto = reemplazar_una_vez(
        texto,
        '    st.divider()\n\n    if st.button(\n        "Cerrar sesión",',
        (
            '    pendientes = contar_no_leidas(\n'
            '        st.session_state["notificaciones"]\n'
            '    )\n'
            '    if pendientes:\n'
            '        st.caption(\n'
            '            f"Notificaciones pendientes: {pendientes}"\n'
            '        )\n\n'
            '    st.divider()\n\n'
            '    if st.button(\n        "Cerrar sesión",'
        ),
        MAIN,
    )

    texto = reemplazar_una_vez(
        texto,
        (
            '                    st.success(\n'
            '                        "La plantilla de vacante "\n'
            '                        "se guardó correctamente."\n'
            '                    )'
        ),
        (
            '                    st.success(\n'
            '                        "La plantilla de vacante "\n'
            '                        "se guardó correctamente."\n'
            '                    )\n\n'
            '                    st.session_state["notificaciones"] = (\n'
            '                        crear_notificacion(\n'
            '                            st.session_state["notificaciones"],\n'
            '                            "Vacante creada",\n'
            '                            f"Se guardó la plantilla: {nombre_limpio}",\n'
            '                            "success",\n'
            '                        )\n'
            '                    )'
        ),
        MAIN,
    )

    texto = reemplazar_una_vez(
        texto,
        (
            'elif pagina == "Notificaciones":\n'
            '    st.title("Notificaciones")\n\n'
            '    st.info(\n'
            '        "El centro de notificaciones "\n'
            '        "se implementará en el Issue #57."\n'
            '    )'
        ),
        (
            'elif pagina == "Notificaciones":\n'
            '    st.title("Notificaciones")\n'
            '    st.write("Consulta los eventos de esta sesión.")\n\n'
            '    notificaciones = st.session_state["notificaciones"]\n'
            '    pendientes = contar_no_leidas(notificaciones)\n'
            '    st.metric("Sin leer", pendientes)\n\n'
            '    col1, col2 = st.columns(2)\n'
            '    with col1:\n'
            '        if st.button("Marcar todas como leídas"):\n'
            '            st.session_state["notificaciones"] = (\n'
            '                marcar_todas_leidas(notificaciones)\n'
            '            )\n'
            '            st.rerun()\n'
            '    with col2:\n'
            '        if st.button("Limpiar notificaciones"):\n'
            '            st.session_state["notificaciones"] = (\n'
            '                limpiar_notificaciones()\n'
            '            )\n'
            '            st.rerun()\n\n'
            '    if not notificaciones:\n'
            '        st.info("No hay notificaciones en esta sesión.")\n'
            '    else:\n'
            '        for notificacion in notificaciones:\n'
            '            estado = (\n'
            '                "Leída" if notificacion["leida"] else "Sin leer"\n'
            '            )\n'
            '            with st.container(border=True):\n'
            '                st.write(\n'
            '                    f"**{notificacion[\'titulo\']}** "\n'
            '                    f"— {estado}"\n'
            '                )\n'
            '                st.caption(notificacion["fecha"])\n'
            '                st.write(notificacion["mensaje"])'
        ),
        MAIN,
    )

    return texto


def actualizar_rankings(texto):
    texto = reemplazar_una_vez(
        texto,
        "from src.demo_ranking import generar_ranking_demo",
        (
            "from src.demo_ranking import generar_ranking_demo\n"
            "from dashboard.notifications import crear_notificacion"
        ),
        RANKINGS,
    )

    texto = reemplazar_una_vez(
        texto,
        (
            '                        st.success(\n'
            '                            "Ranking de demostración "\n'
            '                            "generado correctamente."\n'
            '                        )'
        ),
        (
            '                        st.success(\n'
            '                            "Ranking de demostración "\n'
            '                            "generado correctamente."\n'
            '                        )\n\n'
            '                        st.session_state["notificaciones"] = (\n'
            '                            crear_notificacion(\n'
            '                                st.session_state.get(\n'
            '                                    "notificaciones", []\n'
            '                                ),\n'
            '                                "Ranking generado",\n'
            '                                "Se completó un ranking de "\n'
            '                                "demostración gratuita.",\n'
            '                                "success",\n'
            '                            )\n'
            '                        )'
        ),
        RANKINGS,
    )

    texto = reemplazar_una_vez(
        texto,
        (
            '                st.success(\n'
            '                    "Ranking generado correctamente."\n'
            '                )'
        ),
        (
            '                st.success(\n'
            '                    "Ranking generado correctamente."\n'
            '                )\n\n'
            '                st.session_state["notificaciones"] = (\n'
            '                    crear_notificacion(\n'
            '                        st.session_state.get(\n'
            '                            "notificaciones", []\n'
            '                        ),\n'
            '                        "Ranking generado",\n'
            '                        "Se completó un ranking con Claude.",\n'
            '                        "success",\n'
            '                    )\n'
            '                )'
        ),
        RANKINGS,
    )

    return texto


def main():
    original_main = MAIN.read_text(encoding="utf-8")
    original_rankings = RANKINGS.read_text(encoding="utf-8")

    nuevo_main = actualizar_main(original_main)
    nuevo_rankings = actualizar_rankings(original_rankings)

    # Escribir solo después de validar ambas transformaciones.
    MAIN.write_text(nuevo_main, encoding="utf-8")
    RANKINGS.write_text(nuevo_rankings, encoding="utf-8")

    print("Integración de notificaciones completada.")


if __name__ == "__main__":
    main()
