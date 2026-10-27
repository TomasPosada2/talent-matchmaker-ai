"""
Sistema visual del dashboard.

Sprint 6 - #60 (responsive) y Sprint 7 - #59 (accesibilidad).
Sprint 8 - #89: rediseño. Los colores, la tipografía (Inter) y los radios
vienen del tema en .streamlit/config.toml; aquí van los estilos que el tema
no cubre y los componentes reutilizables (encabezado, chips, tarjetas).

Todo texto que venga de un CV o del usuario se escapa con html.escape antes
de entrar a un bloque HTML (#61).
"""

import html

import streamlit as st

# Paleta (debe coincidir con .streamlit/config.toml).
PRIMARIO = "#4F46E5"
TEXTO = "#0F172A"
TEXTO_SUAVE = "#475569"
BORDE = "#E2E8F0"

ESTILOS = """
<style>
/* ---------- Estructura ---------- */
.block-container {
    max-width: 1280px;
    padding: 2rem 2.5rem 6rem;
}
[data-testid="stHeader"] {
    background: transparent;
}
/* El iframe que fija el idioma no debe ocupar espacio. */
.st-key-fijar_idioma {
    display: none;
}

/* ---------- Encabezado de página ---------- */
.tm-encabezado {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin: 0 0 1.5rem;
}
.tm-encabezado-icono {
    flex: none;
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: grid;
    place-items: center;
    font-size: 1.5rem;
    background: #EEF2FF;
}
.tm-encabezado h1 {
    font-size: 1.75rem;
    line-height: 1.2;
    margin: 0;
    padding: 0;
}
.tm-encabezado p {
    margin: 0.25rem 0 0;
    color: #475569;
    font-size: 0.975rem;
}

/* ---------- Tarjetas ---------- */
.tm-tarjeta {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    height: 100%;
}
.tm-tarjeta h3 {
    font-size: 1.05rem;
    margin: 0.5rem 0 0.35rem;
    padding: 0;
}
.tm-tarjeta p {
    margin: 0;
    color: #475569;
    font-size: 0.925rem;
    line-height: 1.5;
}
.tm-tarjeta-icono {
    font-size: 1.4rem;
}
.tm-acceso h3 {
    font-size: 1.05rem;
    margin: 0.4rem 0 0.25rem;
    padding: 0;
}
.tm-acceso p {
    margin: 0 0 0.25rem;
    color: #475569;
    font-size: 0.925rem;
    line-height: 1.5;
    min-height: 2.8em;
}

/* Contenedores con borde de Streamlit = tarjetas blancas. */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border-radius: 16px;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    background: transparent;
}

/* ---------- Indicadores ---------- */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 1rem 1.25rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
[data-testid="stMetricLabel"] p {
    font-size: 0.8rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748B;
}
[data-testid="stMetricValue"] {
    font-size: 1.9rem !important;
    font-weight: 700;
    color: #0F172A;
}

/* ---------- Chips de estado ---------- */
.tm-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0 0 1.25rem;
}
.tm-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.3rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 500;
    border: 1px solid transparent;
    line-height: 1.4;
}
.tm-chip-ok      { background: #ECFDF5; color: #065F46; border-color: #A7F3D0; }
.tm-chip-aviso   { background: #FFFBEB; color: #92400E; border-color: #FDE68A; }
.tm-chip-error   { background: #FEF2F2; color: #991B1B; border-color: #FECACA; }
.tm-chip-neutro  { background: #F1F5F9; color: #334155; border-color: #E2E8F0; }
.tm-chip-primario{ background: #EEF2FF; color: #3730A3; border-color: #C7D2FE; }

/* ---------- Ranking ---------- */
.tm-candidato {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.tm-posicion {
    flex: none;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    font-weight: 700;
    background: #EEF2FF;
    color: #3730A3;
}
.tm-candidato-info {
    flex: 1;
    min-width: 0;
}
.tm-candidato-nombre {
    font-weight: 600;
    font-size: 1.02rem;
    color: #0F172A;
}
.tm-candidato-id {
    font-size: 0.8rem;
    color: #64748B;
}
.tm-barra {
    height: 8px;
    border-radius: 999px;
    background: #E2E8F0;
    overflow: hidden;
    margin-top: 0.45rem;
}
.tm-barra > span {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #6366F1, #4F46E5);
}
.tm-puntaje {
    flex: none;
    text-align: right;
    font-size: 1.5rem;
    font-weight: 700;
    color: #0F172A;
    min-width: 72px;
}
.tm-puntaje small {
    display: block;
    font-size: 0.75rem;
    font-weight: 500;
    color: #64748B;
}
.tm-requisito {
    border-top: 1px solid #F1F5F9;
    padding: 0.7rem 0;
}
.tm-requisito:first-child {
    border-top: none;
}
.tm-requisito-titulo {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-weight: 600;
    color: #0F172A;
}
.tm-cita {
    margin: 0.4rem 0 0;
    padding: 0.5rem 0.75rem;
    border-left: 3px solid #A5B4FC;
    background: #F8FAFC;
    border-radius: 0 8px 8px 0;
    color: #334155;
    font-size: 0.9rem;
}

/* ---------- Barra lateral ---------- */
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.25rem;
}
.tm-marca {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.25rem 0 1rem;
}
.tm-marca-logo {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    font-weight: 800;
    color: #FFFFFF;
    background: linear-gradient(135deg, #818CF8, #4F46E5);
}
.tm-marca-nombre {
    color: #F8FAFC;
    font-weight: 700;
    font-size: 1.02rem;
    line-height: 1.2;
}
.tm-marca-sub {
    color: #94A3B8;
    font-size: 0.78rem;
}
.tm-usuario {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.7rem 0.75rem;
    border-radius: 12px;
    background: #1E293B;
    margin: 0.25rem 0 1.25rem;
}
.tm-avatar {
    width: 34px;
    height: 34px;
    border-radius: 999px;
    display: grid;
    place-items: center;
    font-weight: 700;
    font-size: 0.85rem;
    color: #1E1B4B;
    background: #C7D2FE;
    flex: none;
}
.tm-usuario-correo {
    color: #F1F5F9;
    font-size: 0.85rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.tm-usuario-rol {
    color: #94A3B8;
    font-size: 0.75rem;
}
.tm-seccion-menu {
    color: #64748B;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin: 0 0 0.35rem 0.25rem;
}

/* Menú: el radio de navegación se ve como una lista de enlaces.
   Estructura de Streamlit 1.66: radiogroup > div > label[stRadioOption]
   > (input oculto, div > [círculo, texto]). */
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 2px;
}
/* Streamlit ajusta el radio a su contenido; el menú usa todo el ancho. */
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has([data-testid="stRadio"]),
[data-testid="stSidebar"] [data-testid="stRadio"],
[data-testid="stSidebar"] [data-testid="stRadioGroup"],
[data-testid="stSidebar"] [role="radiogroup"] > div {
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
    display: flex;
    width: 100%;
    box-sizing: border-box;
    padding: 0.55rem 0.75rem;
    border-radius: 10px;
    margin: 0;
    cursor: pointer;
    transition: background 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
    background: #1E293B;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {
    display: none;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {
    color: #CBD5E1;
    font-size: 0.93rem;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
    background: #312E81;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {
    color: #FFFFFF;
    font-weight: 600;
}
[data-testid="stSidebar"] hr {
    border-color: #1E293B;
    margin: 1rem 0;
}

/* ---------- Login ---------- */
.tm-login-marca {
    text-align: center;
    margin: 3rem 0 1.5rem;
}
.tm-login-marca .tm-marca-logo {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    font-size: 1.4rem;
    margin: 0 auto 1rem;
}
.tm-login-marca h1 {
    font-size: 1.6rem;
    margin: 0;
    padding: 0;
}
.tm-login-marca p {
    color: #475569;
    margin: 0.35rem 0 0;
}

/* ---------- Accesibilidad (#59) ---------- */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
a:focus-visible,
[role="radio"]:focus-visible {
    outline: 3px solid #6366F1 !important;
    outline-offset: 2px;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:focus-visible) {
    outline: 3px solid #A5B4FC;
    outline-offset: 1px;
}
.stMarkdown p,
.stMarkdown li {
    line-height: 1.6;
}
[data-testid="stDataFrame"] {
    max-width: 100%;
    overflow-x: auto;
}

/* ---------- Responsive (#60) ---------- */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 0.9rem 6rem;
    }
    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }
    [data-testid="column"] {
        min-width: min(100%, 260px) !important;
        flex: 1 1 100% !important;
    }
    .tm-encabezado h1 {
        font-size: 1.45rem;
    }
}

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


# Streamlit declara la página como lang="en"; los lectores de pantalla
# leerían el español con pronunciación inglesa (WCAG 3.1.1).
FIJAR_IDIOMA = """
<script>
window.parent.document.documentElement.lang = "es";
</script>
"""


def aplicar_estilos():
    """Aplica estilos visuales al dashboard."""
    st.markdown(
        ESTILOS,
        unsafe_allow_html=True,
    )
    with st.container(key="fijar_idioma"):
        st.iframe(FIJAR_IDIOMA, height=1)


def encabezado(titulo: str, descripcion: str = "", icono: str = "") -> None:
    """Encabezado común de cada página: ícono, título (h1) y descripción."""
    icono_html = (
        f'<div class="tm-encabezado-icono" aria-hidden="true">{icono}</div>'
        if icono
        else ""
    )
    descripcion_html = f"<p>{html.escape(descripcion)}</p>" if descripcion else ""
    st.markdown(
        f'<div class="tm-encabezado">{icono_html}'
        f"<div><h1>{html.escape(titulo)}</h1>{descripcion_html}</div></div>",
        unsafe_allow_html=True,
    )


def chip(texto: str, tipo: str = "neutro", icono: str = "") -> str:
    """HTML de un chip. ``tipo``: ok, aviso, error, neutro o primario."""
    prefijo = f'<span aria-hidden="true">{icono}</span>' if icono else ""
    return f'<span class="tm-chip tm-chip-{tipo}">{prefijo}{html.escape(texto)}</span>'


def fila_de_chips(chips: list[str]) -> None:
    st.markdown(
        f'<div class="tm-chips">{"".join(chips)}</div>',
        unsafe_allow_html=True,
    )


def tarjeta(titulo: str, descripcion: str, icono: str = "") -> str:
    """HTML de una tarjeta informativa simple (contenido propio, no de CVs)."""
    icono_html = (
        f'<div class="tm-tarjeta-icono" aria-hidden="true">{icono}</div>' if icono else ""
    )
    return (
        f'<div class="tm-tarjeta">{icono_html}<h3>{html.escape(titulo)}</h3>'
        f"<p>{html.escape(descripcion)}</p></div>"
    )


def acceso_html(titulo: str, descripcion: str, icono: str = "") -> str:
    """Contenido de una tarjeta de acceso rápido (va dentro de un contenedor con borde)."""
    icono_html = (
        f'<div class="tm-tarjeta-icono" aria-hidden="true">{icono}</div>' if icono else ""
    )
    return (
        f'<div class="tm-acceso">{icono_html}<h3>{html.escape(titulo)}</h3>'
        f"<p>{html.escape(descripcion)}</p></div>"
    )


def mostrar_tabla(filas: list[dict]) -> None:
    """
    Muestra una tabla de datos.

    st.dataframe se dibuja en un canvas que los lectores de pantalla no
    pueden recorrer. Con la opción "Tablas accesibles" del menú lateral se
    usa st.table, que genera una tabla HTML semántica (WCAG 1.3.1).
    """
    if st.session_state.get("tablas_accesibles"):
        st.table(filas)
    else:
        st.dataframe(
            filas,
            width="stretch",
            hide_index=True,
        )
