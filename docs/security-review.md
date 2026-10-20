# Revisión de seguridad (OWASP Top 10) — Sprint 7, issue #61

Alcance: pipeline de ingesta (Gmail → adjunto → ClamAV → extracción → Postgres),
API FastAPI (`src/api.py`, `src/auth.py`) y dashboard Streamlit (`dashboard/`).
Fecha: 2026-10-20.

Estados: **Corregido** (cambio en este sprint, con prueba automatizada),
**Verificado** (ya estaba bien, se revisó el código), **Aceptado** (riesgo
conocido y asumido, con su justificación) y **Pendiente** (queda en backlog).

| # | Categoría | Hallazgo | Estado |
|---|---|---|---|
| A01 | Broken Access Control | `/auth/register` era público: cualquiera podía crear una cuenta y leer todos los CVs. Ahora exige rol admin; el primer admin se crea con `scripts/create_admin.py`. | Corregido |
| A01 | Broken Access Control | Las plantillas de vacante se filtran por `recruiter_id`. | Verificado |
| A01 | Broken Access Control | Todos los recruiters ven todos los perfiles de candidatos (pool compartido). | Aceptado: es el modelo de negocio actual; revisar si se separan equipos o clientes. |
| A02 | Cryptographic Failures | `JWT_SECRET` aceptaba cualquier longitud (las pruebas usaban 16 bytes). Ahora se exigen ≥ 32 caracteres. | Corregido |
| A02 | Cryptographic Failures | Contraseñas con Argon2 (`pwdlib`). | Verificado |
| A02 | Cryptographic Failures | La API y el dashboard hablan HTTP plano. | Aceptado en red interna de Docker; en producción TLS se termina en el proxy (ver `docs/runbook.md`). |
| A03 | Injection | Todas las consultas SQL usan parámetros (`%s`, `%(nombre)s`); no hay SQL construido con f-strings. | Verificado |
| A03 | Injection | El texto de los CVs (evidencias, requisitos, explicación del LLM) se mostraba como Markdown: un CV con `![x](https://externo/pixel)` cargaba una imagen externa o mostraba enlaces de phishing. Ahora se escapa (`escapar_markdown`). | Corregido |
| A03 | Injection | Prompt injection desde el contenido del CV. | Verificado (salvaguardas de Sprint 4, `tests/test_agent.py`). |
| A04 | Insecure Design | `POST /rankings` ejecuta el agente de forma síncrona y sin cuota por usuario: un recruiter autenticado puede generar costo de API sin límite. | Pendiente: añadir cuota diaria por recruiter. |
| A05 | Security Misconfiguration | La API no enviaba cabeceras de seguridad. Ahora: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store`. | Corregido |
| A05 | Security Misconfiguration | Swagger (`/docs`) expuesto siempre. Ahora se desactiva con `ENABLE_API_DOCS=false` (valor por defecto en `docker-compose.yml`). | Corregido |
| A06 | Vulnerable Components | Dependencias sin versión fija. Ahora `constraints.txt` fija versiones y CI corre `pip-audit` en cada PR. Resultado actual: sin vulnerabilidades conocidas. | Corregido |
| A07 | Identification & Auth Failures | Login sin límite de intentos. Ahora 5 intentos fallidos por correo en 15 minutos → `429`. | Corregido |
| A07 | Identification & Auth Failures | El login respondía más rápido si el correo no existía (enumeración de cuentas por tiempo). Ahora verifica un hash ficticio. | Corregido |
| A07 | Identification & Auth Failures | El contador de intentos vive en memoria del proceso: se reinicia al reiniciar la API y no se comparte entre réplicas. | Aceptado con una sola réplica; si se escala, moverlo a Postgres/Redis. |
| A07 | Identification & Auth Failures | Los JWT no se pueden revocar antes de expirar. | Aceptado: expiran en 60 minutos. |
| A08 | Software & Data Integrity | Adjuntos escaneados con ClamAV antes de procesarse; si ClamAV no está disponible el adjunto se rechaza (falla cerrado). | Verificado |
| A08 | Software & Data Integrity | Cambios entran por PR con CI (lint, pruebas, auditoría de dependencias). | Corregido (#64) |
| A09 | Logging & Monitoring Failures | Sin métricas ni alertas. | Corregido en #66 (ver `docs/monitoring.md`). |
| A10 | SSRF | El sistema no descarga URLs proporcionadas por usuarios; `API_URL` solo viene del entorno. | Verificado (no aplica) |

## Secretos

- Se revisó todo el historial de git (`git log -p --all`) buscando llaves de
  API, `client_secret`, llaves privadas y contraseñas: solo aparecen
  contraseñas de prueba (`Password123!`) en los tests.
- `credentials.json`, `token.json`, `.env` y `secrets/` están en `.gitignore`.
- Los secretos de producción se pasan como variables de entorno (ver
  `.env.example`); nunca dentro de la imagen Docker.

## Cómo se verifica

```bash
pytest -q tests/test_auth.py tests/test_api.py tests/test_ranking_view.py
pip-audit -r constraints.txt --no-deps --disable-pip
```
