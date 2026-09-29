import logging

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from src import (
    agent,
    auth,
    email_notifier,
    job_template_repository,
    profile_repository,
)


logger = logging.getLogger("api")


app = FastAPI(
    title="Talent Matchmaker AI API",
    description=(
        "REST API para consultar perfiles y generar "
        "rankings de candidatos."
    ),
    version="1.0.0",
)


# ============================================================
# Modelos de entrada
# ============================================================

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


# ============================================================
# Authentication
# ============================================================

@app.post("/auth/register", status_code=201)
def registrar_recruiter(
    request: RecruiterRegisterRequest,
):
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
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )

    if not auth.verificar_password(
        request.password,
        recruiter["password_hash"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas.",
        )

    token = auth.crear_access_token(
        recruiter["email"]
    )

    return {
        "access_token": token,
        "token_type": "bearer",
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
            recruiter.get("email"),
            exc,
        )

    return {
        "ranking": resultado.ranking,
        "metricas": resultado.metricas,
        "notificacion_enviada": notificacion_enviada,
    }