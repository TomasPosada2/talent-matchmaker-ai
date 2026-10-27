import logging
import os
import time
from typing import Literal

import anthropic
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from src import (
    agent,
    auth,
    chatbot,
    email_notifier,
    email_polling,
    job_template_repository,
    observability,
    privacy,
    profile_repository,
)

observability.configurar_logging()
logger = logging.getLogger("api")


def _docs_habilitados() -> bool:
    """Swagger/OpenAPI solo se expone si ENABLE_API_DOCS lo permite."""
    return os.getenv("ENABLE_API_DOCS", "true").lower() in ("1", "true", "yes")


app = FastAPI(
    title="Talent Matchmaker AI API",
    description=(
        "REST API para consultar perfiles y generar "
        "rankings de candidatos."
    ),
    version="1.0.0",
    docs_url="/docs" if _docs_habilitados() else None,
    redoc_url="/redoc" if _docs_habilitados() else None,
    openapi_url="/openapi.json" if _docs_habilitados() else None,
)


# Sprint 7 - #61: cabeceras de seguridad (A05 Security Misconfiguration).
CABECERAS_SEGURIDAD = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


@app.middleware("http")
async def agregar_cabeceras_seguridad(request: Request, call_next):
    response = await call_next(request)
    for nombre, valor in CABECERAS_SEGURIDAD.items():
        response.headers.setdefault(nombre, valor)
    return response


# Sprint 7 - #66: métricas, log por petición y alertas de errores/latencia.
# Se registra después del middleware de cabeceras, así que lo envuelve y
# también mide las respuestas de error.
@app.middleware("http")
async def medir_peticiones(request: Request, call_next):
    inicio = time.perf_counter()

    try:
        response = await call_next(request)
        status = response.status_code
    except Exception:
        logger.exception("Error no controlado en %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor."},
        )
        status = 500

    duracion = time.perf_counter() - inicio
    ruta = request.scope.get("route")
    plantilla = getattr(ruta, "path", "sin_ruta")

    observability.PETICIONES_HTTP.labels(
        method=request.method, route=plantilla, status=str(status)
    ).inc()
    observability.LATENCIA_HTTP.labels(
        method=request.method, route=plantilla
    ).observe(duracion)

    logger.info(
        "%s %s -> %d (%.0f ms)",
        request.method,
        plantilla,
        status,
        duracion * 1000,
    )

    if status >= 500:
        observability.alertar(
            "error_api",
            f"{request.method} {plantilla} respondió {status}.",
            clave=f"error_api:{request.method}:{plantilla}",
        )
    elif duracion > observability.umbral_peticion_lenta_segundos():
        observability.alertar(
            "latencia_api",
            f"{request.method} {plantilla} tardó {duracion:.1f} s.",
            clave=f"latencia_api:{request.method}:{plantilla}",
        )

    return response


# ============================================================
# Modelos de entrada
# ============================================================

class MensajeChat(BaseModel):
    rol: Literal["usuario", "asistente"]
    texto: str = Field(
        ...,
        min_length=1,
        max_length=chatbot.MAX_CARACTERES_MENSAJE,
    )


class ChatRequest(BaseModel):
    mensajes: list[MensajeChat] = Field(
        ...,
        min_length=1,
        max_length=chatbot.MAX_MENSAJES_HISTORIAL,
    )


class RankingRequest(BaseModel):
    vacante: dict = Field(
        ...,
        description="Descripción estructurada de la vacante.",
    )


class RecruiterRegisterRequest(BaseModel):
    email: str
    password: str = Field(
        ...,
        min_length=8,
    )
    role: str = Field(
        "recruiter",
        pattern="^(recruiter|admin)$",
    )


class RecruiterLoginRequest(BaseModel):
    email: str
    password: str


class JobTemplateRequest(BaseModel):
    nombre: str = Field(
        ...,
        min_length=1,
    )
    vacante: dict = Field(
        ...,
        description="Descripción estructurada de la vacante.",
    )


# ============================================================
# Health check público
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "talent-matchmaker-ai",
    }


@app.get("/health/ready")
def health_ready():
    """
    Sprint 7 - #66: verifica dependencias (PostgreSQL).

    /health solo dice que el proceso responde; /health/ready dice si
    puede atender peticiones reales. Docker y el monitoreo usan este.
    """
    try:
        with profile_repository.obtener_conexion() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Health check: PostgreSQL no disponible.")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "unavailable"},
        )

    return {"status": "ok", "database": "ok"}


@app.get("/metrics", include_in_schema=False)
def metricas(request: Request):
    """
    Métricas en formato Prometheus.

    Si METRICS_TOKEN está definido, exige ``Authorization: Bearer <token>``.
    """
    token = os.getenv("METRICS_TOKEN")
    if token and request.headers.get("Authorization") != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="No autorizado.")

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================================
# Authentication
# ============================================================

