from unittest.mock import MagicMock, patch

from src.email_polling import (
    cargar_ids_procesados,
    ejecutar_polling_una_vez,
    guardar_ids_procesados,
)


def test_cargar_ids_sin_archivo_devuelve_vacio(tmp_path):
    ruta_estado = tmp_path / "polling_state.json"

    resultado = cargar_ids_procesados(ruta_estado)

    assert resultado == set()


def test_guardar_y_cargar_ids(tmp_path):
    ruta_estado = tmp_path / "polling_state.json"

    guardar_ids_procesados(
        ruta_estado,
        {"gmail-2", "gmail-1"},
    )

    resultado = cargar_ids_procesados(ruta_estado)

    assert resultado == {"gmail-1", "gmail-2"}


def test_estado_invalido_devuelve_vacio(tmp_path):
    ruta_estado = tmp_path / "polling_state.json"
    ruta_estado.write_text(
        "json-invalido",
        encoding="utf-8",
    )

    resultado = cargar_ids_procesados(ruta_estado)

    assert resultado == set()


def test_polling_procesa_solo_correos_nuevos(tmp_path):
    ruta_estado = tmp_path / "polling_state.json"

    guardar_ids_procesados(
        ruta_estado,
        {"gmail-antiguo"},
    )

    correo_antiguo = MagicMock()
    correo_antiguo.email_id = "gmail-antiguo"

    correo_nuevo = MagicMock()
    correo_nuevo.email_id = "gmail-nuevo"

    with patch(
        "src.email_polling.obtener_correos_gmail",
        return_value=[correo_nuevo, correo_antiguo],
    ), patch(
        "src.email_polling.procesar_lote",
        return_value={"procesados_exitosamente": 1},
    ) as mock_pipeline:

        resultado = ejecutar_polling_una_vez(
            carpeta_descargas=tmp_path / "gmail",
            carpeta_trabajo=tmp_path / "salida",
            ruta_estado=ruta_estado,
        )

    assert resultado == {
        "procesados_exitosamente": 1
    }

    mock_pipeline.assert_called_once()

    correos_enviados = (
        mock_pipeline.call_args.kwargs["correos"]
    )

    assert len(correos_enviados) == 1
    assert correos_enviados[0].email_id == "gmail-nuevo"

    assert cargar_ids_procesados(ruta_estado) == {
        "gmail-antiguo",
        "gmail-nuevo",
    }


def test_polling_sin_correos_nuevos_no_ejecuta_pipeline(
    tmp_path,
):
    ruta_estado = tmp_path / "polling_state.json"

    guardar_ids_procesados(
        ruta_estado,
        {"gmail-1"},
    )

    correo = MagicMock()
    correo.email_id = "gmail-1"

    with patch(
        "src.email_polling.obtener_correos_gmail",
        return_value=[correo],
    ), patch(
        "src.email_polling.procesar_lote",
    ) as mock_pipeline:

        resultado = ejecutar_polling_una_vez(
            carpeta_descargas=tmp_path / "gmail",
            carpeta_trabajo=tmp_path / "salida",
            ruta_estado=ruta_estado,
        )

    assert resultado is None
    mock_pipeline.assert_not_called()