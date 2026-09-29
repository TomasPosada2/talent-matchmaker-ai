"""
Persistencia de perfiles de candidatos en PostgreSQL.

Sprint 5 - Issue #46:
Migrate profile storage from JSON files to Postgres.

Este módulo encapsula el acceso a la base de datos para que el resto
del proyecto no dependa directamente de psycopg.
"""

import json
import os

import psycopg
from psycopg.rows import dict_row


def obtener_database_url() -> str:
    """
    Obtiene la URL de conexión desde la variable de entorno DATABASE_URL.

    Las credenciales nunca deben almacenarse directamente en el código.
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "La variable de entorno DATABASE_URL no está configurada."
        )

    return database_url


def obtener_conexion():
    """Crea una conexión nueva a PostgreSQL."""
    return psycopg.connect(obtener_database_url())


def crear_tablas() -> None:
    """
    Crea la tabla de perfiles si todavía no existe.

    Se conserva el perfil completo como JSONB para mantener exactamente
    la estructura validada por PERFIL_SCHEMA, mientras los campos
    principales se almacenan también como columnas consultables.
    """
    consulta = """
        CREATE TABLE IF NOT EXISTS profiles (
            id BIGSERIAL PRIMARY KEY,
            email_id TEXT NOT NULL UNIQUE,
            archivo_origen TEXT NOT NULL,
            nombre TEXT,
            email TEXT,
            telefono TEXT,
            perfil JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(consulta)


def _extraer_valor(campo):
    """
    Obtiene 'valor' de un campo con la estructura:
    {"valor": ..., "evidencia": ...}

    Si el valor es una lista, se serializa como JSON para no perder datos.
    """
    if not isinstance(campo, dict):
        return None

    valor = campo.get("valor")

    if isinstance(valor, list):
        return json.dumps(valor, ensure_ascii=False)

    return valor


def guardar_perfil(perfil: dict) -> None:
    """
    Inserta un perfil en PostgreSQL.

    Si ya existe un perfil con el mismo email_id, actualiza sus datos.
    """
    contacto = perfil.get("contacto") or {}

    nombre = _extraer_valor(perfil.get("nombre"))
    email = _extraer_valor(contacto.get("email"))
    telefono = _extraer_valor(contacto.get("telefono"))

    consulta = """
        INSERT INTO profiles (
            email_id,
            archivo_origen,
            nombre,
            email,
            telefono,
            perfil
        )
        VALUES (
            %(email_id)s,
            %(archivo_origen)s,
            %(nombre)s,
            %(email)s,
            %(telefono)s,
            %(perfil)s
        )
        ON CONFLICT (email_id)
        DO UPDATE SET
            archivo_origen = EXCLUDED.archivo_origen,
            nombre = EXCLUDED.nombre,
            email = EXCLUDED.email,
            telefono = EXCLUDED.telefono,
            perfil = EXCLUDED.perfil,
            updated_at = CURRENT_TIMESTAMP;
    """

    parametros = {
        "email_id": perfil["email_id"],
        "archivo_origen": perfil["archivo_origen"],
        "nombre": nombre,
        "email": email,
        "telefono": telefono,
        "perfil": json.dumps(perfil, ensure_ascii=False),
    }

    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(consulta, parametros)


def obtener_perfil(email_id: str) -> dict | None:
    """Recupera un perfil completo por email_id."""
    consulta = """
        SELECT perfil
        FROM profiles
        WHERE email_id = %s;
    """

    with obtener_conexion() as conexion:
        with conexion.cursor(row_factory=dict_row) as cursor:
            cursor.execute(consulta, (email_id,))
            fila = cursor.fetchone()

    if fila is None:
        return None

    return fila["perfil"]


def listar_perfiles() -> list[dict]:
    """Recupera todos los perfiles almacenados."""
    consulta = """
        SELECT perfil
        FROM profiles
        ORDER BY id;
    """

    with obtener_conexion() as conexion:
        with conexion.cursor(row_factory=dict_row) as cursor:
            cursor.execute(consulta)
            filas = cursor.fetchall()

    return [fila["perfil"] for fila in filas]


def contar_perfiles() -> int:
    """Devuelve la cantidad de perfiles almacenados."""
    consulta = "SELECT COUNT(*) AS total FROM profiles;"

    with obtener_conexion() as conexion:
        with conexion.cursor(row_factory=dict_row) as cursor:
            cursor.execute(consulta)
            fila = cursor.fetchone()

    return int(fila["total"])