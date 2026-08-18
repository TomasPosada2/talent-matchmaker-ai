"""
Pruebas unitarias mínimas para el Sprint 1 (Definition of Done).
Ejecutar con: pytest tests/ -v   (desde la raíz del proyecto)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document

from src import email_detector, attachment_handler, text_extractor, profile_structurer, schema


def test_deteccion_correo_sin_adjunto(tmp_path):
    carpeta = tmp_path / "email_x"
    carpeta.mkdir()
    (carpeta / "metadata.json").write_text('{"attachments": []}', encoding="utf-8")
    resultado = email_detector.detectar_correo(carpeta)
    assert resultado.estado == "ignorado_sin_adjunto"


def test_deteccion_correo_formato_no_soportado(tmp_path):
    carpeta = tmp_path / "email_y"
    carpeta.mkdir()
    (carpeta / "foto.jpg").write_bytes(b"x")
    (carpeta / "metadata.json").write_text('{"attachments": ["foto.jpg"]}', encoding="utf-8")
    resultado = email_detector.detectar_correo(carpeta)
    assert resultado.estado == "descartado_formato_no_soportado"


def test_deteccion_correo_valido(tmp_path):
    carpeta = tmp_path / "email_z"
    carpeta.mkdir()
    (carpeta / "cv.docx").write_bytes(b"contenido")
    (carpeta / "metadata.json").write_text('{"attachments": ["cv.docx"]}', encoding="utf-8")
    resultado = email_detector.detectar_correo(carpeta)
    assert resultado.estado == "candidato_a_procesar"
    assert resultado.adjunto_valido.name == "cv.docx"


def test_extraccion_adjunto_vacio_es_invalido(tmp_path):
    archivo_vacio = tmp_path / "cv.docx"
    archivo_vacio.write_bytes(b"")
    resultado = attachment_handler.extraer_adjunto("email_1", archivo_vacio, tmp_path / "salida")
    assert resultado.valido is False


def test_extraccion_texto_docx(tmp_path):
    doc = Document()
    doc.add_paragraph("Juan Pérez")
    doc.add_paragraph("juan@example.com")
    doc.add_paragraph("Habilidades")
    doc.add_paragraph("Python, SQL")
    ruta = tmp_path / "cv.docx"
    doc.save(ruta)

    resultado = text_extractor.extraer_texto("email_1", ruta)
    assert resultado.procesable is True
    assert "juan@example.com" in resultado.texto_completo


def test_docx_vacio_no_procesable(tmp_path):
    doc = Document()
    ruta = tmp_path / "cv_vacio.docx"
    doc.save(ruta)
    resultado = text_extractor.extraer_texto("email_1", ruta)
    assert resultado.procesable is False


def test_estructuracion_perfil_no_alucina_campos_faltantes():
    lineas = ["Ana Gómez", "ana@example.com"]
    texto_completo = "\n".join(lineas)
    perfil = profile_structurer.estructurar_perfil("email_1", "cv.docx", texto_completo, lineas)

    assert perfil["nombre"]["valor"] == "Ana Gómez"
    assert perfil["contacto"]["email"]["valor"] == "ana@example.com"
    # No hay sección de educación/experiencia/habilidades en el texto -> deben quedar en None
    assert perfil["educacion"]["valor"] is None
    assert perfil["educacion"]["evidencia"] is None
    assert perfil["experiencia"]["valor"] is None
    assert perfil["habilidades"]["valor"] is None


def test_perfil_valido_contra_schema():
    lineas = ["Carlos Ruiz", "carlos@example.com", "Habilidades", "Python"]
    texto_completo = "\n".join(lineas)
    perfil = profile_structurer.estructurar_perfil("email_1", "cv.docx", texto_completo, lineas)
    es_valido, error = schema.validar_perfil(perfil)
    assert es_valido, error


def test_perfil_invalido_es_rechazado():
    perfil_malformado = {"email_id": "x"}  # faltan campos requeridos
    es_valido, error = schema.validar_perfil(perfil_malformado)
    assert es_valido is False
    assert error is not None
