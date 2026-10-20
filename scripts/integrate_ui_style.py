
"""Integra estilos responsive y accesibles en el dashboard."""

from pathlib import Path


ARCHIVO = Path("dashboard/main.py")


def main():
    original = ARCHIVO.read_text(encoding="utf-8")

    importacion = "import streamlit as st\n"

    if original.count(importacion) != 1:
        raise RuntimeError(
            "No se encontró una única importación de Streamlit."
        )

    actualizado = original.replace(
        importacion,
        (
            "import streamlit as st\n"
            "from dashboard.ui_style import aplicar_estilos\n"
        ),
        1,
    )

    inicio = actualizado.find("st.markdown(\n")

    if inicio == -1:
        raise RuntimeError(
            "No se encontró el bloque de estilos anterior."
        )

    fin = actualizado.find(
        "\n\n# ---------------------------------------------------------",
        inicio,
    )

    if fin == -1:
        raise RuntimeError(
            "No se encontró el final del bloque de estilos."
        )

    actualizado = (
        actualizado[:inicio]
        + "aplicar_estilos()"
        + actualizado[fin:]
    )

    ARCHIVO.write_text(
        actualizado,
        encoding="utf-8",
    )

    print(
        "Estilos responsive y accesibles integrados."
    )


if __name__ == "__main__":
    main()
