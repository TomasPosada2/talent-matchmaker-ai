
"""Integra el panel de analítica del Issue #58 en Streamlit."""

from pathlib import Path


ARCHIVO = Path("dashboard/main.py")


def reemplazar(texto, anterior, nuevo):
    coincidencias = texto.count(anterior)

    if coincidencias != 1:
        raise RuntimeError(
            f"Se esperaba una coincidencia y se encontraron "
            f"{coincidencias}: {anterior!r}"
        )

    return texto.replace(anterior, nuevo, 1)


def main():
    original = ARCHIVO.read_text(encoding="utf-8")

    actualizado = reemplazar(
        original,
        "from dashboard.rankings_page import mostrar_rankings",
        (
            "from dashboard.rankings_page import mostrar_rankings\n"
            "from dashboard.analytics import mostrar_analitica"
        ),
    )

    actualizado = reemplazar(
        actualizado,
        '            "Rankings",\n            "Vacantes",',
        '            "Rankings",\n            "Vacantes",\n            "Analítica",',
    )

    actualizado = reemplazar(
        actualizado,
        'elif pagina == "Notificaciones":',
        (
            'elif pagina == "Analítica":\n'
            '    mostrar_analitica(\n'
            '        st.session_state["access_token"]\n'
            '    )\n\n'
            'elif pagina == "Notificaciones":'
        ),
    )

    ARCHIVO.write_text(actualizado, encoding="utf-8")
    print("Panel de analítica integrado correctamente.")


if __name__ == "__main__":
    main()
