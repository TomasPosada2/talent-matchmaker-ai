
"""Pruebas de creación de vacantes desde el dashboard - Issue #54."""

import httpx

from dashboard import api_client


def test_enviar_vacante_correctamente(monkeypatch):
    """Verifica que la vacante se envía con autenticación."""

    def post_simulado(url, json, headers, timeout):
        assert url.endswith("/job-templates")
        assert headers["Authorization"] == "Bearer token-prueba"
        assert json["nombre"] == "Analista de datos"
        assert json["vacante"]["cargo"] == "Analista de datos"
        assert json["vacante"]["requisitos"] == [
            "Python",
            "SQL",
        ]

        return httpx.Response(
            201,
            json={
                "id": 1,
                "nombre": "Analista de datos",
                "vacante": json["vacante"],
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        api_client.httpx,
        "post",
        post_simulado,
    )

    datos, error = api_client.enviar_api(
        "/job-templates",
        {
            "nombre": "Analista de datos",
            "vacante": {
                "cargo": "Analista de datos",
                "requisitos": ["Python", "SQL"],
            },
        },
        "token-prueba",
    )

    assert error is None
    assert datos["id"] == 1
    assert datos["vacante"]["requisitos"] == [
        "Python",
        "SQL",
    ]


def test_error_http_al_guardar(monkeypatch):
    """Verifica el manejo de errores del servidor."""

    def post_simulado(url, json, headers, timeout):
        return httpx.Response(
            500,
            json={"detail": "Error interno"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        api_client.httpx,
        "post",
        post_simulado,
    )

    datos, error = api_client.enviar_api(
        "/job-templates",
        {"nombre": "Prueba", "vacante": {}},
        "token-prueba",
    )

    assert datos is None
    assert "500" in error


def test_error_de_conexion_al_guardar(monkeypatch):
    """Verifica el manejo de fallos de conexión."""

    def post_simulado(url, json, headers, timeout):
        raise httpx.ConnectError("Servidor no disponible")

    monkeypatch.setattr(
        api_client.httpx,
        "post",
        post_simulado,
    )

    datos, error = api_client.enviar_api(
        "/job-templates",
        {"nombre": "Prueba", "vacante": {}},
        "token-prueba",
    )

    assert datos is None
    assert "conectar" in error.lower()
