"""
Tests de persistencia PostgreSQL.

Sprint 5 - Issue #46:
Migrate profile storage from JSON files to Postgres.

Las pruebas unitarias no necesitan una instancia real de PostgreSQL:
se mockea la conexión para comprobar el comportamiento del repositorio.
"""

from unittest.mock import MagicMock, patch

import pytest

from src import profile_repository


def _perfil_ejemplo():
    return {
        "email_id": "email-001",
        "archivo_origen": "candidato.pdf",
        "nombre": {
            "valor": "Ana Torres",
            "evidencia": "Ana Torres",
        },
        "contacto": {
            "email": {
                "valor": "ana@example.com",
                "evidencia": "ana@example.com",
            },
            "telefono": {
                "valor": "+57 300 123 4567",
                "evidencia": "+57 300 123 4567",
            },
        },
        "educacion": {
            "valor": ["Ingeniería de Sistemas"],
            "evidencia": ["Ingeniería de Sistemas"],
        },
        "experiencia": {
            "valor": ["Backend Developer"],
            "evidencia": ["Backend Developer"],
        },
        "habilidades": {
            "valor": ["Python", "SQL"],
            "evidencia": ["Python", "SQL"],
        },
    }


def _conexion_mock():
    conexion = MagicMock()
    cursor = MagicMock()

    conexion.__enter__.return_value = conexion
    conexion.__exit__.return_value = False

    cursor.__enter__.return_value = cursor
    cursor.__exit__.return_value = False

    conexion.cursor.return_value = cursor

    return conexion, cursor


def test_obtener_database_url_desde_entorno(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://usuario:password@localhost:5432/test_db",
    )

    resultado = profile_repository.obtener_database_url()

    assert resultado == (
        "postgresql://usuario:password@localhost:5432/test_db"
    )


def test_obtener_database_url_falla_si_no_existe(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError):
        profile_repository.obtener_database_url()


def test_crear_tablas_ejecuta_create_table():
    conexion, cursor = _conexion_mock()

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        profile_repository.crear_tablas()

    consulta = cursor.execute.call_args.args[0]

    assert "CREATE TABLE IF NOT EXISTS profiles" in consulta
    assert "JSONB" in consulta
    assert "email_id TEXT NOT NULL UNIQUE" in consulta


def test_guardar_perfil_realiza_upsert():
    conexion, cursor = _conexion_mock()
    perfil = _perfil_ejemplo()

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        profile_repository.guardar_perfil(perfil)

    consulta = cursor.execute.call_args.args[0]
    parametros = cursor.execute.call_args.args[1]

    assert "INSERT INTO profiles" in consulta
    assert "ON CONFLICT (email_id)" in consulta

    assert parametros["email_id"] == "email-001"
    assert parametros["archivo_origen"] == "candidato.pdf"
    assert parametros["nombre"] == "Ana Torres"
    assert parametros["email"] == "ana@example.com"
    assert parametros["telefono"] == "+57 300 123 4567"

    assert '"email_id": "email-001"' in parametros["perfil"]


def test_obtener_perfil_devuelve_perfil():
    conexion, cursor = _conexion_mock()
    perfil = _perfil_ejemplo()

    cursor.fetchone.return_value = {
        "perfil": perfil,
    }

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        resultado = profile_repository.obtener_perfil(
            "email-001"
        )

    assert resultado == perfil

    cursor.execute.assert_called_once()

    consulta = cursor.execute.call_args.args[0]
    parametros = cursor.execute.call_args.args[1]

    assert "WHERE email_id = %s" in consulta
    assert parametros == ("email-001",)


def test_obtener_perfil_inexistente_devuelve_none():
    conexion, cursor = _conexion_mock()

    cursor.fetchone.return_value = None

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        resultado = profile_repository.obtener_perfil(
            "no-existe"
        )

    assert resultado is None


def test_listar_perfiles_devuelve_todos():
    conexion, cursor = _conexion_mock()

    perfil_1 = _perfil_ejemplo()

    perfil_2 = _perfil_ejemplo()
    perfil_2["email_id"] = "email-002"
    perfil_2["nombre"]["valor"] = "Carlos Pérez"

    cursor.fetchall.return_value = [
        {"perfil": perfil_1},
        {"perfil": perfil_2},
    ]

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        resultado = profile_repository.listar_perfiles()

    assert len(resultado) == 2
    assert resultado[0]["email_id"] == "email-001"
    assert resultado[1]["email_id"] == "email-002"


def test_contar_perfiles():
    conexion, cursor = _conexion_mock()

    cursor.fetchone.return_value = {
        "total": 7,
    }

    with patch.object(
        profile_repository,
        "obtener_conexion",
        return_value=conexion,
    ):
        resultado = profile_repository.contar_perfiles()

    assert resultado == 7