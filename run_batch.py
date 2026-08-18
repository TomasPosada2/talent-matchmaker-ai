"""
Punto de entrada del Sprint 1.

Uso:
    python run_batch.py

Corre el pipeline completo (HU-01 a HU-08) sobre la bandeja simulada en
data/inbox_simulado/ y deja los resultados en data/salida/:
    - reporte_lote.json  -> métricas y detalle de fallos (HU-07)
    - perfiles.json       -> perfiles estructurados en JSON válido (HU-06)
"""

from pathlib import Path

from src.pipeline import procesar_lote

BASE_DIR = Path(__file__).resolve().parent
INBOX_DIR = BASE_DIR / "data" / "inbox_simulado"
CARPETA_TRABAJO = BASE_DIR / "data" / "salida"


def main():
    reporte = procesar_lote(INBOX_DIR, CARPETA_TRABAJO)

    print("\n=== REPORTE SPRINT 1 ===")
    print(f"Total correos en bandeja:        {reporte['total_correos_en_bandeja']}")
    print(f"Candidatos a procesar:           {reporte['candidatos_a_procesar']}")
    print(f"Procesados con éxito:            {reporte['procesados_exitosamente']}")
    print(f"Fallidos:                        {reporte['fallidos']}")
    print(f"Ignorados (sin adjunto):         {reporte['ignorados_sin_adjunto']}")
    print(f"Descartados (formato inválido):  {reporte['descartados_formato_no_soportado']}")
    print(f"Tasa de éxito:                   {reporte['tasa_exito'] * 100:.1f}%")

    if reporte["detalle_fallidos"]:
        print("\nCasos fallidos:")
        for f in reporte["detalle_fallidos"]:
            print(f"  - {f['email_id']}: {f['motivo']}")

    print(f"\nResultados guardados en: {CARPETA_TRABAJO}")


if __name__ == "__main__":
    main()
