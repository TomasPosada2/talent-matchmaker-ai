
import os

import httpx


API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


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
        return None, (
            f"Error HTTP {exc.response.status_code} "
            "al consultar la API."
        )

    except (httpx.RequestError, ValueError):
        return None, (
            "No fue posible conectar con FastAPI "
            "o interpretar su respuesta."
        )
