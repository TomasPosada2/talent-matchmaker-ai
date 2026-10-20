"""
Prueba de carga del pipeline y de la API (Sprint 7 - Issue #62).

1. Pipeline: genera N CVs sintéticos (datos ficticios, Faker) y los procesa
   con procesar_lote. Usa el pipeline real: ClamAV, extracción, schema y
   PostgreSQL. Mide la duración total, el rendimiento (CVs/min), la latencia
   por CV (p50/p95/máx) y la memoria pico del proceso.
2. API: lanza peticiones concurrentes a GET /profiles y mide latencia y errores.

Los perfiles de la prueba usan el prefijo ``load_`` y se borran al terminar.

Uso (dentro de Docker, con el stack levantado):
    docker compose run --rm api python scripts/load_test.py --cvs 100 200 \\
        --api-url http://api:8000 --api-requests 500 --api-concurrency 20
"""

import argparse
import json
import statistics
import sys
import tempfile
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import httpx  # noqa: E402

from scripts.generate_sample_inbox import _crear_cv_docx  # noqa: E402
from src import pipeline, profile_repository  # noqa: E402

PLANTILLAS = ["clasica", "en_ingles", "minimalista", "con_tabla"]
PREFIJO = "load_"


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, round(p / 100 * (len(ordenados) - 1)))
    return ordenados[indice]


def generar_bandeja(carpeta: Path, cantidad: int) -> None:
    for i in range(cantidad):
        email_id = f"{PREFIJO}{i:05d}"
        destino = carpeta / email_id
        destino.mkdir(parents=True)
        nombre_archivo = f"cv_{i}.docx"
        _crear_cv_docx(destino / nombre_archivo, PLANTILLAS[i % len(PLANTILLAS)])
        (destino / "metadata.json").write_text(
            json.dumps({"attachments": [nombre_archivo]}),
            encoding="utf-8",
        )


def borrar_perfiles_de_prueba() -> int:
    with profile_repository.obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "DELETE FROM profiles WHERE email_id LIKE %s",
                (f"{PREFIJO}%",),
            )
            return cursor.rowcount


def prueba_pipeline(cantidad: int) -> dict:
    latencias: list[float] = []
    original = pipeline.procesar_correo

    def medido(correo, carpeta_trabajo):
        inicio = time.perf_counter()
        try:
            return original(correo, carpeta_trabajo)
        finally:
            latencias.append(time.perf_counter() - inicio)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        inbox = tmp / "inbox"
        generar_bandeja(inbox, cantidad)

        pipeline.procesar_correo = medido
        tracemalloc.start()
        inicio = time.perf_counter()
        try:
            reporte = pipeline.procesar_lote(inbox, tmp / "salida")
        finally:
            duracion = time.perf_counter() - inicio
            _, memoria_pico = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            pipeline.procesar_correo = original

    return {
        "cvs": cantidad,
        "exitosos": reporte["procesados_exitosamente"],
        "fallidos": reporte["fallidos"],
        "duracion_s": round(duracion, 1),
        "cvs_por_minuto": round(cantidad / duracion * 60),
        "p50_ms": round(statistics.median(latencias) * 1000),
        "p95_ms": round(percentil(latencias, 95) * 1000),
        "max_ms": round(max(latencias) * 1000),
        "memoria_pico_mb": round(memoria_pico / 1024 / 1024, 1),
    }


def prueba_api(url: str, email: str, password: str, total: int, concurrencia: int) -> dict:
    respuesta = httpx.post(f"{url}/auth/login", json={"email": email, "password": password}, timeout=10)
    respuesta.raise_for_status()
    cabeceras = {"Authorization": f"Bearer {respuesta.json()['access_token']}"}

    latencias: list[float] = []
    errores = 0
    lock = threading.Lock()

    def peticion(_):
        nonlocal errores
        inicio = time.perf_counter()
        try:
            r = httpx.get(f"{url}/profiles", headers=cabeceras, timeout=30)
            ok = r.status_code == 200
        except httpx.HTTPError:
            ok = False
        with lock:
            latencias.append(time.perf_counter() - inicio)
            if not ok:
                errores += 1

    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrencia) as pool:
        list(pool.map(peticion, range(total)))
    duracion = time.perf_counter() - inicio

    return {
        "peticiones": total,
        "concurrencia": concurrencia,
        "errores": errores,
        "req_por_segundo": round(total / duracion, 1),
        "p50_ms": round(statistics.median(latencias) * 1000),
        "p95_ms": round(percentil(latencias, 95) * 1000),
        "max_ms": round(max(latencias) * 1000),
    }


def main() -> int:
    import os

    parser = argparse.ArgumentParser(description="Prueba de carga del pipeline y la API.")
    parser.add_argument("--cvs", type=int, nargs="+", default=[100])
    parser.add_argument("--api-url")
    parser.add_argument("--api-requests", type=int, default=200)
    parser.add_argument("--api-concurrency", type=int, default=10)
    args = parser.parse_args()

    profile_repository.crear_tablas()
    resultados = {"pipeline": [], "api": None}

    try:
        for cantidad in args.cvs:
            borrar_perfiles_de_prueba()
            resultado = prueba_pipeline(cantidad)
            resultados["pipeline"].append(resultado)
            print("pipeline", json.dumps(resultado), flush=True)

        if args.api_url:
            resultados["api"] = prueba_api(
                args.api_url,
                os.environ["DEMO_ADMIN_EMAIL"],
                os.environ["DEMO_ADMIN_PASSWORD"],
                args.api_requests,
                args.api_concurrency,
            )
            print("api", json.dumps(resultados["api"]), flush=True)
    finally:
        print(f"Perfiles de prueba borrados: {borrar_perfiles_de_prueba()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