@app.post("/auth/register", status_code=201)
def registrar_recruiter(
    request: RecruiterRegisterRequest,
    admin: dict = Depends(auth.requerir_admin),
):
    # Sprint 7 - #61: solo un admin puede crear cuentas. Antes el registro
    # era público y cualquiera podía crear una cuenta y leer los CVs.
    # El primer admin se crea con scripts/create_admin.py.
    try:
        auth.crear_tabla_recruiters()

        existente = auth.obtener_recruiter_por_email(
            request.email
        )

        if existente is not None:
            raise HTTPException(
                status_code=409,
                detail="El recruiter ya existe.",
            )

        recruiter = auth.crear_recruiter(
            request.email,
            request.password,
            request.role,
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible crear el recruiter.",
        ) from exc

    return recruiter


@app.post("/auth/login")
def login_recruiter(
    request: RecruiterLoginRequest,
):
    if auth.login_bloqueado(request.email):
        raise HTTPException(
            status_code=429,
            detail=(
                "Demasiados intentos fallidos. "
                "Intenta de nuevo más tarde."
            ),
        )

    try:
        auth.crear_tabla_recruiters()

        recruiter = auth.obtener_recruiter_por_email(
            request.email
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible autenticar al recruiter.",
        ) from exc

    if recruiter is None:
        auth.verificar_password_ficticio(request.password)
        auth.registrar_login_fallido(request.email)
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )

    if not auth.verificar_password(
        request.password,
        recruiter["password_hash"],
    ):
        auth.registrar_login_fallido(request.email)
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )

    auth.limpiar_intentos_login(request.email)

    token = auth.crear_access_token(
        recruiter["email"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# ============================================================
# Usuario actual y administración
# ============================================================

@app.get("/auth/me")
def obtener_mi_usuario(
    recruiter: dict = Depends(auth.obtener_recruiter_actual),
):
    return {
        "id": recruiter["id"],
        "email": recruiter["email"],
        "role": recruiter["role"],
    }


@app.get("/admin/users")
def listar_usuarios_admin(
    admin: dict = Depends(auth.requerir_admin),
):
    try:
        usuarios = auth.listar_recruiters_admin()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los usuarios.",
        ) from exc

    return {
        "total": len(usuarios),
        "users": usuarios,
    }


# ============================================================
# Profiles protegidos
# ============================================================

@app.get("/profiles")
def listar_perfiles(
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        perfiles = profile_repository.listar_perfiles()

        return {
            "total": len(perfiles),
            "profiles": perfiles,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los perfiles.",
        ) from exc


@app.get("/profiles/{email_id}")
def obtener_perfil(
    email_id: str,
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        perfil = profile_repository.obtener_perfil(
            email_id
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar el perfil.",
        ) from exc

    if perfil is None:
        raise HTTPException(
            status_code=404,
            detail="Perfil no encontrado.",
        )

    return perfil


@app.delete("/profiles/{email_id}")
def eliminar_perfil(
    email_id: str,
    admin: dict = Depends(auth.requerir_admin),
):
    """
    Sprint 7 - #63: derecho de supresión (Ley 1581 de 2012).

    Borra el perfil de la base de datos y las copias del CV en disco.
    """
    try:
        existia = profile_repository.eliminar_perfil(email_id)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible eliminar el perfil.",
        ) from exc

    try:
        archivos = privacy.eliminar_archivos_candidato(email_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Identificador de perfil inválido.",
        ) from exc

    if not existia and archivos == 0:
        raise HTTPException(
            status_code=404,
            detail="Perfil no encontrado.",
        )

    logger.info(
        "Perfil %s eliminado por %s (archivos borrados: %d).",
        email_id,
        privacy.enmascarar_email(admin.get("email")),
        archivos,
    )

    return {
        "email_id": email_id,
        "perfil_eliminado": existia,
        "archivos_eliminados": archivos,
    }


# ============================================================
# Gmail (Sprint 8 - #86)
# ============================================================

@app.get("/gmail/status")
def estado_gmail(
    recruiter: dict = Depends(auth.obtener_recruiter_actual),
):
    """
    Estado de la conexión con Gmail, según el último ciclo del listener.

    Se considera desconectado si no hubo un ciclo correcto en los últimos
    5 intervalos de polling (mínimo 5 minutos).
    """
    intervalo = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

    return email_polling.leer_estado_listener(
        privacy.obtener_carpeta_trabajo() / "listener_heartbeat.json",
        max_segundos_sin_ciclo=max(300, intervalo * 5),
    )


# ============================================================
# Asistente (Sprint 8 - #87)
# ============================================================

@app.get("/chat/status")
def estado_asistente(
    recruiter: dict = Depends(auth.obtener_recruiter_actual),
):
    return {
        "disponible": chatbot.asistente_disponible(),
        "modelo": chatbot.obtener_modelo(),
        "preguntas_restantes_hoy": chatbot.preguntas_restantes(recruiter["id"]),
    }


@app.post("/chat")
def conversar(
    request: ChatRequest,
    recruiter: dict = Depends(auth.obtener_recruiter_actual),
):
    """
    Responde la última pregunta de la conversación con datos del sistema.

    El cliente envía la conversación visible completa (máximo
    MAX_MENSAJES_HISTORIAL mensajes); el servidor no guarda historial.
    """
    try:
        respuesta = chatbot.responder(
            [mensaje.model_dump() for mensaje in request.mensajes],
            recruiter,
        )
    except chatbot.AsistenteNoDisponible as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "El asistente no está configurado: falta "
                "ANTHROPIC_API_KEY en el servidor."
            ),
        ) from exc
    except chatbot.CuotaAgotada as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=503,
            detail="La llave de Anthropic configurada no es válida.",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="El servicio de IA está saturado. Intenta en un minuto.",
        ) from exc
    except anthropic.APIError as exc:
        logger.exception("Error del servicio de IA en el asistente.")
        raise HTTPException(
            status_code=502,
            detail="El servicio de IA no respondió. Intenta de nuevo.",
        ) from exc

    return {
        "respuesta": respuesta.texto,
        "herramientas_usadas": respuesta.herramientas_usadas,
        "metricas": {
            "pasos": respuesta.pasos,
            "tokens_entrada": respuesta.tokens_entrada,
            "tokens_salida": respuesta.tokens_salida,
        },
        "preguntas_restantes_hoy": chatbot.preguntas_restantes(recruiter["id"]),
    }


