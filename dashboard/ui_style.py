
"""Estilos responsive y accesibilidad - Issues #60 y #59."""

import streamlit as st


ESTILOS = """
<style>
/* Diseño general */
.block-container {
    max-width: 1400px;
    padding: 1.5rem 2rem 3rem;
}

/* Indicadores */
[data-testid="stMetric"] {
    border: 1px solid #64748b;
    border-radius: 12px;
    padding: 1rem;
}

/* Navegación */
[data-testid="stSidebar"] {
    border-right: 1px solid #94a3b8;
}

/* Estados de enfoque visibles para teclado */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
a:focus-visible,
[role="radio"]:focus-visible {
    outline: 3px solid #2563eb !important;
    outline-offset: 3px;
}

/* Mejor legibilidad */
.stMarkdown p,
.stMarkdown li {
    line-height: 1.6;
}

/* Tablas con desplazamiento horizontal */
[data-testid="stDataFrame"] {
    max-width: 100%;
    overflow-x: auto;
}

/* Responsive */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 0.75rem 2rem;
    }

    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="column"] {
        min-width: min(100%, 260px) !important;
        flex: 1 1 100% !important;
    }

    [data-testid="stMetric"] {
        padding: 0.75rem;
    }

    h1 {
        font-size: 1.8rem !important;
    }

    h2 {
        font-size: 1.4rem !important;
    }
}

/* Preferencias de movimiento reducido */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
</style>
"""


def aplicar_estilos():
    """Aplica estilos visuales al dashboard."""
    st.markdown(
        ESTILOS,
        unsafe_allow_html=True,
    )
