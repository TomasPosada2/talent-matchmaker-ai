from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src import agent, profile_repository


app = FastAPI(
    title="Talent Matchmaker AI API",
    description="REST API para consultar perfiles y generar rankings de candidatos.",
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


# ============================================================
# Health check
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "talent-matchmaker-ai",
    }


# ============================================================
# Profiles
# ============================================================

@app.get("/profiles")
def listar_perfiles():
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
def obtener_perfil(email_id: str):
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
# Rankings
# ============================================================

@app.post("/rankings")
def generar_ranking(request: RankingRequest):
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
            detail="No hay perfiles disponibles para generar el ranking.",
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

    return {
        "ranking": resultado.ranking,
        "metricas": resultado.metricas,
    }