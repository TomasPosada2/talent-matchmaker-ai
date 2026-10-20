
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src import auth

SECRET_PRUEBA = "secret-de-prueba-con-al-menos-32-caracteres"


def credenciales_de(email):
    token = auth.crear_access_token(email)
    return HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )


def test_hash_y_verificacion_password():
    password = "Password123!"
    hashed = auth.hash_password(password)

    assert hashed != password
    assert auth.verificar_password(password, hashed)
    assert not auth.verificar_password("incorrecta", hashed)


def test_jwt_secret_requerido(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(RuntimeError):
        auth.obtener_jwt_secret()


def test_jwt_secret_corto_rechazado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "corto")

    with pytest.raises(RuntimeError):
        auth.obtener_jwt_secret()


def test_login_se_bloquea_tras_intentos_fallidos():
    email = "atacante@example.com"

    for _ in range(auth.MAX_INTENTOS_FALLIDOS - 1):
        auth.registrar_login_fallido(email)

    assert not auth.login_bloqueado(email)

    auth.registrar_login_fallido(email)

    assert auth.login_bloqueado(email)
    assert auth.login_bloqueado(email.upper())

    auth.limpiar_intentos_login(email)

    assert not auth.login_bloqueado(email)


def test_crear_recruiter_rechaza_rol_invalido():
    with pytest.raises(ValueError):
        auth.crear_recruiter("x@example.com", "Password123!", role="root")


def test_crear_access_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    token = auth.crear_access_token("recruiter@example.com")

    payload = jwt.decode(
        token,
        SECRET_PRUEBA,
        algorithms=[auth.ALGORITHM],
    )

    assert payload["sub"] == "recruiter@example.com"
    assert "iat" in payload
    assert "exp" in payload


def test_token_valido_devuelve_recruiter(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 1,
            "email": email,
            "password_hash": "hash",
            "role": "recruiter",
        },
    )

    recruiter = auth.obtener_recruiter_actual(
        credenciales_de("recruiter@example.com")
    )

    assert recruiter == {
        "id": 1,
        "email": "recruiter@example.com",
        "role": "recruiter",
    }


def test_token_valido_devuelve_admin(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 2,
            "email": email,
            "password_hash": "hash",
            "role": "admin",
        },
    )

    admin = auth.obtener_recruiter_actual(
        credenciales_de("admin@example.com")
    )

    assert admin["role"] == "admin"


def test_token_invalido(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="token-invalido",
    )

    with pytest.raises(HTTPException) as exc:
        auth.obtener_recruiter_actual(credentials)

    assert exc.value.status_code == 401


def test_recruiter_token_no_existe(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: None,
    )

    with pytest.raises(HTTPException) as exc:
        auth.obtener_recruiter_actual(
            credenciales_de("noexiste@example.com")
        )

    assert exc.value.status_code == 401


def test_rol_desconocido_rechazado(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", SECRET_PRUEBA)

    monkeypatch.setattr(
        auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 3,
            "email": email,
            "role": "superuser",
        },
    )

    with pytest.raises(HTTPException) as exc:
        auth.obtener_recruiter_actual(
            credenciales_de("usuario@example.com")
        )

    assert exc.value.status_code == 403


def test_recruiter_no_tiene_permisos_admin():
    with pytest.raises(HTTPException) as exc:
        auth.requerir_admin(
            {"id": 1, "email": "recruiter@example.com",
             "role": "recruiter"}
        )

    assert exc.value.status_code == 403


def test_admin_tiene_permisos():
    usuario = {
        "id": 2,
        "email": "admin@example.com",
        "role": "admin",
    }

    assert auth.requerir_admin(usuario) == usuario
