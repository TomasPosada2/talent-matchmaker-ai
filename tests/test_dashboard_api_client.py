
import httpx

from dashboard import api_client


def test_consultar_api_exitosamente(monkeypatch):
    class RespuestaFake:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "ok"}

    def get_fake(url, headers, timeout):
        assert url.endswith("/health")
        assert headers == {}
        return RespuestaFake()

    monkeypatch.setattr(
        api_client.httpx,
        "get",
        get_fake,
    )

    datos, error = api_client.consultar_api("/health")

    assert datos == {"status": "ok"}
    assert error is None


def test_consultar_api_con_token(monkeypatch):
    class RespuestaFake:
        def raise_for_status(self):
            pass

        def json(self):
            return {"total": 3}

    def get_fake(url, headers, timeout):
        assert url.endswith("/profiles")
        assert headers["Authorization"] == "Bearer token-prueba"
        return RespuestaFake()

    monkeypatch.setattr(
        api_client.httpx,
        "get",
        get_fake,
    )

    datos, error = api_client.consultar_api(
        "/profiles",
        "token-prueba",
    )

    assert datos == {"total": 3}
    assert error is None


def test_consultar_api_error_http(monkeypatch):
    def get_fake(url, headers, timeout):
        request = httpx.Request("GET", url)
        response = httpx.Response(
            401,
            request=request,
        )
        raise httpx.HTTPStatusError(
            "Unauthorized",
            request=request,
            response=response,
        )

    monkeypatch.setattr(
        api_client.httpx,
        "get",
        get_fake,
    )

    datos, error = api_client.consultar_api("/profiles")

    assert datos is None
    assert "401" in error


def test_consultar_api_sin_conexion(monkeypatch):
    def get_fake(url, headers, timeout):
        raise httpx.ConnectError(
            "No se pudo conectar."
        )

    monkeypatch.setattr(
        api_client.httpx,
        "get",
        get_fake,
    )

    datos, error = api_client.consultar_api("/health")

    assert datos is None
    assert "No fue posible conectar" in error


def test_consultar_api_respuesta_invalida(monkeypatch):
    class RespuestaFake:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("JSON inválido")

    monkeypatch.setattr(
        api_client.httpx,
        "get",
        lambda url, headers, timeout: RespuestaFake(),
    )

    datos, error = api_client.consultar_api("/health")

    assert datos is None
    assert error is not None


# Sprint 8 - #75: el ranking con IA tarda más de un minuto.


def test_enviar_api_usa_el_timeout_indicado(monkeypatch):
    import httpx

    from dashboard import api_client

    recibido = {}

    def post(url, **kwargs):
        recibido["timeout"] = kwargs["timeout"]
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("POST", url))

    monkeypatch.setattr(api_client.httpx, "post", post)

    datos, error = api_client.enviar_api("/rankings", {}, "token", timeout=300)

    assert error is None
    assert recibido["timeout"] == 300


def test_enviar_api_explica_el_timeout(monkeypatch):
    import httpx

    from dashboard import api_client

    def post(url, **kwargs):
        raise httpx.ReadTimeout("tardó", request=httpx.Request("POST", url))

    monkeypatch.setattr(api_client.httpx, "post", post)

    datos, error = api_client.enviar_api("/rankings", {}, "token")

    assert datos is None
    assert "tardó más de lo esperado" in error
