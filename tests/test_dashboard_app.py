"""
Pruebas del dashboard completo con streamlit.testing (sin navegador).

Sprint 7 - #59 (accesibilidad) y administración de cuentas (#61/#63).
"""

from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from dashboard import api_client

PERFIL = {
    "email_id": "email_001",
    "archivo_origen": "cv.docx",
    "nombre": {"valor": "Ana Pérez", "evidencia": "Ana Pérez"},
    "contacto": {
        "email": {"valor": "ana@example.com", "evidencia": "ana@example.com"},
        "telefono": {"valor": None, "evidencia": None},
    },
    "educacion": {"valor": "EAFIT", "evidencia": "EAFIT"},
    "experiencia": {"valor": "Analista", "evidencia": "Analista"},
    "habilidades": {"valor": "Python, SQL", "evidencia": "Python, SQL"},
}


def api_falsa(ruta, token=None):
    respuestas = {
        "/health": {"status": "ok"},
        "/profiles": {"total": 1, "profiles": [PERFIL]},
        "/job-templates": {"total": 0, "templates": []},
        "/admin/users": {
            "total": 1,
            "users": [{"email": "admin@demo.local", "role": "admin", "created_at": "2026-10-20"}],
        },
    }
    return respuestas.get(ruta), None


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(api_client, "consultar_api", api_falsa)
    main = Path(__file__).resolve().parents[1] / "dashboard" / "main.py"
    return AppTest.from_file(str(main), default_timeout=30)


def iniciar_como(app, rol):
    app.session_state["access_token"] = "token"
    app.session_state["recruiter_email"] = f"{rol}@demo.local"
    app.session_state["recruiter_role"] = rol
    return app.run()


def test_sin_sesion_muestra_login(app):
    app.run()

    assert not app.exception
    assert app.header[0].value == "Iniciar sesión"
    assert [campo.label for campo in app.text_input] == ["Correo electrónico", "Contraseña"]


def test_recruiter_no_ve_administracion(app):
    iniciar_como(app, "recruiter")

    assert not app.exception
    assert "Administración" not in app.sidebar.radio[0].options


def test_admin_ve_administracion(app):
    iniciar_como(app, "admin")
    app.sidebar.radio[0].set_value("Administración").run()

    assert not app.exception
    assert app.title[0].value == "Administración"
    assert "Crear cuenta" in [h.value for h in app.header]


def test_tablas_accesibles_usan_tabla_html(app):
    iniciar_como(app, "recruiter")
    app.sidebar.radio[0].set_value("Candidatos").run()

    assert len(app.dataframe) == 1
    assert len(app.table) == 0

    app.sidebar.toggle[0].set_value(True).run()

    assert not app.exception
    assert len(app.table) == 1
    assert len(app.dataframe) == 0


def test_mensaje_sesion_expirada(monkeypatch):
    def respuesta_401(*args, **kwargs):
        request = httpx.Request("GET", "http://api/profiles")
        raise httpx.HTTPStatusError(
            "401", request=request, response=httpx.Response(401, request=request)
        )

    monkeypatch.setattr(api_client.httpx, "get", respuesta_401)

    datos, error = api_client.consultar_api("/profiles", "token")

    assert datos is None
    assert "sesión expiró" in error
    assert "401" in error


def test_login_bloqueado_muestra_espera(monkeypatch):
    def respuesta_429(*args, **kwargs):
        request = httpx.Request("POST", "http://api/auth/login")
        raise httpx.HTTPStatusError(
            "429", request=request, response=httpx.Response(429, request=request)
        )

    monkeypatch.setattr(api_client.httpx, "post", respuesta_429)

    _, error = api_client.iniciar_sesion("a@b.com", "x")

    assert "15 minutos" in error


def test_eliminar_api(monkeypatch):
    request = httpx.Request("DELETE", "http://api/profiles/email_001")
    monkeypatch.setattr(
        api_client.httpx,
        "delete",
        lambda *a, **k: httpx.Response(200, json={"archivos_eliminados": 1}, request=request),
    )

    datos, error = api_client.eliminar_api("/profiles/email_001", "token")

    assert error is None
    assert datos == {"archivos_eliminados": 1}
