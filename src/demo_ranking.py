
"""
Motor de ranking local para demostraciones.

No utiliza inteligencia artificial ni servicios externos.
Los resultados son orientativos y no sustituyen una
evaluación profesional de los candidatos.
"""

import re
import unicodedata

PALABRAS_GENERICAS = {
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "los",
    "para",
    "por",
    "un",
    "una",
    "y",
    "experiencia",
    "conocimiento",
    "conocimientos",
    "manejo",
    "dominio",
    "habilidad",
    "habilidades",
    "nivel",
    "avanzado",
    "intermedio",
    "basico",
}


def normalizar(texto):
    """Normaliza un texto para comparar términos."""
    texto = unicodedata.normalize(
        "NFKD",
        str(texto or ""),
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    return texto.casefold()


def extraer_terminos(requisito):
    """Extrae términos relevantes del requisito."""
    palabras = re.findall(
        r"[a-z0-9+#.]+",
        normalizar(requisito),
    )

    return [
        palabra
        for palabra in palabras
        if palabra not in PALABRAS_GENERICAS
        and len(palabra) >= 2
    ]


def obtener_evidencias(perfil):
    """Obtiene únicamente las evidencias trazadas del perfil."""
    evidencias = []

    for campo in (
        "nombre",
        "educacion",
        "experiencia",
        "habilidades",
    ):
        dato = perfil.get(campo)

        if not isinstance(dato, dict):
            continue

        evidencia = dato.get("evidencia")

        if isinstance(evidencia, str) and evidencia.strip():
            evidencias.append(
                {
                    "campo": campo,
                    "texto": evidencia.strip(),
                }
            )

    return evidencias


def contiene_termino(texto, termino):
    """Busca un término completo, no una subcadena."""
    patron = (
        r"(?<!\w)"
        + re.escape(termino)
        + r"(?!\w)"
    )

    return bool(
        re.search(
            patron,
            normalizar(texto),
        )
    )


def evaluar_requisito(perfil, requisito):
    """
    Busca todos los términos relevantes del requisito
    dentro de una misma evidencia.
    """
    terminos = extraer_terminos(requisito)

    if not terminos:
        return None

    for evidencia in obtener_evidencias(perfil):
        texto = evidencia["texto"]

        if all(
            contiene_termino(texto, termino)
            for termino in terminos
        ):
            return texto

    return None


def generar_ranking_demo(vacante, perfiles):
    """
    Genera un ranking determinista basado en coincidencias
    textuales de evidencias existentes.
    """
    requisitos = vacante.get("requisitos", [])

    if not isinstance(requisitos, list):
        requisitos = []

    requisitos = [
        requisito.strip()
        for requisito in requisitos
        if isinstance(requisito, str)
        and requisito.strip()
    ]

    ranking = []

    for perfil in perfiles:
        if not isinstance(perfil, dict):
            continue

        justificacion = []
        requisitos_sin_evidencia = []

        for requisito in requisitos:
            evidencia = evaluar_requisito(
                perfil,
                requisito,
            )

            if evidencia is not None:
                justificacion.append(
                    {
                        "requisito": requisito,
                        "evidencia": evidencia,
                    }
                )
            else:
                requisitos_sin_evidencia.append(
                    requisito
                )

        total = len(requisitos)
        encontrados = len(justificacion)

        proporcion = (
            encontrados / total
            if total
            else 0
        )

        ranking.append(
            {
                "email_id": str(
                    perfil.get("email_id", "")
                ),
                "puntaje": round(
                    proporcion * 100,
                    2,
                ),
                "confianza": round(
                    proporcion,
                    2,
                ),
                "razon_confianza": (
                    f"Modo demostración: {encontrados} "
                    f"de {total} requisitos tienen "
                    "coincidencias textuales en "
                    "las evidencias registradas. "
                    "No representa una evaluación "
                    "realizada por inteligencia artificial."
                ),
                "justificacion": justificacion,
                "requisitos_sin_evidencia": (
                    requisitos_sin_evidencia
                ),
            }
        )

    ranking.sort(
        key=lambda candidato: candidato["puntaje"],
        reverse=True,
    )

    return {
        "ranking": ranking,
        "metricas": {
            "modo": "demostracion",
            "total_candidatos": len(ranking),
            "total_requisitos": len(requisitos),
        },
        "notificacion_enviada": False,
        "modo_demostracion": True,
    }
