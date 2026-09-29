from fastapi.testclient import TestClient

from src import api


client = TestClient(api.app)


def perfil_ejemplo():
    return {
        "email_id": "email-001",
        "archivo_origen": "candidato.pdf",
        "nombre": {
            "valor": "Ana Pérez",
            "evidencia": "Ana Pérez",
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
            "valor": ["Desarrolladora Python"],
            "evidencia": ["Desarrolladora Python"],
        },
        "habilidades": {
            "valor": ["Python", "SQL"],
            "evidencia": ["Python", "SQL"],
        },
    }


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "talent-matchmaker-ai",
    }


def test_listar_perfiles(monkeypatch):
    perfiles = [perfil_ejemplo()]

    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lambda: perfiles,
    )

    response = client.get("/profiles")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["profiles"] == perfiles


def test_obtener_perfil(monkeypatch):
    perfil = perfil_ejemplo()

    monkeypatch.setattr(
        api.profile_repository,
        "obtener_perfil",
        lambda email_id: perfil,
    )

    response = client.get("/profiles/email-001")

    assert response.status_code == 200
    assert response.json() == perfil


def test_perfil_no_encontrado(monkeypatch):
    monkeypatch.setattr(
        api.profile_repository,
        "obtener_perfil",
        lambda email_id: None,
    )

    response = client.get("/profiles/no-existe")

    assert response.status_code == 404
    assert response.json()["detail"] == "Perfil no encontrado."


def test_error_listando_perfiles(monkeypatch):
    def lanzar_error():
        raise RuntimeError("DB error")

    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lanzar_error,
    )

    response = client.get("/profiles")

    assert response.status_code == 500


def test_ranking_sin_perfiles(monkeypatch):
    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lambda: [],
    )

    response = client.post(
        "/rankings",
        json={
            "vacante": {
                "titulo": "Backend Developer",
            }
        },
    )

    assert response.status_code == 400


def test_generar_ranking(monkeypatch):
    perfiles = [perfil_ejemplo()]

    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lambda: perfiles,
    )

    class ResultadoFake:
        ranking = [
            {
                "email_id": "email-001",
                "puntaje": 90,
                "confianza": 0.95,
                "razon_confianza": "Evidencia suficiente",
                "justificacion": [],
                "requisitos_sin_evidencia": [],
            }
        ]
        pasos = []
        error = None
        metricas = {
            "tokens_totales": 100,
        }

    monkeypatch.setattr(
        api.agent,
        "rankear_candidatos",
        lambda vacante, perfiles: ResultadoFake(),
    )

    response = client.post(
        "/rankings",
        json={
            "vacante": {
                "titulo": "Backend Developer",
            }
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ranking"][0]["email_id"] == "email-001"
    assert data["ranking"][0]["puntaje"] == 90
    assert data["ranking"][0]["confianza"] == 0.95
    assert data["metricas"]["tokens_totales"] == 100


def test_error_del_agente(monkeypatch):
    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lambda: [perfil_ejemplo()],
    )

    class ResultadoFake:
        ranking = None
        pasos = []
        error = "Ranking inválido"
        metricas = {}

    monkeypatch.setattr(
        api.agent,
        "rankear_candidatos",
        lambda vacante, perfiles: ResultadoFake(),
    )

    response = client.post(
        "/rankings",
        json={
            "vacante": {
                "titulo": "Backend Developer",
            }
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Ranking inválido"