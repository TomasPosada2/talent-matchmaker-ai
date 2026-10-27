"""
Listener continuo de Gmail.

Sprint 5 - Issue #44:
Detecta automáticamente nuevos correos y ejecuta el pipeline
sin necesidad de lanzar manualmente run_batch.py.
"""

import os
from pathlib import Path

from src.email_polling import ejecutar_listener
from src.observability import configurar_logging

BASE_DIR = Path(__file__).resolve().parent

CARPETA_TRABAJO = Path(os.getenv("DATA_DIR", BASE_DIR / "data" / "salida"))
CARPETA_GMAIL = CARPETA_TRABAJO / "gmail"
RUTA_ESTADO = CARPETA_TRABAJO / "polling_state.json"
RUTA_HEARTBEAT = CARPETA_TRABAJO / "listener_heartbeat.json"
INTERVALO_SEGUNDOS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))


def main():
    configurar_logging()
    print("Iniciando listener de Gmail...")
    print("Presiona Ctrl+C para detenerlo.")

    ejecutar_listener(
        carpeta_descargas=CARPETA_GMAIL,
        carpeta_trabajo=CARPETA_TRABAJO,
        ruta_estado=RUTA_ESTADO,
        intervalo_segundos=INTERVALO_SEGUNDOS,
        ruta_heartbeat=RUTA_HEARTBEAT,
    )


if __name__ == "__main__":
    main()