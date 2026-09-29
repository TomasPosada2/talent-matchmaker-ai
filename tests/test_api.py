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


def recruiter_autenticado():
    return {
        "id": 1,
        "email": "recruiter@example.com",
    }


def activar_autenticacion():
    api.app.dependency_overrides[
        api.auth.obtener_recruiter_actual
    ] = recruiter_autenticado


def limpiar_autenticacion():
    api.app.dependency_overrides.clear()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "talent-matchmaker-ai",
    }


def test_profiles_requiere_autenticacion():
    limpiar_autenticacion()

    response = client.get("/profiles")

    assert response.status_code in (401, 403)


def test_rankings_requiere_autenticacion():
    limpiar_autenticacion()

    response = client.post(
        "/rankings",
        json={
            "vacante": {
                "titulo": "Backend Developer",
            }
        },
    )

    assert response.status_code in (401, 403)


def test_listar_perfiles(monkeypatch):
    activar_autenticacion()

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

    limpiar_autenticacion()


def test_obtener_perfil(monkeypatch):
    activar_autenticacion()

    perfil = perfil_ejemplo()

    monkeypatch.setattr(
        api.profile_repository,
        "obtener_perfil",
        lambda email_id: perfil,
    )

    response = client.get(
        "/profiles/email-001"
    )

    assert response.status_code == 200
    assert response.json() == perfil

    limpiar_autenticacion()


def test_perfil_no_encontrado(monkeypatch):
    activar_autenticacion()

    monkeypatch.setattr(
        api.profile_repository,
        "obtener_perfil",
        lambda email_id: None,
    )

    response = client.get(
        "/profiles/no-existe"
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Perfil no encontrado."
    )

    limpiar_autenticacion()


def test_error_listando_perfiles(monkeypatch):
    activar_autenticacion()

    def lanzar_error():
        raise RuntimeError("DB error")

    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lanzar_error,
    )

    response = client.get("/profiles")

    assert response.status_code == 500

    limpiar_autenticacion()


def test_ranking_sin_perfiles(monkeypatch):
    activar_autenticacion()

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

    limpiar_autenticacion()


def test_generar_ranking(monkeypatch):
    activar_autenticacion()

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

    assert (
        data["ranking"][0]["email_id"]
        == "email-001"
    )
    assert data["ranking"][0]["puntaje"] == 90
    assert data["ranking"][0]["confianza"] == 0.95
    assert (
        data["metricas"]["tokens_totales"]
        == 100
    )

    limpiar_autenticacion()


def test_error_del_agente(monkeypatch):
    activar_autenticacion()

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
    assert (
        response.json()["detail"]
        == "Ranking inválido"
    )

    limpiar_autenticacion()


def test_registrar_recruiter(monkeypatch):
    monkeypatch.setattr(
        api.auth,
        "crear_tabla_recruiters",
        lambda: None,
    )

    monkeypatch.setattr(
        api.auth,
        "obtener_recruiter_por_email",
        lambda email: None,
    )

    monkeypatch.setattr(
        api.auth,
        "crear_recruiter",
        lambda email, password: {
            "id": 1,
            "email": email,
        },
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "recruiter@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "email": "recruiter@example.com",
    }


def test_recruiter_duplicado(monkeypatch):
    monkeypatch.setattr(
        api.auth,
        "crear_tabla_recruiters",
        lambda: None,
    )

    monkeypatch.setattr(
        api.auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 1,
            "email": email,
        },
    )

    response = client.post(
        "/auth/register",
        json={
            "email": "recruiter@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 409


def test_login_correcto(monkeypatch):
    monkeypatch.setattr(
        api.auth,
        "crear_tabla_recruiters",
        lambda: None,
    )

    monkeypatch.setattr(
        api.auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 1,
            "email": email,
            "password_hash": "hash",
        },
    )

    monkeypatch.setattr(
        api.auth,
        "verificar_password",
        lambda password, hashed: True,
    )

    monkeypatch.setattr(
        api.auth,
        "crear_access_token",
        lambda email: "jwt-de-prueba",
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "recruiter@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "jwt-de-prueba",
        "token_type": "bearer",
    }


def test_login_password_incorrecto(monkeypatch):
    monkeypatch.setattr(
        api.auth,
        "crear_tabla_recruiters",
        lambda: None,
    )

    monkeypatch.setattr(
        api.auth,
        "obtener_recruiter_por_email",
        lambda email: {
            "id": 1,
            "email": email,
            "password_hash": "hash",
        },
    )

    monkeypatch.setattr(
        api.auth,
        "verificar_password",
        lambda password, hashed: False,
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "recruiter@example.com",
            "password": "incorrecta",
        },
    )

    assert response.status_code == 401

