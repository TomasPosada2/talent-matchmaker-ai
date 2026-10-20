
from fastapi.testclient import TestClient

from src import api


client = TestClient(api.app)


def recruiter_falso():
    return {
        "id": 1,
        "email": "recruiter@example.com",
        "role": "recruiter",
    }


def admin_falso():
    return {
        "id": 2,
        "email": "admin@example.com",
        "role": "admin",
    }


def limpiar_dependencias():
    api.app.dependency_overrides.clear()


def test_auth_me_requiere_login():
    limpiar_dependencias()

    response = client.get("/auth/me")

    assert response.status_code in (401, 403)


def test_auth_me_devuelve_rol():
    limpiar_dependencias()

    api.app.dependency_overrides[
        api.auth.obtener_recruiter_actual
    ] = recruiter_falso

    try:
        response = client.get("/auth/me")

        assert response.status_code == 200
        assert response.json() == recruiter_falso()
    finally:
        limpiar_dependencias()


def test_admin_users_requiere_login():
    limpiar_dependencias()

    response = client.get("/admin/users")

    assert response.status_code in (401, 403)


def test_recruiter_no_puede_listar_usuarios():
    limpiar_dependencias()

    api.app.dependency_overrides[
        api.auth.obtener_recruiter_actual
    ] = recruiter_falso

    try:
        response = client.get("/admin/users")

        assert response.status_code == 403
    finally:
        limpiar_dependencias()


def test_admin_puede_listar_usuarios(monkeypatch):
    limpiar_dependencias()

    api.app.dependency_overrides[
        api.auth.obtener_recruiter_actual
    ] = admin_falso

    usuarios = [
        {
            "id": 1,
            "email": "recruiter@example.com",
            "role": "recruiter",
            "created_at": "2026-10-19T10:00:00Z",
        },
        {
            "id": 2,
            "email": "admin@example.com",
            "role": "admin",
            "created_at": "2026-10-19T11:00:00Z",
        },
    ]

    monkeypatch.setattr(
        api.auth,
        "listar_recruiters_admin",
        lambda: usuarios,
    )

    try:
        response = client.get("/admin/users")

        assert response.status_code == 200
        assert response.json()["total"] == 2
        assert response.json()["users"] == usuarios
    finally:
        limpiar_dependencias()
