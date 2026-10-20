# Arquitectura

## 1. Componentes

| Componente | Código | Proceso en Docker | Responsabilidad |
|---|---|---|---|
| Listener de Gmail | `run_listener.py`, `src/email_polling.py`, `src/gmail_inbox.py` | `listener` | Consulta Gmail periódicamente, descarga los adjuntos de correos nuevos y lanza el pipeline. |
| Pipeline de ingesta | `src/pipeline.py` y sus etapas | Dentro del listener (o `seed_demo.py`) | Convierte un correo en un perfil validado y lo guarda. |
| API REST | `src/api.py`, `src/auth.py` | `api` | Autenticación JWT con roles, perfiles, vacantes, rankings, supresión de datos, métricas. |
| Agente de ranking | `src/agent.py`, `src/agent_tools.py` | Dentro de la API | Compara candidatos contra una vacante con Claude, usando tools que verifican la evidencia. |
| Ranking de demostración | `src/demo_ranking.py` | Dentro del dashboard | Coincidencia textual determinista: sin IA y sin costo. |
| Dashboard | `dashboard/` | `dashboard` | Interfaz de recruiters y admins. Solo habla con la API. |
| PostgreSQL | `src/*_repository.py` | `db` | Perfiles, cuentas y plantillas de vacantes. |
| ClamAV | `src/malware_scanner.py` | `clamav` | Antivirus; el pipeline se comunica con él por la red. |
| Mantenimiento | `scripts/purge_expired_data.py` | `maintenance` | Purga diaria por retención. |
| Backups | `scripts/backup*.sh` | `backup` | `pg_dump` diario más los archivos de CVs. |

## 2. Flujo de ingesta (HU-01 a HU-08)

```
correo ─► HU-01 detectar (¿tiene adjunto PDF/DOCX?) ─► ignorado / descartado
            │
            ▼
        HU-02 validar adjunto (existe, no vacío, ≤ 5 MB) y copiarlo con nombre trazable
            │
            ▼
        #45 ClamAV (si no responde, el adjunto se rechaza: falla cerrado)
            │
            ▼
        HU-03 extraer texto en orden (pdfplumber / python-docx; OCR con Tesseract si es imagen)
            │
            ▼
        HU-04/05 estructurar campos; cada uno con {valor, evidencia}
            │
            ▼
        HU-06 validar contra el schema JSON fijo ─► PostgreSQL (upsert por email_id)
```

HU-07/HU-08: `procesar_lote` corre cada correo de forma aislada. Un CV roto
queda como `error` con su motivo y no detiene el lote. Al final se generan
`reporte_lote.json`, métricas Prometheus y, si fallan más del 50 % de los
CVs, una alerta.

## 3. Ranking

1. La vacante se estructura como `{cargo, requisitos[]}` (`vacancy_structurer.py`
   o el formulario del dashboard).
2. `POST /rankings` ejecuta el agente (Claude Agent SDK). El modelo se
   configura con `CLAUDE_MODEL`. El agente sigue el ciclo
   Pensamiento → Acción → Observación, con un máximo de 8 pasos, y tiene dos tools:
   - `consultar_perfiles`: lista los candidatos o consulta uno.
   - `verificar_evidencia`: dice si un requisito tiene evidencia literal
     en el perfil. El agente no puede afirmar que se cumple un requisito
     sin esta verificación.
3. Salvaguardas (Sprint 4): el texto de los CVs se trata como dato y no
   como instrucción (detección de prompt injection), reintentos con
   *backoff* exponencial, puntaje de confianza por decisión y registro de
   tokens y costo.
4. La respuesta trae, por candidato: puntaje, confianza, la evidencia citada
   por requisito y los requisitos sin evidencia. Al terminar se notifica al
   recruiter por correo (#50).

## 4. Modelo de datos

```
recruiters                     job_templates                      profiles
───────────                    ─────────────                      ────────
id            BIGSERIAL PK     id           BIGSERIAL PK          id             BIGSERIAL PK
email         TEXT UNIQUE      recruiter_id → recruiters.id       email_id       TEXT UNIQUE
password_hash TEXT (Argon2)                 ON DELETE CASCADE     archivo_origen TEXT
role          recruiter|admin  nombre       TEXT                  nombre, email, telefono  TEXT
created_at    TIMESTAMPTZ      vacante      JSONB                 perfil         JSONB  (perfil completo con evidencia)
                               UNIQUE(recruiter_id, nombre)       created_at, updated_at TIMESTAMPTZ
```

Las tablas se crean al arrancar (`CREATE TABLE IF NOT EXISTS`). No hay
herramienta de migraciones: los cambios de esquema hasta ahora fueron
aditivos (`ADD COLUMN IF NOT EXISTS`).

## 5. Seguridad y acceso

| Recurso | Anónimo | Recruiter | Admin |
|---|---|---|---|
| `GET /health`, `/health/ready` | ✓ | ✓ | ✓ |
| `POST /auth/login` | ✓ | ✓ | ✓ |
| `GET /profiles`, `/profiles/{id}` | | ✓ | ✓ |
| `/job-templates` (solo las propias) | | ✓ | ✓ |
| `POST /rankings` | | ✓ | ✓ |
| `POST /auth/register`, `GET /admin/users` | | | ✓ |
| `DELETE /profiles/{id}` | | | ✓ |
| `GET /metrics` | ✓ (o con `METRICS_TOKEN`) | | |

Solo el dashboard se publica (detrás de Caddy, con HTTPS). La API, la base
de datos y ClamAV quedan en la red interna de Docker. Ver
[security-review.md](security-review.md).

## 6. Decisiones de diseño

| Decisión | Motivo |
|---|---|
| Evidencia obligatoria por campo y por requisito | Es el criterio de aceptación de todo el producto: un ranking debe poder auditarse línea por línea. |
| Extracción con reglas y regex, no con un LLM | Es determinista, barata y trazable. El LLM se reserva para comparar, que es donde aporta. |
| Perfil completo en JSONB más columnas consultables | Conserva exactamente la estructura validada por el schema y permite filtrar por nombre, correo o teléfono. |
| Bandeja simulada con la misma interfaz que Gmail | Permitió validar el pipeline sin credenciales desde el Sprint 1 y hoy sirve para pruebas y demos. |
| ClamAV por red (clamd) en Docker | Las firmas viven en su propio contenedor y se actualizan solas; la imagen de la app sigue siendo liviana. |
| Modo demostración sin IA | Permite demos y capacitación sin costo y sin enviar datos personales a terceros. |
| Una sola imagen Docker para todos los procesos | Un solo artefacto que construir, escanear y versionar. |
