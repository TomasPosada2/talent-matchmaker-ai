import json
import logging
import time
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src import api, observability


@pytest.fixture(autouse=True)
def limpiar_alertas():
    observability.reiniciar_alertas()
    yield
    observability.reiniciar_alertas()


@pytest.fixture
def webhook(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example/alertas")
    enviado = MagicMock()
    enviado.return_value.raise_for_status.return_value = None
    monkeypatch.setattr(observability.httpx, "post", enviado)
    return enviado


def test_alerta_sin_webhook_no_se_envia(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)

    assert observability.alertar("prueba", "mensaje") is False


def test_alerta_se_envia_y_no_se_repite(webhook):
    assert observability.alertar("error_api", "fallo", clave="k") is True
    assert observability.alertar("error_api", "fallo otra vez", clave="k") is False

    assert webhook.call_count == 1
    cuerpo = webhook.call_args.kwargs["json"]
    assert "error_api" in cuerpo["text"]
    assert "fallo" in cuerpo["text"]


def test_alerta_fallida_no_lanza_excepcion(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example/alertas")

    def caido(*args, **kwargs):
        raise observability.httpx.ConnectError("sin red")

    monkeypatch.setattr(observability.httpx, "post", caido)

    assert observability.alertar("prueba", "mensaje") is False


def test_formato_json():
    registro = logging.LogRecord("api", logging.INFO, __file__, 1, "hola %s", ("mundo",), None)

    evento = json.loads(observability.FormatoJson().format(registro))

    assert evento["message"] == "hola mundo"
    assert evento["level"] == "INFO"
    assert evento["logger"] == "api"


def test_heartbeat(tmp_path):
    ruta = tmp_path / "heartbeat.json"

    assert not observability.heartbeat_vigente(ruta, 60)

    observability.escribir_heartbeat(ruta, "ok")

    assert observability.heartbeat_vigente(ruta, 60)

    datos = json.loads(ruta.read_text(encoding="utf-8"))
    datos["timestamp"] = time.time() - 600
    ruta.write_text(json.dumps(datos), encoding="utf-8")

    assert not observability.heartbeat_vigente(ruta, 60)


def test_metrics_expone_peticiones():
    client = TestClient(api.app)
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "tm_http_requests_total" in response.text
    assert 'route="/health"' in response.text


def test_metrics_con_token(monkeypatch):
    monkeypatch.setenv("METRICS_TOKEN", "token-metricas")
    client = TestClient(api.app)

    assert client.get("/metrics").status_code == 401
    assert client.get(
        "/metrics", headers={"Authorization": "Bearer token-metricas"}
    ).status_code == 200


def test_health_ready_sin_base_de_datos(monkeypatch):
    def sin_bd():
        raise RuntimeError("DATABASE_URL no configurada")

    monkeypatch.setattr(api.profile_repository, "obtener_conexion", sin_bd)

    response = TestClient(api.app).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"


def test_health_ready_con_base_de_datos(monkeypatch):
    conexion = MagicMock()
    conexion.__enter__.return_value = conexion
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    conexion.cursor.return_value = cursor
    monkeypatch.setattr(api.profile_repository, "obtener_conexion", lambda: conexion)

    response = TestClient(api.app).get("/health/ready")

    assert response.status_code == 200
    cursor.execute.assert_called_once_with("SELECT 1")


def test_error_no_controlado_responde_500_y_alerta(monkeypatch, webhook):
    def explota():
        raise RuntimeError("fallo inesperado")

    monkeypatch.setattr(api.profile_repository, "listar_perfiles", explota)
    api.app.dependency_overrides[api.auth.obtener_recruiter_actual] = lambda: {
        "id": 1,
        "email": "r@example.com",
        "role": "recruiter",
    }
    try:
        response = TestClient(api.app).get("/profiles")
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 500
    assert webhook.call_count == 1
    assert "/profiles" in webhook.call_args.kwargs["json"]["text"]


def test_pipeline_alerta_si_fallan_demasiados(monkeypatch, tmp_path, webhook):
    from src import pipeline

    monkeypatch.setattr(pipeline.profile_repository, "crear_tablas", lambda: None)

    correos = [
        pipeline.email_detector.CorreoDetectado(
            email_id=f"email_{i}",
            ruta_carpeta=tmp_path,
            remitente=None,
            asunto=None,
            adjunto_valido=tmp_path / "no_existe.pdf",
            estado="candidato_a_procesar",
        )
        for i in range(3)
    ]

    reporte = pipeline.procesar_lote(None, tmp_path, correos=correos)

    assert reporte["fallidos"] == 3
    assert webhook.call_count == 1
    assert "pipeline_fallos" in webhook.call_args.kwargs["json"]["text"]
