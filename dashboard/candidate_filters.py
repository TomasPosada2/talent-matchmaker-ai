"""Funciones de búsqueda y filtrado de candidatos."""


def obtener_valor(perfil: dict, campo: str):
    """Extrae el valor de un campo estructurado."""
    dato = perfil.get(campo, {})
    if isinstance(dato, dict):
        return dato.get("valor")
    return dato


def convertir_a_texto(valor) -> str:
    """Convierte cadenas, listas y valores vacíos en texto."""
    if valor is None:
        return ""
    if isinstance(valor, list):
        return ", ".join(convertir_a_texto(item) for item in valor)
    return str(valor)


def filtrar_candidatos(
    perfiles: list[dict],
    nombre: str = "",
    habilidad: str = "",
    experiencia: str = "",
) -> list[dict]:
    """Filtra candidatos por coincidencias de texto, sin distinguir mayúsculas."""
    nombre = nombre.strip().casefold()
    habilidad = habilidad.strip().casefold()
    experiencia = experiencia.strip().casefold()

    resultados = []

    for perfil in perfiles:
        if not isinstance(perfil, dict):
            continue

        texto_nombre = convertir_a_texto(
            obtener_valor(perfil, "nombre")
        ).casefold()

        texto_habilidades = convertir_a_texto(
            obtener_valor(perfil, "habilidades")
        ).casefold()

        texto_experiencia = convertir_a_texto(
            obtener_valor(perfil, "experiencia")
        ).casefold()

        if nombre and nombre not in texto_nombre:
            continue

        if habilidad and habilidad not in texto_habilidades:
            continue

        if experiencia and experiencia not in texto_experiencia:
            continue

        resultados.append(perfil)

    return resultados


def preparar_tabla(perfiles: list[dict]) -> list[dict]:
    """Prepara columnas legibles para la tabla de Streamlit."""
    filas = []

    for perfil in perfiles:
        contacto = perfil.get("contacto") or {}

        if not isinstance(contacto, dict):
            contacto = {}

        filas.append({
            "Nombre": convertir_a_texto(
                obtener_valor(perfil, "nombre")
            ),
            "Correo": convertir_a_texto(
                obtener_valor(contacto, "email")
            ),
            "Experiencia": convertir_a_texto(
                obtener_valor(perfil, "experiencia")
            ),
            "Habilidades": convertir_a_texto(
                obtener_valor(perfil, "habilidades")
            ),
            "Educación": convertir_a_texto(
                obtener_valor(perfil, "educacion")
            ),
            "ID": perfil.get("email_id", ""),
        })

    return filas
