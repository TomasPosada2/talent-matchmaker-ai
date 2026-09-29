"""
Sprint 5 - Issue #50.

Notificación por correo electrónico al recruiter cuando
un ranking de candidatos termina correctamente.
"""

import base64
import logging
from email.message import EmailMessage

from googleapiclient.discovery import build

from .gmail_auth import obtener_credenciales_gmail


logger = logging.getLogger("email_notifier")


def construir_mensaje_ranking(
    destinatario: str,
    total_candidatos: int,
) -> EmailMessage:
    """
    Construye el mensaje que informa al recruiter
    que el ranking terminó correctamente.
    """
    mensaje = EmailMessage()

    mensaje["To"] = destinatario
    mensaje["Subject"] = "Talent Matchmaker - Ranking listo"

    mensaje.set_content(
        "El ranking de candidatos ha finalizado correctamente.\n\n"
        f"Candidatos incluidos en el ranking: {total_candidatos}.\n\n"
        "Puedes consultar los resultados en Talent Matchmaker."
    )

    return mensaje


def enviar_notificacion_ranking(
    destinatario: str,
    ranking: list,
) -> str:
    """
    Envía al recruiter una notificación mediante Gmail API.

    Retorna el ID del mensaje enviado por Gmail.
    """
    if not destinatario:
        raise ValueError(
            "Se requiere el email del recruiter."
        )

    credenciales = obtener_credenciales_gmail()

    servicio = build(
        "gmail",
        "v1",
        credentials=credenciales,
        cache_discovery=False,
    )

    mensaje = construir_mensaje_ranking(
        destinatario=destinatario,
        total_candidatos=len(ranking),
    )

    mensaje_codificado = base64.urlsafe_b64encode(
        mensaje.as_bytes()
    ).decode("utf-8")

    resultado = (
        servicio.users()
        .messages()
        .send(
            userId="me",
            body={"raw": mensaje_codificado},
        )
        .execute()
    )

    message_id = resultado.get("id", "")

    logger.info(
        "Notificación de ranking enviada a %s. message_id=%s",
        destinatario,
        message_id,
    )

    return message_id