# ============================================================
# Job templates protegidos
# ============================================================

@app.post("/job-templates", status_code=201)
def guardar_job_template(
    request: JobTemplateRequest,
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        job_template_repository.crear_tabla()

        plantilla = (
            job_template_repository.guardar_plantilla(
                recruiter_id=recruiter["id"],
                nombre=request.nombre,
                vacante=request.vacante,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible guardar la plantilla.",
        ) from exc

    return plantilla


@app.get("/job-templates")
def listar_job_templates(
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        job_template_repository.crear_tabla()

        plantillas = (
            job_template_repository.listar_plantillas(
                recruiter_id=recruiter["id"],
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar las plantillas.",
        ) from exc

    return {
        "total": len(plantillas),
        "templates": plantillas,
    }


@app.get("/job-templates/{template_id}")
def obtener_job_template(
    template_id: int,
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        job_template_repository.crear_tabla()

        plantilla = (
            job_template_repository.obtener_plantilla(
                recruiter_id=recruiter["id"],
                template_id=template_id,
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar la plantilla.",
        ) from exc

    if plantilla is None:
        raise HTTPException(
            status_code=404,
            detail="Plantilla no encontrada.",
        )

    return plantilla


# ============================================================
# Rankings protegidos
# ============================================================

@app.post("/rankings")
def generar_ranking(
    request: RankingRequest,
    recruiter: dict = Depends(
        auth.obtener_recruiter_actual
    ),
):
    try:
        perfiles = profile_repository.listar_perfiles()

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible consultar los perfiles.",
        ) from exc

    if not perfiles:
        raise HTTPException(
            status_code=400,
            detail=(
                "No hay perfiles disponibles para "
                "generar el ranking."
            ),
        )

    try:
        resultado = agent.rankear_candidatos(
            request.vacante,
            perfiles,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Error al ejecutar el ranking.",
        ) from exc

    if resultado.error:
        raise HTTPException(
            status_code=422,
            detail=resultado.error,
        )

    # Sprint 5 - Issue #50:
    # Notificar al recruiter cuando el ranking
    # finaliza correctamente.
    notificacion_enviada = False

    try:
        email_notifier.enviar_notificacion_ranking(
            destinatario=recruiter["email"],
            ranking=resultado.ranking,
        )
        notificacion_enviada = True

    except Exception as exc:
        logger.exception(
            "El ranking terminó correctamente, pero no fue "
            "posible notificar al recruiter %s: %s",
            privacy.enmascarar_email(recruiter.get("email")),
            exc,
        )

    return {
        "ranking": resultado.ranking,
        "metricas": resultado.metricas,
        "notificacion_enviada": notificacion_enviada,
    }