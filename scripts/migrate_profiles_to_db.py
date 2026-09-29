"""
Migra perfiles históricos almacenados en JSON hacia PostgreSQL.

Sprint 5 - Issue #47:
Data migration script: JSON profiles to DB.

Uso:

    py scripts/migrate_profiles_to_db.py ruta/al/perfiles.json

o:

    py scripts/migrate_profiles_to_db.py ruta/al/directorio
"""

import argparse
import json
import sys
from pathlib import Path

# Permite ejecutar este archivo directamente desde scripts/
ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import profile_repository, schema


def cargar_perfiles_archivo(ruta: Path) -> list[dict]:
    """
    Lee perfiles desde un archivo JSON.

    Formatos admitidos:
    - Lista directa de perfiles.
    - Reporte con una clave "perfiles".
    - Un único perfil.
    """
    with ruta.open("r", encoding="utf-8-sig") as archivo:
        datos = json.load(archivo)

    if isinstance(datos, list):
        return datos

    if isinstance(datos, dict) and isinstance(datos.get("perfiles"), list):
        return datos["perfiles"]

    if isinstance(datos, dict) and "email_id" in datos:
        return [datos]

    raise ValueError(
        f"Formato JSON no reconocido en {ruta}. "
        "Se esperaba una lista de perfiles, un reporte con 'perfiles' "
        "o un perfil individual."
    )


def descubrir_archivos(ruta: Path) -> list[Path]:
    """
    Devuelve los archivos JSON que deben migrarse.

    Si la ruta es un archivo, procesa únicamente ese archivo.
    Si es un directorio, procesa todos los *.json del directorio.
    """
    if ruta.is_file():
        if ruta.suffix.lower() != ".json":
            raise ValueError("El archivo de entrada debe tener extensión .json.")

        return [ruta]

    if ruta.is_dir():
        return sorted(ruta.glob("*.json"))

    raise FileNotFoundError(f"No existe la ruta: {ruta}")


def migrar_perfiles(ruta: Path) -> dict:
    """
    Migra los perfiles encontrados hacia PostgreSQL.

    Los perfiles inválidos se omiten y se reportan sin detener
    la migración de los demás.
    """
    archivos = descubrir_archivos(ruta)

    resumen = {
        "archivos_encontrados": len(archivos),
        "perfiles_encontrados": 0,
        "migrados": 0,
        "invalidos": 0,
        "errores_archivo": 0,
        "detalle_errores": [],
    }

    profile_repository.crear_tablas()

    for archivo in archivos:
        try:
            perfiles = cargar_perfiles_archivo(archivo)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            resumen["errores_archivo"] += 1
            resumen["detalle_errores"].append(
                {
                    "archivo": str(archivo),
                    "error": str(error),
                }
            )
            continue

        resumen["perfiles_encontrados"] += len(perfiles)

        for perfil in perfiles:
            if not isinstance(perfil, dict):
                resumen["invalidos"] += 1
                resumen["detalle_errores"].append(
                    {
                        "archivo": str(archivo),
                        "email_id": None,
                        "error": "El perfil no es un objeto JSON.",
                    }
                )
                continue

            es_valido, error_schema = schema.validar_perfil(perfil)

            if not es_valido:
                resumen["invalidos"] += 1
                resumen["detalle_errores"].append(
                    {
                        "archivo": str(archivo),
                        "email_id": perfil.get("email_id"),
                        "error": error_schema,
                    }
                )
                continue

            try:
                profile_repository.guardar_perfil(perfil)
                resumen["migrados"] += 1
            except Exception as error:
                resumen["detalle_errores"].append(
                    {
                        "archivo": str(archivo),
                        "email_id": perfil.get("email_id"),
                        "error": f"Error PostgreSQL: {error}",
                    }
                )

    return resumen


def imprimir_resumen(resumen: dict) -> None:
    """Muestra un resumen legible de la migración."""
    print("\n=== Migración JSON -> PostgreSQL ===")
    print(f"Archivos encontrados: {resumen['archivos_encontrados']}")
    print(f"Perfiles encontrados: {resumen['perfiles_encontrados']}")
    print(f"Migrados:             {resumen['migrados']}")
    print(f"Inválidos:            {resumen['invalidos']}")
    print(f"Errores de archivo:   {resumen['errores_archivo']}")

    if resumen["detalle_errores"]:
        print("\nErrores encontrados:")

        for error in resumen["detalle_errores"]:
            print(
                f"- {error.get('archivo')} | "
                f"{error.get('email_id', '-')} | "
                f"{error['error']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Migra perfiles históricos almacenados en JSON "
            "hacia PostgreSQL."
        )
    )

    parser.add_argument(
        "ruta",
        type=Path,
        help="Archivo JSON o directorio que contiene perfiles JSON.",
    )

    args = parser.parse_args()

    try:
        resumen = migrar_perfiles(args.ruta)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    imprimir_resumen(resumen)

    if (
        resumen["invalidos"] > 0
        or resumen["errores_archivo"] > 0
        or resumen["detalle_errores"]
    ):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())