"""
Carga datos de demostración para ver el sistema funcionando de punta a punta.

Sprint 7 - Issue #65. Pasos:
1. Genera la bandeja simulada (25 correos sintéticos, datos ficticios).
2. Corre el pipeline completo (incluye escaneo ClamAV) y guarda los
   perfiles en PostgreSQL.
3. Crea la cuenta admin de demostración si no existe.
4. Crea una vacante de ejemplo para ese admin.

Uso (dentro de Docker):
    docker compose run --rm api python scripts/seed_demo.py

Variables: DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD.
"""

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.generate_sample_inbox import INBOX_DIR, generar_bandeja  # noqa: E402
from src import auth, job_template_repository, privacy  # noqa: E402
from src.observability import configurar_logging  # noqa: E402
from src.pipeline import procesar_lote  # noqa: E402

VACANTE_DEMO = {
    "nombre": "Analista de datos (demo)",
    "vacante": {
        "cargo": "Analista de Datos",
        "requisitos": ["Python", "SQL", "Power BI", "Inglés B2"],
    },
}


def main() -> int:
    configurar_logging()

    email = os.getenv("DEMO_ADMIN_EMAIL", "admin@demo.local")
    password = os.getenv("DEMO_ADMIN_PASSWORD")

    if not password or len(password) < 8:
        print("Define DEMO_ADMIN_PASSWORD (mínimo 8 caracteres).", file=sys.stderr)
        return 1

    generar_bandeja()
    reporte = procesar_lote(INBOX_DIR, privacy.obtener_carpeta_trabajo())
    print(
        f"Pipeline: {reporte['procesados_exitosamente']}/"
        f"{reporte['candidatos_a_procesar']} CVs procesados."
    )

    auth.crear_tabla_recruiters()
    admin = auth.obtener_recruiter_por_email(email)
    if admin is None:
        auth.crear_recruiter(email, password, role="admin")
        admin = auth.obtener_recruiter_por_email(email)
        print(f"Admin de demostración creado: {email}")
    else:
        print(f"Admin de demostración ya existía: {email}")

    job_template_repository.crear_tabla()
    existentes = job_template_repository.listar_plantillas(recruiter_id=admin["id"])
    if not any(p.get("nombre") == VACANTE_DEMO["nombre"] for p in existentes):
        job_template_repository.guardar_plantilla(
            recruiter_id=admin["id"],
            nombre=VACANTE_DEMO["nombre"],
            vacante=VACANTE_DEMO["vacante"],
        )
        print(f"Vacante de ejemplo creada: {VACANTE_DEMO['nombre']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
