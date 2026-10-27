"""Sprint 8 - Issue #86: conexión con una bandeja real de Gmail."""

import json
import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from dashboard.gmail_status import describir_estado_gmail
from src import api, email_polling, gmail_inbox, observability


def servicio_con_paginas(paginas):
    servicio = MagicMock()
    servicio.users().messages().list.return_value.execute.side_effect = paginas
    servicio.users().messages().get().execute.return_value = {
        "payload": {"headers": [], "parts": []}
    }
    return servicio


def test_consulta_por_defecto_y_configurable(monkeypatch):
    monkeypatch.delenv("GMAIL_QUERY", raising=False)
    assert gmail_inbox.obtener_consulta_gmail() == gmail_inbox.CONSULTA_POR_DEFECTO
    assert "has:attachment" in gmail_inbox.CONSULTA_POR_DEFECTO

    monkeypatch.setenv("GMAIL_QUERY", "label:postulaciones")
    assert gmail_inbox.obtener_consulta_gmail() == "label:postulaciones"


def test_lista_con_consulta_y_paginacion():
    servicio = servicio_con_paginas([
        {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"},
        {"messages": [{"id": "c"}]},
    ])

    ids = gmail_inbox._listar_ids_mensajes(servicio, "has:attachment", 10)

    assert ids == ["a", "b", "c"]
    llamadas = servicio.users().messages().list.call_args_list
    assert llamadas[-2].kwargs["q"] == "has:attachment"
    assert llamadas[-1].kwargs["pageToken"] == "p2"


def test_paginacion_respeta_el_maximo():
    servicio = servicio_con_paginas([
        {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"},
        {"messages": [{"id": "c"}, {"id": "d"}], "nextPageToken": "p3"},
    ])

    assert gmail_inbox._listar_ids_mensajes(servicio, "", 3) == ["a", "b", "c"]


def test_obtener_correos_usa_la_consulta(tmp_path, monkeypatch):
    monkeypatch.setenv("GMAIL_QUERY", "label:cv")
    servicio = servicio_con_paginas([{"messages": [{"id": "m1"}]}])

    with patch("src.gmail_inbox._construir_servicio", return_value=servicio):
        correos = gmail_inbox.obtener_correos_gmail(tmp_path)

    assert [c.email_id for c in correos] == ["m1"]
    assert servicio.users().messages().list.call_args.kwargs["q"] == "label:cv"


def test_obtener_cuenta_gmail():
    servicio = MagicMock()
    servicio.users().getProfile().execute.return_value = {"emailAddress": "rrhh@empresa.com"}

    with patch("src.gmail_inbox._construir_servicio", return_value=servicio):
        assert gmail_inbox.obtener_cuenta_gmail() == "rrhh@empresa.com"


def test_estado_sin_heartbeat(tmp_path):
    estado = email_polling.leer_estado_listener(tmp_path / "no_existe.json", 300)

    assert estado["conectado"] is False
    assert estado["estado"] == "sin_datos"


def test_estado_conectado(tmp_path):
    ruta = tmp_path / "heartbeat.json"
    observability.escribir_heartbeat(
        ruta,
        "ok",
        extra={"cuenta": "rrhh@empresa.com", "nuevos_ultimo_ciclo": 2, "procesados_total": 9},
    )

    estado = email_polling.leer_estado_listener(ruta, 300)

    assert estado["conectado"] is True
    assert estado["cuenta"] == "rrhh@empresa.com"
    assert estado["nuevos_ultimo_ciclo"] == 2
    assert estado["procesados_total"] == 9


def test_estado_inactivo_si_el_ciclo_es_viejo(tmp_path):
    ruta = tmp_path / "heartbeat.json"
    ruta.write_text(
        json.dumps({"timestamp": time.time() - 3600, "estado": "ok"}),
        encoding="utf-8",
    )

    estado = email_polling.leer_estado_listener(ruta, 300)

    assert estado["conectado"] is False
    assert estado["estado"] == "inactivo"


def test_estado_con_error(tmp_path):
    ruta = tmp_path / "heartbeat.json"
    observability.escribir_heartbeat(ruta, "error", "invalid_grant: token revocado")

    estado = email_polling.leer_estado_listener(ruta, 300)

    assert estado["conectado"] is False
    assert estado["estado"] == "error"
    assert "invalid_grant" in estado["detalle"]


def test_listener_registra_cuenta_y_nuevos(tmp_path):
    heartbeat = tmp_path / "heartbeat.json"
    estado = tmp_path / "estado.json"
    email_polling.guardar_ids_procesados(estado, {"x", "y"})

    with patch(
        "src.email_polling.obtener_cuenta_gmail", return_value="rrhh@empresa.com"
    ), patch(
        "src.email_polling.ejecutar_polling_una_vez",
        return_value={"total_correos_en_bandeja": 2},
    ), patch("src.email_polling.time.sleep", side_effect=KeyboardInterrupt):
        email_polling.ejecutar_listener(
            tmp_path, tmp_path, estado, ruta_heartbeat=heartbeat
        )

    datos = json.loads(heartbeat.read_text(encoding="utf-8"))
    assert datos["estado"] == "ok"
    assert datos["cuenta"] == "rrhh@empresa.com"
    assert datos["nuevos_ultimo_ciclo"] == 2
    assert datos["procesados_total"] == 2


def test_listener_registra_error_de_autorizacion(tmp_path, monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    heartbeat = tmp_path / "heartbeat.json"

    with patch(
        "src.email_polling.obtener_cuenta_gmail",
        side_effect=FileNotFoundError("No se encontró credentials.json."),
    ), patch("src.email_polling.time.sleep", side_effect=KeyboardInterrupt):
        email_polling.ejecutar_listener(
            tmp_path, tmp_path, tmp_path / "estado.json", ruta_heartbeat=heartbeat
        )

    datos = json.loads(heartbeat.read_text(encoding="utf-8"))
    assert datos["estado"] == "error"
    assert "credentials.json" in datos["detalle"]


def test_endpoint_estado_gmail(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    observability.escribir_heartbeat(
        tmp_path / "listener_heartbeat.json", "ok", extra={"cuenta": "rrhh@empresa.com"}
    )
    api.app.dependency_overrides[api.auth.obtener_recruiter_actual] = lambda: {
        "id": 1, "email": "r@example.com", "role": "recruiter"
    }
    try:
        response = TestClient(api.app).get("/gmail/status")
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["conectado"] is True
    assert response.json()["cuenta"] == "rrhh@empresa.com"


def test_endpoint_estado_gmail_requiere_login():
    api.app.dependency_overrides.clear()
    assert TestClient(api.app).get("/gmail/status").status_code in (401, 403)


def test_mensajes_del_dashboard():
    nivel, mensaje = describir_estado_gmail(
        {"conectado": True, "cuenta": "rrhh@empresa.com", "segundos_desde_ultimo_ciclo": 120,
         "nuevos_ultimo_ciclo": 1, "procesados_total": 8}
    )
    assert nivel == "ok"
    assert "rrhh@empresa.com" in mensaje
    assert "hace 2 min" in mensaje

    assert describir_estado_gmail({"conectado": False, "estado": "sin_datos"})[0] == "aviso"
    assert describir_estado_gmail({"conectado": False, "estado": "error", "detalle": "x"})[0] == "error"
    assert describir_estado_gmail(None)[0] == "aviso"
