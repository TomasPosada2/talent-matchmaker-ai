import base64
from unittest.mock import MagicMock, patch

import pytest

from src.email_notifier import (
    construir_mensaje_ranking,
    enviar_notificacion_ranking,
)


def test_construir_mensaje_ranking():
    mensaje = construir_mensaje_ranking(
        destinatario="recruiter@example.com",
        total_candidatos=3,
    )

    assert mensaje["To"] == "recruiter@example.com"
    assert mensaje["Subject"] == "Talent Matchmaker - Ranking listo"

    contenido = mensaje.get_content()

    assert "ranking de candidatos" in contenido
    assert "3" in contenido


def test_enviar_notificacion_requiere_destinatario():
    with pytest.raises(
        ValueError,
        match="email del recruiter",
    ):
        enviar_notificacion_ranking(
            destinatario="",
            ranking=[],
        )


@patch("src.email_notifier.build")
@patch("src.email_notifier.obtener_credenciales_gmail")
def test_enviar_notificacion_ranking(
    mock_credenciales,
    mock_build,
):
    servicio = MagicMock()
    mock_build.return_value = servicio

    servicio.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "mensaje-123"
    }

    ranking = [
        {"email_id": "candidato-1", "puntaje": 90},
        {"email_id": "candidato-2", "puntaje": 80},
    ]

    message_id = enviar_notificacion_ranking(
        destinatario="recruiter@example.com",
        ranking=ranking,
    )

    assert message_id == "mensaje-123"

    mock_credenciales.assert_called_once()

    servicio.users.return_value.messages.return_value.send.assert_called_once()

    llamada = (
        servicio.users.return_value
        .messages.return_value
        .send.call_args
    )

    assert llamada.kwargs["userId"] == "me"

    raw = llamada.kwargs["body"]["raw"]
    mensaje_decodificado = base64.urlsafe_b64decode(
        raw.encode("utf-8")
    ).decode("utf-8")

    assert "recruiter@example.com" in mensaje_decodificado
    assert "Ranking listo" in mensaje_decodificado