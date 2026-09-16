"""
Sprint 4 - Issue #38
Golden set fijo para pruebas de regresión de calidad del ranking.

Representa una vacante conocida y tres candidatos con distintos
niveles de cobertura de requisitos.

La evidencia se mantiene como texto para reproducir el formato
consumido por agent_tools.verificar_evidencia().
"""


VACANTE_GOLDEN = {
    "titulo": "Backend Python Developer",
    "requisitos": [
        "Python",
        "SQL",
        "Docker",
        "AWS",
    ],
}


PERFILES_GOLDEN = [
    # ========================================================
    # Candidato fuerte
    # Evidencia para los 4 requisitos
    # ========================================================
    {
        "email_id": "candidato_fuerte",
        "archivo_origen": "cv_fuerte.pdf",

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
                "valor": None,
                "evidencia": None,
            },
        },

        "educacion": {
            "valor": "Ingeniería de Sistemas",
            "evidencia": "Ingeniería de Sistemas",
        },

        "experiencia": {
            "valor": (
                "5 años desarrollando servicios backend "
                "en Python y desplegando aplicaciones en AWS."
            ),
            "evidencia": (
                "5 años desarrollando servicios backend "
                "en Python y desplegando aplicaciones en AWS."
            ),
        },

        "habilidades": {
            "valor": [
                "Python",
                "SQL",
                "Docker",
                "AWS",
            ],
            "evidencia": (
                "Python, SQL, Docker, AWS"
            ),
        },
    },

    # ========================================================
    # Candidato medio
    # Evidencia para Python y SQL
    # Sin evidencia para Docker y AWS
    # ========================================================
    {
        "email_id": "candidato_medio",
        "archivo_origen": "cv_medio.pdf",

        "nombre": {
            "valor": "Carlos Ruiz",
            "evidencia": "Carlos Ruiz",
        },

        "contacto": {
            "email": {
                "valor": "carlos@example.com",
                "evidencia": "carlos@example.com",
            },
            "telefono": {
                "valor": None,
                "evidencia": None,
            },
        },

        "educacion": {
            "valor": "Ingeniería Informática",
            "evidencia": "Ingeniería Informática",
        },

        "experiencia": {
            "valor": (
                "Experiencia desarrollando aplicaciones "
                "con Python y bases de datos SQL."
            ),
            "evidencia": (
                "Experiencia desarrollando aplicaciones "
                "con Python y bases de datos SQL."
            ),
        },

        "habilidades": {
            "valor": [
                "Python",
                "SQL",
            ],
            "evidencia": (
                "Python, SQL"
            ),
        },
    },

    # ========================================================
    # Candidato débil
    # Sin evidencia para los requisitos técnicos de la vacante
    # ========================================================
    {
        "email_id": "candidato_debil",
        "archivo_origen": "cv_debil.pdf",

        "nombre": {
            "valor": "Laura Gómez",
            "evidencia": "Laura Gómez",
        },

        "contacto": {
            "email": {
                "valor": "laura@example.com",
                "evidencia": "laura@example.com",
            },
            "telefono": {
                "valor": None,
                "evidencia": None,
            },
        },

        "educacion": {
            "valor": "Administración de Empresas",
            "evidencia": "Administración de Empresas",
        },

        "experiencia": {
            "valor": (
                "Experiencia en gestión administrativa "
                "y coordinación de equipos."
            ),
            "evidencia": (
                "Experiencia en gestión administrativa "
                "y coordinación de equipos."
            ),
        },

        "habilidades": {
            "valor": [
                "Excel",
                "PowerPoint",
            ],
            "evidencia": (
                "Excel, PowerPoint"
            ),
        },
    },
]


# ============================================================
# Ranking de referencia
# ============================================================

RANKING_GOLDEN = [
    {
        "email_id": "candidato_fuerte",
        "puntaje": 95,

        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "SQL",
            },
            {
                "requisito": "Docker",
                "evidencia": "Docker",
            },
            {
                "requisito": "AWS",
                "evidencia": "AWS",
            },
        ],

        "requisitos_sin_evidencia": [],
    },

    {
        "email_id": "candidato_medio",
        "puntaje": 60,

        "justificacion": [
            {
                "requisito": "Python",
                "evidencia": "Python",
            },
            {
                "requisito": "SQL",
                "evidencia": "SQL",
            },
        ],

        "requisitos_sin_evidencia": [
            "Docker",
            "AWS",
        ],
    },

    {
        "email_id": "candidato_debil",
        "puntaje": 20,

        "justificacion": [],

        "requisitos_sin_evidencia": [
            "Python",
            "SQL",
            "Docker",
            "AWS",
        ],
    },
]


# ============================================================
# Orden esperado de calidad
# ============================================================

ORDEN_ESPERADO = [
    "candidato_fuerte",
    "candidato_medio",
    "candidato_debil",
]