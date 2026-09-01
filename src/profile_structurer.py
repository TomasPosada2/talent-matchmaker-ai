"""
HU-04: Estructuración del perfil en campos.
HU-05: Trazabilidad — cada campo con evidencia textual de origen.

Enfoque del Sprint 1: extracción basada en reglas (regex + detección de
encabezados de sección), NO hay ranking ni matching semántico todavía
("sin ingesta ni parsing confiables, el matching es humo" — ver Sprint Goal).

Principio clave: si el dato no está explícitamente en el texto, el campo
queda en None. Nunca se inventa información (anti-alucinación).
"""

import re

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TELEFONO_REGEX = re.compile(r"(\+?\d[\d\s().-]{6,}\d)")
# BUG-02: un rango de años como "(2018-2021)" cae dentro del regex de arriba
# (misma forma: dígitos-guion-dígitos entre paréntesis). Se descarta explícitamente
# para no alucinar un teléfono a partir de fechas de experiencia laboral.
RANGO_ANIOS_REGEX = re.compile(r"^\(?\d{4}\s*-\s*\d{4}\)?$")

# Encabezados de sección típicos en CVs (español e inglés), en minúsculas.
ENCABEZADOS_EDUCACION = {"educación", "educacion", "formación académica", "formacion academica", "education"}
ENCABEZADOS_EXPERIENCIA = {"experiencia", "experiencia laboral", "experience", "work experience"}
ENCABEZADOS_HABILIDADES = {"habilidades", "skills", "competencias", "habilidades técnicas", "habilidades tecnicas"}
TODOS_LOS_ENCABEZADOS = ENCABEZADOS_EDUCACION | ENCABEZADOS_EXPERIENCIA | ENCABEZADOS_HABILIDADES


def _campo(valor, evidencia):
    """Construye el objeto {"valor": ..., "evidencia": ...} del schema."""
    return {"valor": valor, "evidencia": evidencia}


def _campo_vacio():
    return _campo(None, None)


def _es_encabezado(linea: str, conjunto_encabezados: set[str]) -> bool:
    linea_normalizada = linea.strip().lower().rstrip(":")
    return linea_normalizada in conjunto_encabezados


def _extraer_seccion(lineas: list[str], encabezados_seccion: set[str]) -> tuple[str | None, str | None]:
    """
    Busca un encabezado de sección y devuelve todo el texto hasta el
    siguiente encabezado conocido (de cualquier sección) o el final del documento.
    """
    for i, linea in enumerate(lineas):
        if _es_encabezado(linea, encabezados_seccion):
            contenido = []
            for siguiente in lineas[i + 1:]:
                if _es_encabezado(siguiente, TODOS_LOS_ENCABEZADOS):
                    break
                contenido.append(siguiente)
            if contenido:
                texto = "\n".join(contenido)
                return texto, texto
            return None, None
    return None, None


def _extraer_nombre(lineas: list[str]) -> tuple[str | None, str | None]:
    """
    Heurística MVP: el nombre suele ser la primera línea no vacía del
    documento, siempre que no parezca un email/teléfono/encabezado.
    """
    for linea in lineas[:3]:
        candidato = linea.strip()
        if not candidato:
            continue
        if EMAIL_REGEX.search(candidato) or TELEFONO_REGEX.search(candidato):
            continue
        if _es_encabezado(candidato, TODOS_LOS_ENCABEZADOS):
            continue
        # Evitar líneas demasiado largas (probablemente no es un nombre)
        if len(candidato) <= 60:
            return candidato, candidato
    return None, None


def _extraer_email(texto_completo: str) -> tuple[str | None, str | None]:
    match = EMAIL_REGEX.search(texto_completo)
    if match:
        return match.group(0), match.group(0)
    return None, None


def _extraer_telefono(texto_completo: str) -> tuple[str | None, str | None]:
    for match in TELEFONO_REGEX.finditer(texto_completo):
        valor = match.group(0).strip()
        if RANGO_ANIOS_REGEX.match(valor):
            continue
        return valor, valor
    return None, None


def estructurar_perfil(email_id: str, archivo_origen: str, texto_completo: str, lineas: list[str]) -> dict:
    """Construye el perfil estructurado con evidencia textual, listo para validar contra el schema."""
    nombre_valor, nombre_evidencia = _extraer_nombre(lineas)
    email_valor, email_evidencia = _extraer_email(texto_completo)
    tel_valor, tel_evidencia = _extraer_telefono(texto_completo)
    edu_valor, edu_evidencia = _extraer_seccion(lineas, ENCABEZADOS_EDUCACION)
    exp_valor, exp_evidencia = _extraer_seccion(lineas, ENCABEZADOS_EXPERIENCIA)
    hab_valor, hab_evidencia = _extraer_seccion(lineas, ENCABEZADOS_HABILIDADES)

    perfil = {
        "email_id": email_id,
        "archivo_origen": archivo_origen,
        "nombre": _campo(nombre_valor, nombre_evidencia),
        "contacto": {
            "email": _campo(email_valor, email_evidencia),
            "telefono": _campo(tel_valor, tel_evidencia),
        },
        "educacion": _campo(edu_valor, edu_evidencia),
        "experiencia": _campo(exp_valor, exp_evidencia),
        "habilidades": _campo(hab_valor, hab_evidencia),
    }
    return perfil
