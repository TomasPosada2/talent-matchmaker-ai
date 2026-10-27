
"""
Cliente HTTP para conectar el dashboard con FastAPI.

Sprint 6:
- Autenticación de recruiters.
- Consultas GET a la API.
- Creación de plantillas de vacantes mediante POST.
"""

import os

import httpx

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


def _mensaje_error_http(status: int, accion: str) -> str:
    """
    Mensajes de error que dicen qué hacer, no solo el código
    (Sprint 7 - #59, WCAG 3.3.1 y 2.2.1: avisar cuando la sesión expira).
    """
    if status == 401:
        return (
            "Tu sesión expiró o no es válida (HTTP 401). "
            "Cierra sesión y vuelve a ingresar."
        )
    if status == 403:
        return "No tienes permisos para esta acción (HTTP 403)."
    if status == 409:
        return "El registro ya existe (HTTP 409)."
    if status == 422:
        return "Los datos enviados no son válidos (HTTP 422)."
    if status == 429:
        return "Demasiadas solicitudes. Espera unos minutos (HTTP 429)."
    return f"Error HTTP {status} {accion}. Intenta de nuevo más tarde."


def consultar_api(ruta: str, token: str | None = None):
    """Consulta FastAPI y devuelve (datos, error)."""
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.get(
            f"{API_URL}{ruta}",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        return response.json(), None

    except httpx.HTTPStatusError as exc:
        return None, _mensaje_error_http(
            exc.response.status_code,
            "al consultar la API",
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con FastAPI "
            "o interpretar su respuesta."
        )


def preguntar_asistente(mensajes: list[dict], token: str):
    """
    Envía la conversación a POST /chat y devuelve (datos, error).

    Sprint 8 - #87: una respuesta puede consultar varias herramientas, así
    que el tiempo de espera es mayor, y el error muestra el motivo exacto
    que da el servidor (falta de llave, límite diario, etc.).
    """
    try:
        response = httpx.post(
            f"{API_URL}/chat",
            json={"mensajes": mensajes},
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        response.raise_for_status()
        return response.json(), None

    except httpx.HTTPStatusError as exc:
        try:
            detalle = exc.response.json().get("detail")
        except ValueError:
            detalle = None

        if isinstance(detalle, str) and exc.response.status_code != 401:
            return None, detalle

        return None, _mensaje_error_http(
            exc.response.status_code,
            "al consultar el asistente",
        )

    except httpx.TimeoutException:
        return None, (
            "El asistente tardó demasiado en responder. "
            "Intenta con una pregunta más específica."
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con FastAPI "
            "o interpretar su respuesta."
        )


def enviar_api(
    ruta: str,
    datos: dict,
    token: str | None = None,
    timeout: float = 15,
):
    """
    Envía un POST a FastAPI y devuelve (datos, error).

    Sprint 8 - #75: el ranking con IA tarda más de un minuto, así que quien
    lo llama pasa un ``timeout`` mayor; con 15 s el dashboard abandonaba la
    espera aunque la API terminara bien.
    """
    headers = {}

    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.post(
            f"{API_URL}{ruta}",
            json=datos,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json(), None

    except httpx.HTTPStatusError as exc:
        return None, _mensaje_error_http(
            exc.response.status_code,
            "al guardar la información",
        )

    except httpx.TimeoutException:
        return None, (
            "El servidor tardó más de lo esperado en responder. "
            "La operación puede seguir en curso: revisa tus "
            "notificaciones en unos minutos."
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con FastAPI "
            "o interpretar su respuesta."
        )


def eliminar_api(ruta: str, token: str):
    """Envía un DELETE a FastAPI y devuelve (datos, error)."""
    try:
        response = httpx.delete(
            f"{API_URL}{ruta}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json(), None

    except httpx.HTTPStatusError as exc:
        return None, _mensaje_error_http(
            exc.response.status_code,
            "al eliminar la información",
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con FastAPI "
            "o interpretar su respuesta."
        )


def iniciar_sesion(correo: str, contrasena: str):
    """Autentica un recruiter y devuelve (datos, error)."""
    try:
        response = httpx.post(
            f"{API_URL}/auth/login",
            json={
                "email": correo,
                "password": contrasena,
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json(), None

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            return None, "Correo o contraseña incorrectos."

        if exc.response.status_code == 429:
            return None, (
                "Demasiados intentos fallidos. "
                "Espera 15 minutos e intenta de nuevo."
            )

        return None, (
            f"No fue posible iniciar sesión "
            f"(error HTTP {exc.response.status_code})."
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con el servidor "
            "de autenticación."
        )
