
"""Pruebas del motor de ranking de demostración."""

from src.demo_ranking import generar_ranking_demo


def crear_perfil(email_id, evidencia):
    return {
        "email_id": email_id,
        "nombre": {
            "valor": "Candidato",
            "evidencia": "",
        },
        "educacion": {
            "valor": "",
            "evidencia": "",
        },
        "experiencia": {
            "valor": "",
            "evidencia": "",
        },
        "habilidades": {
            "valor": "",
            "evidencia": evidencia,
        },
    }


def test_ranking_ordena_por_puntaje():
    vacante = {
        "cargo": "Analista de datos",
        "requisitos": ["Python", "SQL"],
    }

    perfiles = [
        crear_perfil("uno", "Experiencia con Python"),
        crear_perfil("dos", "Experiencia con Python y SQL"),
    ]

    resultado = generar_ranking_demo(vacante, perfiles)
    ranking = resultado["ranking"]

    assert ranking[0]["email_id"] == "dos"
    assert ranking[0]["puntaje"] == 100
    assert ranking[1]["puntaje"] == 50


def test_no_inventa_evidencia():
    vacante = {
        "requisitos": ["Python"],
    }

    perfiles = [
        crear_perfil("uno", "Experiencia en Excel"),
    ]

    resultado = generar_ranking_demo(vacante, perfiles)
    candidato = resultado["ranking"][0]

    assert candidato["puntaje"] == 0
    assert candidato["justificacion"] == []
    assert candidato["requisitos_sin_evidencia"] == ["Python"]


def test_evidencia_proviene_del_perfil():
    evidencia = "Desarrollo de aplicaciones con Python"

    vacante = {
        "requisitos": ["Python"],
    }

    perfiles = [
        crear_perfil("uno", evidencia),
    ]

    resultado = generar_ranking_demo(vacante, perfiles)
    candidato = resultado["ranking"][0]

    assert candidato["justificacion"][0]["evidencia"] == evidencia


def test_resultado_identificado_como_demostracion():
    resultado = generar_ranking_demo(
        {"requisitos": ["SQL"]},
        [crear_perfil("uno", "SQL")],
    )

    assert resultado["modo_demostracion"] is True
    assert resultado["metricas"]["modo"] == "demostracion"
    assert resultado["notificacion_enviada"] is False


def test_sin_requisitos_no_asigna_puntaje():
    resultado = generar_ranking_demo(
        {"requisitos": []},
        [crear_perfil("uno", "Python y SQL")],
    )

    assert resultado["ranking"][0]["puntaje"] == 0
    assert resultado["ranking"][0]["confianza"] == 0
