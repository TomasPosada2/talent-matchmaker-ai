"""
HU-04: Estructuración del perfil en campos.

HU-05: Trazabilidad — cada campo con evidencia textual de origen.

Enfoque del Sprint 1: extracción basada en reglas (regex + detección de
encabezados de sección), NO hay ranking ni matching semántico todavía
("sin ingesta ni parsing confiables, el matching es humo" — ver Sprint Goal).

Principio clave: si el dato no está explícitamente en el texto, el campo
queda en None. Nunca se inventa información (anti-alucinación).

Sprint 4:
HU-16: heurística de nombre más robusta para plantillas atípicas.
"""

import re


EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

TELEFONO_REGEX = re.compile(
    r"(\+?\d[\d\s().-]{6,}\d)"
)

# BUG-02: un rango de años como "(2018-2021)" cae dentro del regex de arriba
# (misma forma: dígitos-guion-dígitos entre paréntesis). Se descarta
# explícitamente para no alucinar un teléfono a partir de fechas de
# experiencia laboral.
RANGO_ANIOS_REGEX = re.compile(
    r"^\(?\d{4}\s*-\s*\d{4}\)?$"
)


# Encabezados de sección típicos en CVs (español e inglés), en minúsculas.
ENCABEZADOS_EDUCACION = {
    "educación",
    "educacion",
    "formación académica",
    "formacion academica",
    "education",
}

ENCABEZADOS_EXPERIENCIA = {
    "experiencia",
    "experiencia laboral",
    "experience",
    "work experience",
}

ENCABEZADOS_HABILIDADES = {
    "habilidades",
    "skills",
    "competencias",
    "habilidades técnicas",
    "habilidades tecnicas",
}

TODOS_LOS_ENCABEZADOS = (
    ENCABEZADOS_EDUCACION
    | ENCABEZADOS_EXPERIENCIA
    | ENCABEZADOS_HABILIDADES
)


def _campo(valor, evidencia):
    """Construye el objeto {"valor": ..., "evidencia": ...} del schema."""
    return {"valor": valor, "evidencia": evidencia}


def _campo_vacio():
    return _campo(None, None)


def _es_encabezado(
    linea: str,
    conjunto_encabezados: set[str],
) -> bool:
    linea_normalizada = linea.strip().lower().rstrip(":")
    return linea_normalizada in conjunto_encabezados


def _extraer_seccion(
    lineas: list[str],
    encabezados_seccion: set[str],
) -> tuple[str | None, str | None]:
    """
    Busca un encabezado de sección y devuelve todo el texto hasta el
    siguiente encabezado conocido (de cualquier sección) o el final
    del documento.
    """
    for i, linea in enumerate(lineas):
        if _es_encabezado(linea, encabezados_seccion):
            contenido = []

            for siguiente in lineas[i + 1:]:
                if _es_encabezado(
                    siguiente,
                    TODOS_LOS_ENCABEZADOS,
                ):
                    break

                contenido.append(siguiente)

            if contenido:
                texto = "\n".join(contenido)
                return texto, texto

            return None, None

    return None, None


