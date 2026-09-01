"""
NO USAR EN VIVO PARA LA SPRINT REVIEW: dentro de un sandbox de desarrollo de
Claude Code, este script dio resultados distintos en corridas seguidas sin
cambiar nada (una vez ProcessError capturado correctamente, otra vez un
ranking real) porque el proceso a veces hereda el canal de control de la
sesión de Claude Code actual en vez de correr aislado. Sirve para verificar
el manejo de errores en desarrollo, pero el resultado no es reproducible y
no representa el comportamiento en un entorno de despliegue limpio -> no es
evidencia confiable para una demo en vivo frente al profesor.

Demo original (Acto 3): muestra que cuando el framework del agente falla
(sin el CLI `claude` instalado / sin credenciales), el fallo se captura
limpiamente en ResultadoAgente.error en vez de tumbar el proceso.

Uso: python scripts/demo_agent_error_handling.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import agent

VACANTE = {"cargo": "Backend Developer", "requisitos": ["Python"]}
PERFILES = [{
    "email_id": "email_1",
    "nombre": {"valor": "Ana", "evidencia": "Ana"},
    "contacto": {"email": {"valor": "ana@example.com", "evidencia": "ana@example.com"},
                 "telefono": {"valor": None, "evidencia": None}},
    "educacion": {"valor": None, "evidencia": None},
    "experiencia": {"valor": None, "evidencia": None},
    "habilidades": {"valor": "Python, SQL", "evidencia": "Python, SQL"},
}]

if __name__ == "__main__":
    print("Corriendo el agente sin credenciales/CLI configurados...\n")
    resultado = agent.rankear_candidatos(VACANTE, PERFILES)

    print("ranking:", resultado.ranking)
    print("error:  ", resultado.error)
    print("\n-> El proceso no se colgó ni crasheó: el fallo del framework")
    print("   quedó capturado en ResultadoAgente.error (HU-14).")

    sys.stdout.flush()
    os._exit(0)  # evita el hang de limpieza del transporte del SDK
