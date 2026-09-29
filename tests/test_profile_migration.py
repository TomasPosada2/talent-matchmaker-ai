import json
from unittest.mock import patch

from scripts.migrate_profiles_to_db import (
    cargar_perfiles_archivo,
    descubrir_archivos,
    migrar_perfiles,
)


def perfil_valido(email_id="email-001"):
    return {
        "email_id": email_id,
        "archivo_origen": "candidato.pdf",
        "nombre": {
            "valor": "Ana Torres",
            "evidencia": "Ana Torres",
        },
        "contacto": {
            "email": {
                "valor": "ana@example.com",
                "evidencia": "ana@example.com",
            },
            "telefono": {
                "valor": "3001234567",
                "evidencia": "3001234567",
            },
        },
        "educacion": {
            "valor": ["Ingeniería de Sistemas"],
            "evidencia": ["Ingeniería de Sistemas"],
        },
        "experiencia": {
            "valor": ["Backend Developer"],
            "evidencia": ["Backend Developer"],
        },
        "habilidades": {
            "valor": ["Python", "SQL"],
            "evidencia": ["Python", "SQL"],
        },
    }


def test_cargar_lista_de_perfiles(tmp_path):
    ruta = tmp_path / "perfiles.json"

    perfiles = [
        perfil_valido("email-001"),
        perfil_valido("email-002"),
    ]

    ruta.write_text(
        json.dumps(perfiles, ensure_ascii=False),
        encoding="utf-8",
    )

    resultado = cargar_perfiles_archivo(ruta)

    assert len(resultado) == 2
    assert resultado[0]["email_id"] == "email-001"
    assert resultado[1]["email_id"] == "email-002"


def test_cargar_perfiles_desde_reporte(tmp_path):
    ruta = tmp_path / "reporte_lote.json"

    datos = {
        "total_correos_en_bandeja": 1,
        "perfiles": [perfil_valido()],
    }

    ruta.write_text(
        json.dumps(datos, ensure_ascii=False),
        encoding="utf-8",
    )

    resultado = cargar_perfiles_archivo(ruta)

    assert len(resultado) == 1
    assert resultado[0]["email_id"] == "email-001"


def test_cargar_perfil_individual(tmp_path):
    ruta = tmp_path / "perfil.json"

    ruta.write_text(
        json.dumps(perfil_valido(), ensure_ascii=False),
        encoding="utf-8",
    )

    resultado = cargar_perfiles_archivo(ruta)

    assert len(resultado) == 1
    assert resultado[0]["email_id"] == "email-001"


def test_descubrir_json_en_directorio(tmp_path):
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.json").write_text("[]", encoding="utf-8")
    (tmp_path / "ignorar.txt").write_text("texto", encoding="utf-8")

    resultado = descubrir_archivos(tmp_path)

    assert len(resultado) == 2
    assert all(ruta.suffix == ".json" for ruta in resultado)


def test_migrar_perfiles_validos(tmp_path):
    ruta = tmp_path / "perfiles.json"

    perfiles = [
        perfil_valido("email-001"),
        perfil_valido("email-002"),
    ]

    ruta.write_text(
        json.dumps(perfiles, ensure_ascii=False),
        encoding="utf-8",
    )

    with (
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.crear_tablas"
        ) as crear_tablas,
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.guardar_perfil"
        ) as guardar_perfil,
    ):
        resumen = migrar_perfiles(ruta)

    crear_tablas.assert_called_once()
    assert guardar_perfil.call_count == 2

    assert resumen["archivos_encontrados"] == 1
    assert resumen["perfiles_encontrados"] == 2
    assert resumen["migrados"] == 2
    assert resumen["invalidos"] == 0
    assert resumen["errores_archivo"] == 0


def test_perfil_invalido_no_se_migra(tmp_path):
    ruta = tmp_path / "perfiles.json"

    perfil_invalido = {
        "email_id": "email-invalido",
        "archivo_origen": "invalido.pdf",
    }

    ruta.write_text(
        json.dumps([perfil_invalido]),
        encoding="utf-8",
    )

    with (
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.crear_tablas"
        ),
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.guardar_perfil"
        ) as guardar_perfil,
    ):
        resumen = migrar_perfiles(ruta)

    guardar_perfil.assert_not_called()

    assert resumen["perfiles_encontrados"] == 1
    assert resumen["migrados"] == 0
    assert resumen["invalidos"] == 1


def test_json_corrupto_se_reporta_sin_detener_migracion(tmp_path):
    archivo_malo = tmp_path / "a_corrupto.json"
    archivo_bueno = tmp_path / "b_perfiles.json"

    archivo_malo.write_text(
        "{esto no es json",
        encoding="utf-8",
    )

    archivo_bueno.write_text(
        json.dumps([perfil_valido()], ensure_ascii=False),
        encoding="utf-8",
    )

    with (
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.crear_tablas"
        ),
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.guardar_perfil"
        ) as guardar_perfil,
    ):
        resumen = migrar_perfiles(tmp_path)

    guardar_perfil.assert_called_once()

    assert resumen["archivos_encontrados"] == 2
    assert resumen["perfiles_encontrados"] == 1
    assert resumen["migrados"] == 1
    assert resumen["errores_archivo"] == 1
    assert len(resumen["detalle_errores"]) == 1


def test_error_postgresql_se_reporta(tmp_path):
    ruta = tmp_path / "perfiles.json"

    ruta.write_text(
        json.dumps([perfil_valido()], ensure_ascii=False),
        encoding="utf-8",
    )

    with (
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.crear_tablas"
        ),
        patch(
            "scripts.migrate_profiles_to_db."
            "profile_repository.guardar_perfil",
            side_effect=RuntimeError("DB no disponible"),
        ),
    ):
        resumen = migrar_perfiles(ruta)

    assert resumen["perfiles_encontrados"] == 1
    assert resumen["migrados"] == 0

    assert len(resumen["detalle_errores"]) == 1
    assert "PostgreSQL" in resumen["detalle_errores"][0]["error"]




    def test_cargar_json_utf8_con_bom(tmp_path):
                ruta = tmp_path / "perfiles_bom.json"

                contenido = json.dumps(
                [perfil_valido()],
                 ensure_ascii=False,
                    )

                ruta.write_text(
                    contenido,
             encoding="utf-8-sig",
                 )

                resultado = cargar_perfiles_archivo(ruta)

                assert len(resultado) == 1
                assert resultado[0]["email_id"] == "email-001"
def test_cargar_json_utf8_con_bom(tmp_path):
    ruta = tmp_path / "perfiles_bom.json"

    contenido = json.dumps(
        [perfil_valido()],
        ensure_ascii=False,
    )

    ruta.write_text(
        contenido,
        encoding="utf-8-sig",
    )

    resultado = cargar_perfiles_archivo(ruta)

    assert len(resultado) == 1
    assert resultado[0]["email_id"] == "email-001"
