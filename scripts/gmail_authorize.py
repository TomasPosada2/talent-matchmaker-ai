"""
Autoriza por primera vez el acceso a la bandeja de Gmail.

Sprint 8 - Issue #86. El consentimiento de Google abre un navegador, así
que se hace en el computador (no dentro de Docker):

1. Descarga desde Google Cloud las credenciales OAuth de tipo
   "App de escritorio" y guárdalas como secrets/credentials.json.
2. Ejecuta:
       python scripts/gmail_authorize.py
3. Inicia sesión con la cuenta de Gmail que recibe las hojas de vida
   y acepta los permisos (leer correos y enviar notificaciones).

El token queda en secrets/token.json; el listener de Docker lo usa y lo
renueva solo. Ver docs/runbook.md, sección 3.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SECRETS_DIR = ROOT_DIR / "secrets"

os.environ.setdefault("GMAIL_CREDENTIALS_PATH", str(SECRETS_DIR / "credentials.json"))
os.environ.setdefault("GMAIL_TOKEN_PATH", str(SECRETS_DIR / "token.json"))

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# gmail_auth lee las rutas del entorno al importarse.
from src.gmail_inbox import (  # noqa: E402
    obtener_consulta_gmail,
    obtener_cuenta_gmail,
)


def main() -> int:
    credenciales = Path(os.environ["GMAIL_CREDENTIALS_PATH"])

    if not credenciales.is_file():
        print(
            f"No se encontró {credenciales}.\n"
            "Descarga las credenciales OAuth (App de escritorio) desde "
            "Google Cloud y guárdalas con ese nombre. Ver docs/runbook.md §3.",
            file=sys.stderr,
        )
        return 1

    print("Se abrirá el navegador para autorizar el acceso a Gmail...")
    cuenta = obtener_cuenta_gmail()

    print(f"Gmail conectado: {cuenta}")
    print(f"Token guardado en: {os.environ['GMAIL_TOKEN_PATH']}")
    print(f"Correos que se procesarán (GMAIL_QUERY): {obtener_consulta_gmail()}")
    print("Siguiente paso: docker compose --profile gmail up -d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
