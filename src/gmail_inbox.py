import base64
import logging
from pathlib import Path

from googleapiclient.discovery import build

from .email_detector import CorreoDetectado, FORMATOS_SOPORTADOS
from .gmail_auth import obtener_credenciales_gmail


logger = logging.getLogger("gmail_inbox")


def _obtener_header(headers: list[dict], nombre: str) -> str | None:
    """Obtiene un header de Gmail sin distinguir mayúsculas/minúsculas."""
    for header in headers:
        if header.get("name", "").lower() == nombre.lower():
            return header.get("value")
    return None


def _obtener_partes(payload: dict) -> list[dict]:
    """Recorre recursivamente las partes MIME de un correo."""
    partes = []

    for parte in payload.get("parts", []):
        partes.append(parte)
        partes.extend(_obtener_partes(parte))

    return partes


def _sanitizar_nombre(nombre: str) -> str:
    """
    Evita que el nombre de un adjunto pueda escribir fuera
    de la carpeta destinada al correo.
    """
    return Path(nombre).name


def _descargar_adjunto(
    servicio,
    message_id: str,
    attachment_id: str,
    destino: Path,
) -> None:
    respuesta = (
        servicio.users()
        .messages()
        .attachments()
        .get(
            userId="me",
            messageId=message_id,
            id=attachment_id,
        )
        .execute()
    )

    datos = respuesta.get("data", "")
    contenido = base64.urlsafe_b64decode(datos.encode("utf-8"))

    destino.write_bytes(contenido)


def obtener_correos_gmail(
    carpeta_descargas: Path,
    max_resultados: int = 50,
) -> list[CorreoDetectado]:
    """
    Lee correos reales de Gmail y devuelve objetos CorreoDetectado,
    manteniendo la interfaz utilizada por el pipeline existente.

    Los adjuntos soportados se descargan localmente para que las etapas
    posteriores puedan procesarlos sin conocer detalles de Gmail.
    """
    carpeta_descargas = Path(carpeta_descargas)
    carpeta_descargas.mkdir(parents=True, exist_ok=True)

    credenciales = obtener_credenciales_gmail()

    servicio = build(
        "gmail",
        "v1",
        credentials=credenciales,
        cache_discovery=False,
    )

    respuesta = (
        servicio.users()
        .messages()
        .list(
            userId="me",
            maxResults=max_resultados,
        )
        .execute()
    )

    mensajes = respuesta.get("messages", [])
    resultados = []

    for referencia in mensajes:
        message_id = referencia["id"]

        mensaje = (
            servicio.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        payload = mensaje.get("payload", {})
        headers = payload.get("headers", [])

        remitente = _obtener_header(headers, "From")
        asunto = _obtener_header(headers, "Subject")

        carpeta_email = carpeta_descargas / message_id
        carpeta_email.mkdir(parents=True, exist_ok=True)

        partes = _obtener_partes(payload)

        partes_con_adjunto = [
            parte
            for parte in partes
            if parte.get("filename")
        ]

        if not partes_con_adjunto:
            resultados.append(
                CorreoDetectado(
                    email_id=message_id,
                    ruta_carpeta=carpeta_email,
                    remitente=remitente,
                    asunto=asunto,
                    adjunto_valido=None,
                    estado="ignorado_sin_adjunto",
                    motivo="El correo no tiene archivos adjuntos.",
                )
            )
            continue

        adjunto_valido = None
        extensiones_encontradas = []

        for parte in partes_con_adjunto:
            nombre_original = parte.get("filename", "")
            nombre_archivo = _sanitizar_nombre(nombre_original)
            extension = Path(nombre_archivo).suffix.lower()

            extensiones_encontradas.append(extension)

            if extension not in FORMATOS_SOPORTADOS:
                continue

            attachment_id = parte.get("body", {}).get("attachmentId")

            if not attachment_id:
                continue

            ruta_adjunto = carpeta_email / nombre_archivo

            _descargar_adjunto(
                servicio,
                message_id,
                attachment_id,
                ruta_adjunto,
            )

            adjunto_valido = ruta_adjunto
            break

        if adjunto_valido is not None:
            resultado = CorreoDetectado(
                email_id=message_id,
                ruta_carpeta=carpeta_email,
                remitente=remitente,
                asunto=asunto,
                adjunto_valido=adjunto_valido,
                estado="candidato_a_procesar",
            )
        else:
            resultado = CorreoDetectado(
                email_id=message_id,
                ruta_carpeta=carpeta_email,
                remitente=remitente,
                asunto=asunto,
                adjunto_valido=None,
                estado="descartado_formato_no_soportado",
                motivo=(
                    f"Formatos no soportados: {extensiones_encontradas}. "
                    f"Soportados: {sorted(FORMATOS_SOPORTADOS)}"
                ),
            )

        resultados.append(resultado)

        logger.info(
            "[%s] %s",
            resultado.email_id,
            resultado.estado,
        )

    return resultados