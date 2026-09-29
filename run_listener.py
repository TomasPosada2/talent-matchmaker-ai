"""
Listener continuo de Gmail.

Sprint 5 - Issue #44:
Detecta automáticamente nuevos correos y ejecuta el pipeline
sin necesidad de lanzar manualmente run_batch.py.
"""

from pathlib import Path

from src.email_polling import ejecutar_listener


BASE_DIR = Path(__file__).resolve().parent

CARPETA_TRABAJO = BASE_DIR / "data" / "salida"
CARPETA_GMAIL = CARPETA_TRABAJO / "gmail"
RUTA_ESTADO = CARPETA_TRABAJO / "polling_state.json"


def main():
    print("Iniciando listener de Gmail...")
    print("Presiona Ctrl+C para detenerlo.")

    ejecutar_listener(
        carpeta_descargas=CARPETA_GMAIL,
        carpeta_trabajo=CARPETA_TRABAJO,
        ruta_estado=RUTA_ESTADO,
        intervalo_segundos=60,
        max_resultados=50,
    )


if __name__ == "__main__":
    main()