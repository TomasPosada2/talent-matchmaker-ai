"""
Persistencia de plantillas de descripciones de vacantes.

Sprint 5 - Issue #51:
Configurable job description templates.
"""

import json

from psycopg.rows import dict_row

from src import profile_repository


def crear_tabla() -> None:
    """
    Crea la tabla job_templates si todavía no existe.

    Cada plantilla pertenece a un recruiter.
    """
    consulta = """
        CREATE TABLE IF NOT EXISTS job_templates (
            id BIGSERIAL PRIMARY KEY,
            recruiter_id BIGINT NOT NULL
                REFERENCES recruiters(id)
                ON DELETE CASCADE,
            nombre TEXT NOT NULL,
            vacante JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (recruiter_id, nombre)
        );
    """

    with profile_repository.obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(consulta)


def guardar_plantilla(
    recruiter_id: int,
    nombre: str,
    vacante: dict,
) -> dict:
    """
    Guarda una plantilla para un recruiter.

    Si ya existe una plantilla con el mismo nombre para ese
    recruiter, actualiza su contenido.
    """
    consulta = """
        INSERT INTO job_templates (
            recruiter_id,
            nombre,
            vacante
        )
        VALUES (%s, %s, %s)
        ON CONFLICT (recruiter_id, nombre)
        DO UPDATE SET
            vacante = EXCLUDED.vacante
        RETURNING id, recruiter_id, nombre, vacante;
    """

    with profile_repository.obtener_conexion() as conexion:
        with conexion.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                consulta,
                (
                    recruiter_id,
                    nombre.strip(),
                    json.dumps(
                        vacante,
                        ensure_ascii=False,
                    ),
                ),
            )

            fila = cursor.fetchone()

    return dict(fila)


def listar_plantillas(
    recruiter_id: int,
) -> list[dict]:
    """Lista las plantillas pertenecientes a un recruiter."""
    consulta = """
        SELECT id, recruiter_id, nombre, vacante
        FROM job_templates
        WHERE recruiter_id = %s
        ORDER BY id;
    """

    with profile_repository.obtener_conexion() as conexion:
        with conexion.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                consulta,
                (recruiter_id,),
            )

            filas = cursor.fetchall()

    return [dict(fila) for fila in filas]


def obtener_plantilla(
    recruiter_id: int,
    template_id: int,
) -> dict | None:
    """
    Obtiene una plantilla únicamente si pertenece
    al recruiter autenticado.
    """
    consulta = """
        SELECT id, recruiter_id, nombre, vacante
        FROM job_templates
        WHERE id = %s
          AND recruiter_id = %s;
    """

    with profile_repository.obtener_conexion() as conexion:
        with conexion.cursor(
            row_factory=dict_row
        ) as cursor:
            cursor.execute(
                consulta,
                (
                    template_id,
                    recruiter_id,
                ),
            )

            fila = cursor.fetchone()

    if fila is None:
        return None

    return dict(fila)