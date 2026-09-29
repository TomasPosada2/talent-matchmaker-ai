import base64
from unittest.mock import MagicMock, patch

from src.gmail_inbox import (
    _obtener_header,
    _obtener_partes,
    _sanitizar_nombre,
    obtener_correos_gmail,
)


def test_obtener_header():
    headers = [
        {"name": "From", "value": "candidato@example.com"},
        {"name": "Subject", "value": "CV candidato"},
    ]

    assert _obtener_header(headers, "from") == "candidato@example.com"
    assert _obtener_header(headers, "SUBJECT") == "CV candidato"
    assert _obtener_header(headers, "Date") is None


def test_obtener_partes_recursivas():
    payload = {
        "parts": [
            {
                "filename": "",
                "parts": [
                    {
                        "filename": "cv.pdf",
                        "body": {"attachmentId": "adj-1"},
                    }
                ],
            }
        ]
    }

    partes = _obtener_partes(payload)

    assert len(partes) == 2
    assert partes[1]["filename"] == "cv.pdf"


def test_sanitizar_nombre():
    assert _sanitizar_nombre("../../cv.pdf") == "cv.pdf"


def test_gmail_correo_sin_adjunto(tmp_path):
    servicio = MagicMock()

    servicio.users().messages().list().execute.return_value = {
        "messages": [{"id": "gmail-1"}]
    }

    servicio.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "From", "value": "persona@example.com"},
                {"name": "Subject", "value": "Hola"},
            ],
            "parts": [],
        }
    }

    with patch(
        "src.gmail_inbox.obtener_credenciales_gmail"
    ), patch(
        "src.gmail_inbox.build",
        return_value=servicio,
    ):
        resultados = obtener_correos_gmail(tmp_path)

    assert len(resultados) == 1
    assert resultados[0].email_id == "gmail-1"
    assert resultados[0].estado == "ignorado_sin_adjunto"
    assert resultados[0].adjunto_valido is None


def test_gmail_descarga_cv_pdf(tmp_path):
    servicio = MagicMock()

    servicio.users().messages().list().execute.return_value = {
        "messages": [{"id": "gmail-2"}]
    }

    servicio.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "From", "value": "candidato@example.com"},
                {"name": "Subject", "value": "Mi CV"},
            ],
            "parts": [
                {
                    "filename": "curriculum.pdf",
                    "body": {"attachmentId": "adj-123"},
                }
            ],
        }
    }

    contenido = b"contenido pdf de prueba"

    servicio.users().messages().attachments().get().execute.return_value = {
        "data": base64.urlsafe_b64encode(contenido).decode("utf-8")
    }

    with patch(
        "src.gmail_inbox.obtener_credenciales_gmail"
    ), patch(
        "src.gmail_inbox.build",
        return_value=servicio,
    ):
        resultados = obtener_correos_gmail(tmp_path)

    assert len(resultados) == 1

    correo = resultados[0]

    assert correo.email_id == "gmail-2"
    assert correo.estado == "candidato_a_procesar"
    assert correo.remitente == "candidato@example.com"
    assert correo.asunto == "Mi CV"
    assert correo.adjunto_valido is not None
    assert correo.adjunto_valido.name == "curriculum.pdf"
    assert correo.adjunto_valido.read_bytes() == contenido


def test_gmail_descarta_formato_no_soportado(tmp_path):
    servicio = MagicMock()

    servicio.users().messages().list().execute.return_value = {
        "messages": [{"id": "gmail-3"}]
    }

    servicio.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [],
            "parts": [
                {
                    "filename": "foto.jpg",
                    "body": {"attachmentId": "adj-jpg"},
                }
            ],
        }
    }

    with patch(
        "src.gmail_inbox.obtener_credenciales_gmail"
    ), patch(
        "src.gmail_inbox.build",
        return_value=servicio,
    ):
        resultados = obtener_correos_gmail(tmp_path)

    assert len(resultados) == 1
    assert (
        resultados[0].estado
        == "descartado_formato_no_soportado"
    )
    assert resultados[0].adjunto_valido is None
    assert ".jpg" in resultados[0].motivo