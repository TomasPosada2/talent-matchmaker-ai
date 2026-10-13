
"""Pruebas del cliente de autenticación del dashboard."""

import httpx

from dashboard import api_client


def test_iniciar_sesion_exitoso(monkeypatch):
    class RespuestaFake:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "access_token": "token-de-prueba",
                "token_type": "bearer",
            }

    def post_fake(url, json, timeout):
        assert url.endswith("/auth/login")
        assert json == {
            "email": "recruiter@example.com",
            "password": "clave-de-prueba",
        }
        return RespuestaFake()

    monkeypatch.setattr(api_client.httpx, "post", post_fake)

    datos, error = api_client.iniciar_sesion(
        "recruiter@example.com",
        "clave-de-prueba",
    )

    assert datos["access_token"] == "token-de-prueba"
    assert error is None


def test_iniciar_sesion_credenciales_incorrectas(monkeypatch):
    def post_fake(url, json, timeout):
        request = httpx.Request("POST", url)
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError(
            "Unauthorized",
            request=request,
            response=response,
        )

    monkeypatch.setattr(api_client.httpx, "post", post_fake)

    datos, error = api_client.iniciar_sesion(
        "recruiter@example.com",
        "clave-incorrecta",
    )

    assert datos is None
    assert error == "Correo o contraseña incorrectos."


def test_iniciar_sesion_error_servidor(monkeypatch):
    def post_fake(url, json, timeout):
        request = httpx.Request("POST", url)
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError(
            "Internal Server Error",
            request=request,
            response=response,
        )

    monkeypatch.setattr(api_client.httpx, "post", post_fake)

    datos, error = api_client.iniciar_sesion(
        "recruiter@example.com",
        "clave-de-prueba",
    )

    assert datos is None
    assert "500" in error


def test_iniciar_sesion_sin_conexion(monkeypatch):
    def post_fake(url, json, timeout):
        raise httpx.ConnectError("Conexión rechazada")

    monkeypatch.setattr(api_client.httpx, "post", post_fake)

    datos, error = api_client.iniciar_sesion(
        "recruiter@example.com",
        "clave-de-prueba",
    )

    assert datos is None
    assert "No fue posible conectar" in error
