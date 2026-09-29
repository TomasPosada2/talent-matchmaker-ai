from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

ROOT_DIR = Path(__file__).resolve().parents[1]
CREDENTIALS_PATH = ROOT_DIR / "credentials.json"
TOKEN_PATH = ROOT_DIR / "token.json"


def obtener_credenciales_gmail() -> Credentials:
    """
    Obtiene credenciales OAuth2 válidas para Gmail.

    Primera ejecución:
    - abre el navegador;
    - solicita autorización del usuario;
    - guarda token.json.

    Ejecuciones posteriores:
    - reutiliza token.json;
    - refresca automáticamente el token cuando sea necesario.
    """

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_PATH),
            SCOPES,
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not CREDENTIALS_PATH.exists():
            raise FileNotFoundError(
                "No se encontró credentials.json."
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES,
        )

        creds = flow.run_local_server(
            port=0,
        )

    TOKEN_PATH.write_text(
        creds.to_json(),
        encoding="utf-8",
    )

    return creds