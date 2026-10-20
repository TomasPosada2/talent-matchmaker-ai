"""
Purga los datos de candidatos que superan el periodo de retención.

Sprint 7 - Issue #63. Borra:
- perfiles en PostgreSQL sin actualizar en más de RETENTION_DAYS días;
- CVs originales en disco (adjuntos extraídos y descargas de Gmail) más
  antiguos que ese mismo plazo.

Uso:
    RETENTION_DAYS=180 python scripts/purge_expired_data.py
    python scripts/purge_expired_data.py --dry-run

En Docker se ejecuta a diario desde el servicio `maintenance`.
"""

import argparse
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src import privacy, profile_repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Purga datos de candidatos vencidos.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo informa el periodo de retención, no borra nada.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    dias = privacy.obtener_retencion_dias()

    if args.dry_run:
        print(f"Retención configurada: {dias} días. No se borró nada (--dry-run).")
        return 0

    profile_repository.crear_tablas()
    eliminados = profile_repository.eliminar_perfiles_anteriores_a(dias)

    for email_id in eliminados:
        privacy.eliminar_archivos_candidato(email_id)

    archivos = privacy.purgar_archivos_antiguos(dias)

    print(
        f"Perfiles eliminados: {len(eliminados)}. "
        f"Archivos antiguos eliminados: {archivos}. "
        f"Retención: {dias} días."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