def _extraer_nombre(
    lineas: list[str],
) -> tuple[str | None, str | None]:
    """
    HU-16: extrae el nombre del candidato usando una heurística más
    tolerante a plantillas atípicas.

    A diferencia de la implementación inicial, no se limita a las
    primeras tres líneas. Busca dentro de las primeras diez líneas y
    descarta títulos del documento, datos de contacto, encabezados,
    URLs, números y otros contenidos que claramente no corresponden
    a un nombre.
    """

    # Textos frecuentes que aparecen antes del nombre en CVs.
    etiquetas_descartadas = {
        "curriculum vitae",
        "currículum vitae",
        "cv",
        "resume",
        "résumé",
        "hoja de vida",
        "perfil",
        "profile",
    }

    # Prefijos frecuentes de información de contacto.
    prefijos_contacto = (
        "tel:",
        "teléfono:",
        "telefono:",
        "phone:",
        "email:",
        "correo:",
        "e-mail:",
        "dirección:",
        "direccion:",
        "address:",
        "linkedin:",
        "github:",
    )

    # Revisar hasta las primeras diez líneas permite soportar plantillas
    # donde el nombre no aparece necesariamente al principio.
    for linea in lineas[:10]:
        candidato = linea.strip()

        if not candidato:
            continue

        candidato_normalizado = candidato.lower().rstrip(":")

        # Descartar títulos genéricos del documento.
        if candidato_normalizado in etiquetas_descartadas:
            continue

        # Descartar emails y teléfonos.
        if EMAIL_REGEX.search(candidato):
            continue

        if TELEFONO_REGEX.search(candidato):
            continue

        # Descartar líneas identificadas como datos de contacto.
        if candidato_normalizado.startswith(prefijos_contacto):
            continue

        # Descartar encabezados conocidos.
        if _es_encabezado(
            candidato,
            TODOS_LOS_ENCABEZADOS,
        ):
            continue

        # Un nombre razonable normalmente tiene entre 2 y 6 palabras.
        palabras = candidato.split()

        if not 2 <= len(palabras) <= 6:
            continue

        # Un nombre no debería contener números.
        if any(char.isdigit() for char in candidato):
            continue

        # Descartar URLs.
        if "http://" in candidato_normalizado:
            continue

        if "https://" in candidato_normalizado:
            continue

        if "www." in candidato_normalizado:
            continue

        # Las palabras del nombre deben estar formadas principalmente
        # por letras. Se permiten tildes, ñ, guiones y apóstrofes.
        nombre_valido = all(
            re.fullmatch(
                r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'’-]+",
                palabra,
            )
            for palabra in palabras
        )

        if not nombre_valido:
            continue

        # Mantener trazabilidad:
        # la evidencia es exactamente el texto encontrado en el CV.
        return candidato, candidato

    # Si no existe evidencia suficiente, no inventamos un nombre.
    return None, None


def _extraer_email(
    texto_completo: str,
) -> tuple[str | None, str | None]:
    match = EMAIL_REGEX.search(texto_completo)

    if match:
        return match.group(0), match.group(0)

    return None, None


def _extraer_telefono(
    texto_completo: str,
) -> tuple[str | None, str | None]:
    for match in TELEFONO_REGEX.finditer(texto_completo):
        valor = match.group(0).strip()

        if RANGO_ANIOS_REGEX.match(valor):
            continue

        return valor, valor

    return None, None


def estructurar_perfil(
    email_id: str,
    archivo_origen: str,
    texto_completo: str,
    lineas: list[str],
) -> dict:
    """
    Construye el perfil estructurado con evidencia textual,
    listo para validar contra el schema.
    """

    nombre_valor, nombre_evidencia = _extraer_nombre(lineas)

    email_valor, email_evidencia = _extraer_email(
        texto_completo
    )

    tel_valor, tel_evidencia = _extraer_telefono(
        texto_completo
    )

    edu_valor, edu_evidencia = _extraer_seccion(
        lineas,
        ENCABEZADOS_EDUCACION,
    )

    exp_valor, exp_evidencia = _extraer_seccion(
        lineas,
        ENCABEZADOS_EXPERIENCIA,
    )

    hab_valor, hab_evidencia = _extraer_seccion(
        lineas,
        ENCABEZADOS_HABILIDADES,
    )

    perfil = {
        "email_id": email_id,
        "archivo_origen": archivo_origen,
        "nombre": _campo(
            nombre_valor,
            nombre_evidencia,
        ),
        "contacto": {
            "email": _campo(
                email_valor,
                email_evidencia,
            ),
            "telefono": _campo(
                tel_valor,
                tel_evidencia,
            ),
        },
        "educacion": _campo(
            edu_valor,
            edu_evidencia,
        ),
        "experiencia": _campo(
            exp_valor,
            exp_evidencia,
        ),
        "habilidades": _campo(
            hab_valor,
            hab_evidencia,
        ),
    }

    return perfil