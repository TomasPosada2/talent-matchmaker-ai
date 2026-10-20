
"""Notificaciones locales del dashboard - Issue #57."""

from datetime import datetime


MAX_NOTIFICACIONES = 50


def crear_notificacion(
    notificaciones: list,
    titulo: str,
    mensaje: str,
    tipo: str = "info",
) -> list:
    """Agrega una notificación al inicio de la lista."""
    if tipo not in {"info", "success", "warning", "error"}:
        tipo = "info"

    nueva = {
        "id": datetime.now().isoformat(timespec="microseconds"),
        "titulo": titulo,
        "mensaje": mensaje,
        "tipo": tipo,
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "leida": False,
    }

    return [nueva, *notificaciones][:MAX_NOTIFICACIONES]


def contar_no_leidas(notificaciones: list) -> int:
    """Cuenta las notificaciones pendientes de lectura."""
    return sum(
        1
        for notificacion in notificaciones
        if not notificacion.get("leida", False)
    )


def marcar_todas_leidas(notificaciones: list) -> list:
    """Marca todas las notificaciones como leídas."""
    return [
        {**notificacion, "leida": True}
        for notificacion in notificaciones
    ]


def limpiar_notificaciones() -> list:
    """Devuelve una lista vacía de notificaciones."""
    return []
