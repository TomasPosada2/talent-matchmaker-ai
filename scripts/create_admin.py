"""
Crea (o promueve) la cuenta de administrador inicial.

Sprint 7 - #61: el endpoint /auth/register ya no es público; solo un admin
puede crear cuentas. Este script crea el primer admin directamente en la
base de datos.

Uso:
    python scripts/create_admin.py admin@empresa.com

La contraseña se lee de la variable ADMIN_PASSWORD o se pide por consola
(nunca como argumento, para que no quede en el historial del shell).
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import auth, profile_repository  # noqa: E402


def promover_a_admin(email: str) -> None:
    with profile_repository.obtener_conexion() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE recruiters SET role = 'admin' WHERE email = %s",
                (email.lower().strip(),),
            )
        conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("email", help="Correo del administrador.")
    args = parser.parse_args()

    auth.crear_tabla_recruiters()

    if auth.obtener_recruiter_por_email(args.email) is not None:
        promover_a_admin(args.email)
        print(f"La cuenta {args.email} ya existía; ahora tiene rol admin.")
        return 0

    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Contraseña: ")

    if len(password) < 8:
        print("La contraseña debe tener al menos 8 caracteres.", file=sys.stderr)
        return 1

    auth.crear_recruiter(args.email, password, role="admin")
    print(f"Administrador creado: {args.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