def test_ranking_notifica_al_recruiter(monkeypatch):
    activar_autenticacion()

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

    notificacion = {}

    def enviar_fake(destinatario, ranking):
        notificacion["destinatario"] = destinatario
        notificacion["ranking"] = ranking
        return "mensaje-123"

    monkeypatch.setattr(
        api.email_notifier,
        "enviar_notificacion_ranking",
        enviar_fake,
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

    assert data["notificacion_enviada"] is True
    assert notificacion["destinatario"] == "recruiter@example.com"
    assert notificacion["ranking"] == ResultadoFake.ranking

    limpiar_autenticacion()


def test_ranking_continua_si_notificacion_falla(monkeypatch):
    activar_autenticacion()

    monkeypatch.setattr(
        api.profile_repository,
        "listar_perfiles",
        lambda: [perfil_ejemplo()],
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
        metricas = {}

    monkeypatch.setattr(
        api.agent,
        "rankear_candidatos",
        lambda vacante, perfiles: ResultadoFake(),
    )

    def enviar_con_error(destinatario, ranking):
        raise RuntimeError("Gmail no disponible")

    monkeypatch.setattr(
        api.email_notifier,
        "enviar_notificacion_ranking",
        enviar_con_error,
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

    assert data["ranking"] == ResultadoFake.ranking
    assert data["notificacion_enviada"] is False

    limpiar_autenticacion()


def test_ranking_con_error_no_envia_notificacion(monkeypatch):
    activar_autenticacion()

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

    llamadas = []

    def enviar_fake(destinatario, ranking):
        llamadas.append((destinatario, ranking))

    monkeypatch.setattr(
        api.email_notifier,
        "enviar_notificacion_ranking",
        enviar_fake,
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
    assert llamadas == []

    limpiar_autenticacion()

def test_guardar_job_template(monkeypatch):
    activar_autenticacion()

    plantilla = {
        "id": 1,
        "recruiter_id": 1,
        "nombre": "Backend Developer",
        "vacante": {
            "titulo": "Backend Developer",
            "experiencia": "3 años",
        },
    }

    monkeypatch.setattr(
        api.job_template_repository,
        "crear_tabla",
        lambda: None,
    )

    monkeypatch.setattr(
        api.job_template_repository,
        "guardar_plantilla",
        lambda recruiter_id, nombre, vacante: plantilla,
    )

    response = client.post(
        "/job-templates",
        json={
            "nombre": "Backend Developer",
            "vacante": {
                "titulo": "Backend Developer",
                "experiencia": "3 años",
            },
        },
    )

    assert response.status_code == 201
    assert response.json() == plantilla

    limpiar_autenticacion()


def test_listar_job_templates(monkeypatch):
    activar_autenticacion()

    plantillas = [
        {
            "id": 1,
            "recruiter_id": 1,
            "nombre": "Backend",
            "vacante": {
                "titulo": "Backend Developer",
            },
        },
        {
            "id": 2,
            "recruiter_id": 1,
            "nombre": "Data",
            "vacante": {
                "titulo": "Data Engineer",
            },
        },
    ]

    monkeypatch.setattr(
        api.job_template_repository,
        "crear_tabla",
        lambda: None,
    )

    monkeypatch.setattr(
        api.job_template_repository,
        "listar_plantillas",
        lambda recruiter_id: plantillas,
    )

    response = client.get(
        "/job-templates"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 2
    assert data["templates"] == plantillas

    limpiar_autenticacion()


def test_obtener_job_template(monkeypatch):
    activar_autenticacion()

    plantilla = {
        "id": 7,
        "recruiter_id": 1,
        "nombre": "Backend",
        "vacante": {
            "titulo": "Backend Developer",
        },
    }

    monkeypatch.setattr(
        api.job_template_repository,
        "crear_tabla",
        lambda: None,
    )

    monkeypatch.setattr(
        api.job_template_repository,
        "obtener_plantilla",
        lambda recruiter_id, template_id: plantilla,
    )

    response = client.get(
        "/job-templates/7"
    )

    assert response.status_code == 200
    assert response.json() == plantilla

    limpiar_autenticacion()


def test_job_template_ajena_o_inexistente(
    monkeypatch,
):
    activar_autenticacion()

    monkeypatch.setattr(
        api.job_template_repository,
        "crear_tabla",
        lambda: None,
    )

    monkeypatch.setattr(
        api.job_template_repository,
        "obtener_plantilla",
        lambda recruiter_id, template_id: None,
    )

    response = client.get(
        "/job-templates/999"
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Plantilla no encontrada."
    )

    limpiar_autenticacion()