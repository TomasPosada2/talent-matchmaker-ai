
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from src import profile_repository


ALGORITHM = "HS256"
TOKEN_EXPIRATION_MINUTES = 60
ROLES_VALIDOS = {"recruiter", "admin"}

password_hash = PasswordHash.recommended()
security = HTTPBearer()


def obtener_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET")
    if not secret:
        raise RuntimeError(
            "La variable de entorno JWT_SECRET no está configurada."
        )
    return secret


def crear_tabla_recruiters() -> None:
    with profile_repository.obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS recruiters (
                    id BIGSERIAL PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                ALTER TABLE recruiters
                ADD COLUMN IF NOT EXISTS role TEXT
                    NOT NULL DEFAULT 'recruiter'
                """
            )
            cursor.execute(
                """
                ALTER TABLE recruiters
                DROP CONSTRAINT IF EXISTS recruiters_role_check
                """
            )
            cursor.execute(
                """
                ALTER TABLE recruiters
                ADD CONSTRAINT recruiters_role_check
                CHECK (role IN ('recruiter', 'admin'))
                """
            )
        conn.commit()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verificar_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def crear_recruiter(email: str, password: str) -> dict:
    hashed = hash_password(password)

    with profile_repository.obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO recruiters (email, password_hash, role)
                VALUES (%s, %s, 'recruiter')
                RETURNING id, email
                """,
                (email.lower().strip(), hashed),
            )
            row = cursor.fetchone()
        conn.commit()

    return {"id": row[0], "email": row[1]}


def obtener_recruiter_por_email(email: str) -> dict | None:
    with profile_repository.obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, email, password_hash, role
                FROM recruiters
                WHERE email = %s
                """,
                (email.lower().strip(),),
            )
            row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "email": row[1],
        "password_hash": row[2],
        "role": row[3],
    }


def crear_access_token(email: str) -> str:
    ahora = datetime.now(timezone.utc)

    payload = {
        "sub": email,
        "iat": ahora,
        "exp": ahora + timedelta(
            minutes=TOKEN_EXPIRATION_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        obtener_jwt_secret(),
        algorithm=ALGORITHM,
    )


def obtener_recruiter_actual(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            obtener_jwt_secret(),
            algorithms=[ALGORITHM],
        )
        email = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=401,
                detail="Token inválido.",
            )

    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado.",
        ) from exc

    recruiter = obtener_recruiter_por_email(email)

    if recruiter is None:
        raise HTTPException(
            status_code=401,
            detail="Recruiter no encontrado.",
        )

    role = recruiter.get("role", "recruiter")

    if role not in ROLES_VALIDOS:
        raise HTTPException(
            status_code=403,
            detail="Rol de usuario no autorizado.",
        )

    return {
        "id": recruiter["id"],
        "email": recruiter["email"],
        "role": role,
    }


def requerir_admin(
    recruiter: dict = Depends(obtener_recruiter_actual),
) -> dict:
    if recruiter.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Se requieren permisos de administrador.",
        )

    return recruiter


def listar_recruiters_admin() -> list[dict]:
    with profile_repository.obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, email, role, created_at
                FROM recruiters
                ORDER BY id
                """
            )
            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "email": row[1],
            "role": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]
