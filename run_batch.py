"""
Punto de entrada para procesar candidatos desde una bandeja real de Gmail.

Sprint 5 - Issue #11:
    Gmail -> descarga de adjuntos -> pipeline existente.

Los correos obtenidos desde Gmail se convierten en CorreoDetectado,
manteniendo intactas las etapas posteriores del pipeline.
"""

from pathlib import Path

from src.gmail_inbox import obtener_correos_gmail
from src.pipeline import procesar_lote


BASE_DIR = Path(__file__).resolve().parent
CARPETA_TRABAJO = BASE_DIR / "data" / "salida"
CARPETA_GMAIL = CARPETA_TRABAJO / "gmail"


def main():
    print("Conectando con Gmail...")

    correos = obtener_correos_gmail(
        carpeta_descargas=CARPETA_GMAIL,
        max_resultados=50,
    )

    print(f"Correos obtenidos de Gmail: {len(correos)}")

    reporte = procesar_lote(
        inbox_dir=None,
        carpeta_trabajo=CARPETA_TRABAJO,
        correos=correos,
    )

    print("\n=== REPORTE DE PROCESAMIENTO ===")
    print(
        f"Total correos en bandeja:        "
        f"{reporte['total_correos_en_bandeja']}"
    )
    print(
        f"Candidatos a procesar:           "
        f"{reporte['candidatos_a_procesar']}"
    )
    print(
        f"Procesados con éxito:            "
        f"{reporte['procesados_exitosamente']}"
    )
    print(
        f"Fallidos:                        "
        f"{reporte['fallidos']}"
    )
    print(
        f"Ignorados (sin adjunto):         "
        f"{reporte['ignorados_sin_adjunto']}"
    )
    print(
        f"Descartados (formato inválido):  "
        f"{reporte['descartados_formato_no_soportado']}"
    )
    print(
        f"Tasa de éxito:                   "
        f"{reporte['tasa_exito'] * 100:.1f}%"
    )

    if reporte["detalle_fallidos"]:
        print("\nCasos fallidos:")
        for fallo in reporte["detalle_fallidos"]:
            print(
                f"  - {fallo['email_id']}: "
                f"{fallo['motivo']}"
            )

    print(f"\nResultados guardados en: {CARPETA_TRABAJO}")


if __name__ == "__main__":
    main()