import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src import auth


def test_hash_y_verificacion_password():
    password = "Password123!"

    hashed = auth.hash_password(password)

    assert hashed != password
    assert auth.verificar_password(
        password,
        hashed,
    )
    assert not auth.verificar_password(
        "incorrecta",
        hashed,
    )


def test_jwt_secret_requerido(monkeypatch):
    monkeypatch.delenv(
        "JWT_SECRET",
        raising=False,
    )

    with pytest.raises(RuntimeError):
        auth.obtener_jwt_secret()


def test_crear_access_token(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "secret-de-prueba",
    )

    token = auth.crear_access_token(
        "recruiter@example.com"
    )

    payload = jwt.decode(
        token,
        "secret-de-prueba",
        algorithms=[auth.ALGORITHM],
    )

    assert payload["sub"] == "recruiter@example.com"
    assert "iat" in payload
    assert "exp" in payload


def test_token_valido_devuelve_recruiter(
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET",
        "secret-de-prueba",
    )

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 1,
            "email": email,
            "password_hash": "hash",
        },
    )

    token = auth.crear_access_token(
        "recruiter@example.com"
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    recruiter = auth.obtener_recruiter_actual(
        credentials
    )

    assert recruiter == {
        "id": 1,
        "email": "recruiter@example.com",
    }


def test_token_invalido(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET",
        "secret-de-prueba",
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token-invalido",
    )

    with pytest.raises(HTTPException) as exc:
        auth.obtener_recruiter_actual(
            credentials
        )

    assert exc.value.status_code == 401


def test_recruiter_token_no_existe(
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET",
        "secret-de-prueba",
    )

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: None,
    )

    token = auth.crear_access_token(
        "noexiste@example.com"
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc:
        auth.obtener_recruiter_actual(
            credentials
        )

    assert exc.value.status_code == 401