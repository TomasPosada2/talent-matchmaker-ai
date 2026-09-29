from unittest.mock import MagicMock, patch

import pytest

import src.gmail_auth as gmail_auth


def test_falla_si_no_existe_credentials(tmp_path, monkeypatch):
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"

    monkeypatch.setattr(gmail_auth, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(gmail_auth, "TOKEN_PATH", token_path)

    with pytest.raises(FileNotFoundError):
        gmail_auth.obtener_credenciales_gmail()


def test_reutiliza_token_valido(tmp_path, monkeypatch):
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    token_path.write_text("token-falso", encoding="utf-8")

    monkeypatch.setattr(gmail_auth, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(gmail_auth, "TOKEN_PATH", token_path)

    creds = MagicMock()
    creds.valid = True
    creds.expired = False
    creds.to_json.return_value = '{"token": "test"}'

    with patch.object(
        gmail_auth.Credentials,
        "from_authorized_user_file",
        return_value=creds,
    ) as mock_load:
        resultado = gmail_auth.obtener_credenciales_gmail()

    assert resultado is creds
    mock_load.assert_called_once_with(
        str(token_path),
        gmail_auth.SCOPES,
    )


def test_refresca_token_expirado(tmp_path, monkeypatch):
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    token_path.write_text("token-falso", encoding="utf-8")

    monkeypatch.setattr(gmail_auth, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(gmail_auth, "TOKEN_PATH", token_path)

    creds = MagicMock()
    creds.valid = False
    creds.expired = True
    creds.refresh_token = "refresh-token"
    creds.to_json.return_value = '{"token": "renovado"}'

    def refrescar(_request):
        creds.valid = True
        creds.expired = False

    creds.refresh.side_effect = refrescar

    with patch.object(
        gmail_auth.Credentials,
        "from_authorized_user_file",
        return_value=creds,
    ):
        resultado = gmail_auth.obtener_credenciales_gmail()

    assert resultado is creds
    creds.refresh.assert_called_once()


def test_crea_token_con_flujo_oauth(tmp_path, monkeypatch):
    credentials_path = tmp_path / "credentials.json"
    token_path = tmp_path / "token.json"
    credentials_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(gmail_auth, "CREDENTIALS_PATH", credentials_path)
    monkeypatch.setattr(gmail_auth, "TOKEN_PATH", token_path)

    creds = MagicMock()
    creds.valid = True
    creds.to_json.return_value = '{"token": "nuevo"}'

    flow = MagicMock()
    flow.run_local_server.return_value = creds

    with patch.object(
        gmail_auth.InstalledAppFlow,
        "from_client_secrets_file",
        return_value=flow,
    ) as mock_flow:
        resultado = gmail_auth.obtener_credenciales_gmail()

    assert resultado is creds
    mock_flow.assert_called_once_with(
        str(credentials_path),
        gmail_auth.SCOPES,
    )
    flow.run_local_server.assert_called_once_with(port=0)

    assert token_path.exists()
    assert token_path.read_text(encoding="utf-8") == '{"token": "nuevo"}'