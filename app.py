"""
Interfaz de prueba (Sprint 1/2) para Talent Matchmaker AI.

Uso:
    streamlit run app.py

Permite correr el pipeline sobre la bandeja simulada y navegar los perfiles
extraídos junto con su evidencia textual, sin tener que leer los JSON a mano.
"""

import json
from pathlib import Path

import streamlit as st

from src.pipeline import procesar_lote

BASE_DIR = Path(__file__).resolve().parent
INBOX_DIR = BASE_DIR / "data" / "inbox_simulado"
CARPETA_TRABAJO = BASE_DIR / "data" / "salida"
REPORTE_PATH = CARPETA_TRABAJO / "reporte_lote.json"

# BUG-01 / BUG-02 conocidos (ver SPRINT_REVIEW.md) — se resaltan en la UI
# para que sean visibles mientras siguen sin corregir en el backlog.
BUG01_AFECTADOS = {"email_004", "email_008", "email_012", "email_016", "email_020"}


def bug02_sospechoso(telefono: str | None) -> bool:
    if not telefono:
        return False
    return bool(__import__("re").fullmatch(r"[\(\)\d\- ]*\d{4}-\d{4}[\(\)\d\- ]*", telefono))


st.set_page_config(page_title="Talent Matchmaker AI — Prueba", layout="wide")
st.title("Talent Matchmaker AI — Panel de prueba")
st.caption("Sprint 1: ingesta y extracción trazable de CVs. Sin ranking todavía (Sprint 3).")

col_run, col_info = st.columns([1, 3])
with col_run:
    if st.button("▶ Correr pipeline sobre la bandeja simulada", type="primary"):
        with st.spinner("Procesando bandeja..."):
            reporte = procesar_lote(INBOX_DIR, CARPETA_TRABAJO)
        st.success("Pipeline ejecutado.")
        st.session_state["reporte"] = reporte

if "reporte" not in st.session_state:
    if REPORTE_PATH.exists():
        st.session_state["reporte"] = json.loads(REPORTE_PATH.read_text(encoding="utf-8"))
    else:
        st.info("Todavía no hay resultados. Corre el pipeline para generarlos.")
        st.stop()

reporte = st.session_state["reporte"]

st.subheader("Métricas del lote")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total correos", reporte["total_correos_en_bandeja"])
m2.metric("Candidatos a procesar", reporte["candidatos_a_procesar"])
m3.metric("Procesados con éxito", reporte["procesados_exitosamente"])
m4.metric("Fallidos", reporte["fallidos"])
m5.metric("Tasa de éxito", f"{reporte['tasa_exito'] * 100:.1f}%")

if reporte["detalle_fallidos"]:
    with st.expander(f"Casos fallidos ({len(reporte['detalle_fallidos'])})"):
        for f in reporte["detalle_fallidos"]:
            st.write(f"**{f['email_id']}** — {f['motivo']}")

st.divider()
st.subheader(f"Perfiles extraídos ({len(reporte['perfiles'])})")

busqueda = st.text_input("Buscar por nombre, habilidad o experiencia")
solo_con_bugs = st.checkbox("Mostrar solo perfiles con defectos conocidos (BUG-01 / BUG-02)")

perfiles = reporte["perfiles"]

if busqueda:
    q = busqueda.lower()
    def coincide(p):
        campos = [
            p["nombre"]["valor"] or "",
            p["habilidades"]["valor"] or "",
            p["experiencia"]["valor"] or "",
            p["educacion"]["valor"] or "",
        ]
        return any(q in str(c).lower() for c in campos)
    perfiles = [p for p in perfiles if coincide(p)]

if solo_con_bugs:
    perfiles = [
        p for p in perfiles
        if p["email_id"] in BUG01_AFECTADOS or bug02_sospechoso(p["contacto"]["telefono"]["valor"])
    ]

for p in perfiles:
    flags = []
    if p["email_id"] in BUG01_AFECTADOS:
        flags.append("⚠️ BUG-01 (tabla mal ordenada)")
    if bug02_sospechoso(p["contacto"]["telefono"]["valor"]):
        flags.append("⚠️ BUG-02 (posible rango de años como teléfono)")

    titulo = f"{p['nombre']['valor'] or '(sin nombre)'} — {p['email_id']}"
    if flags:
        titulo += "  " + " ".join(flags)

    with st.expander(titulo):
        st.caption(f"Archivo origen: {p['archivo_origen']}")

        campos = [
            ("Nombre", p["nombre"]),
            ("Email", p["contacto"]["email"]),
            ("Teléfono", p["contacto"]["telefono"]),
            ("Educación", p["educacion"]),
            ("Experiencia", p["experiencia"]),
            ("Habilidades", p["habilidades"]),
        ]
        for etiqueta, campo in campos:
            valor = campo["valor"]
            evidencia = campo["evidencia"]
            c1, c2 = st.columns([1, 2])
            with c1:
                if valor is None:
                    st.markdown(f"**{etiqueta}:** `null`")
                else:
                    st.markdown(f"**{etiqueta}:** {valor}")
            with c2:
                if evidencia:
                    st.code(evidencia, language=None)

if not perfiles:
    st.warning("Ningún perfil coincide con el filtro.")
