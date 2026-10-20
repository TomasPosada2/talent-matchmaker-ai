import os
import time

import pytest
from fastapi.testclient import TestClient

from src import api, privacy

client = TestClient(api.app)


def test_enmascarar_email():
    assert privacy.enmascarar_email("maria.torres@empresa.com") == "m***@empresa.com"
    assert privacy.enmascarar_email(None) == "***"
    assert privacy.enmascarar_email("sin-arroba") == "***"


def test_retencion_desde_entorno(monkeypatch):
    monkeypatch.setenv("RETENTION_DAYS", "30")
    assert privacy.obtener_retencion_dias() == 30

    monkeypatch.setenv("RETENTION_DAYS", "0")
    with pytest.raises(ValueError):
        privacy.obtener_retencion_dias()


def test_eliminar_archivos_candidato(tmp_path):
    adjuntos = tmp_path / "adjuntos_extraidos"
    adjuntos.mkdir()
    (adjuntos / "email_001__cv.pdf").write_bytes(b"cv")
    (adjuntos / "email_002__cv.pdf").write_bytes(b"otro")

    carpeta_gmail = tmp_path / "gmail" / "email_001"
    carpeta_gmail.mkdir(parents=True)
    (carpeta_gmail / "cv.pdf").write_bytes(b"cv")

    eliminados = privacy.eliminar_archivos_candidato("email_001", tmp_path)

    assert eliminados == 2
    assert not (adjuntos / "email_001__cv.pdf").exists()
    assert not carpeta_gmail.exists()
    assert (adjuntos / "email_002__cv.pdf").exists()


@pytest.mark.parametrize("email_id", ["../otro", "a/b", ""])
def test_eliminar_archivos_rechaza_rutas(tmp_path, email_id):
    with pytest.raises(ValueError):
        privacy.eliminar_archivos_candidato(email_id, tmp_path)


def test_purgar_archivos_antiguos(tmp_path):
    adjuntos = tmp_path / "adjuntos_extraidos"
    adjuntos.mkdir()
    viejo = adjuntos / "email_001__cv.pdf"
    nuevo = adjuntos / "email_002__cv.pdf"
    viejo.write_bytes(b"x")
    nuevo.write_bytes(b"y")

    ahora = time.time()
    hace_200_dias = ahora - 200 * 86400
    os.utime(viejo, (hace_200_dias, hace_200_dias))

    eliminados = privacy.purgar_archivos_antiguos(180, tmp_path, ahora=ahora)

    assert eliminados == 1
    assert not viejo.exists()
    assert nuevo.exists()


def _admin():
    return {"id": 1, "email": "admin@example.com", "role": "admin"}


def _recruiter():
    return {"id": 2, "email": "recruiter@example.com", "role": "recruiter"}


def test_eliminar_perfil_requiere_admin():
    api.app.dependency_overrides[api.auth.obtener_recruiter_actual] = _recruiter
    try:
        response = client.delete("/profiles/email_001")
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 403


def test_eliminar_perfil(monkeypatch):
    monkeypatch.setattr(api.profile_repository, "eliminar_perfil", lambda email_id: True)
    monkeypatch.setattr(api.privacy, "eliminar_archivos_candidato", lambda email_id: 1)
    api.app.dependency_overrides[api.auth.obtener_recruiter_actual] = _admin
    try:
        response = client.delete("/profiles/email_001")
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "email_id": "email_001",
        "perfil_eliminado": True,
        "archivos_eliminados": 1,
    }


def test_eliminar_perfil_inexistente(monkeypatch):
    monkeypatch.setattr(api.profile_repository, "eliminar_perfil", lambda email_id: False)
    monkeypatch.setattr(api.privacy, "eliminar_archivos_candidato", lambda email_id: 0)
    api.app.dependency_overrides[api.auth.obtener_recruiter_actual] = _admin
    try:
        response = client.delete("/profiles/no_existe")
    finally:
        api.app.dependency_overrides.clear()

    assert response.status_code == 404
