# Revisión de privacidad de datos personales — Sprint 7, issue #63

Marco de referencia: Ley 1581 de 2012 (Habeas Data, Colombia) y su Decreto
1377 de 2013. Esta revisión es técnica y no sustituye una revisión legal.

## 1. Inventario de datos personales

| Dato | Origen | Dónde se guarda | Quién accede |
|---|---|---|---|
| CV original (PDF/DOCX/imagen) | Adjunto del correo del candidato | `data/salida/gmail/<id>/` y `data/salida/adjuntos_extraidos/` (volumen `app-data` en Docker) | Procesos del backend |
| Nombre, correo, teléfono, educación, experiencia, habilidades y la evidencia textual de cada campo | Extraídos del CV | Tabla `profiles` en PostgreSQL (columnas + JSONB) | Cualquier recruiter o admin autenticado |
| Reporte de lote (incluye los perfiles del lote) | Pipeline | `data/salida/reporte_lote.json` | Procesos del backend y la interfaz de prueba `app.py` |
| Remitente y asunto del correo | Gmail | Solo en memoria durante el procesamiento | — |
| Correo y hash Argon2 de la contraseña del recruiter | Alta por un admin | Tabla `recruiters` | Admins (`/admin/users`) |
| Fragmentos de perfiles enviados al LLM | Ranking con Claude | Anthropic (encargado del tratamiento) | Anthropic, según su política de retención |
| Preguntas al asistente y los perfiles que consulta para responder | Recruiter (#87) | Solo en la sesión del navegador; el servidor no guarda el historial del chat | Anthropic, igual que el ranking con IA |

## 2. Controles implementados

| Principio | Control | Dónde |
|---|---|---|
| Acceso restringido | Toda consulta de perfiles exige JWT; crear cuentas exige rol admin. | `src/api.py`, `src/auth.py` (#61) |
| Supresión (derecho del titular) | `DELETE /profiles/{email_id}` (solo admin) borra el perfil de Postgres y las copias del CV en disco. | `src/api.py`, `src/privacy.py` |
| Temporalidad / retención | `scripts/purge_expired_data.py` borra perfiles sin actualizar y CVs en disco con más de `RETENTION_DAYS` días (180 por defecto). En Docker corre a diario desde el servicio `maintenance`. | `scripts/purge_expired_data.py` |
| Minimización en logs | Los correos de recruiters se enmascaran (`m***@empresa.com`) antes de escribirse en logs. Los logs del pipeline identifican candidatos solo por `email_id`, no por nombre. | `src/privacy.py`, `src/api.py`, `src/email_notifier.py` |
| Veracidad | Ningún dato se infiere: si no está en el CV, queda en `null` con su evidencia. | Principio del producto desde Sprint 1 |
| Seguridad | Escaneo antimalware, contraseñas Argon2, backups cifrados en tránsito dentro de la red de Docker. | #45, #61, #67 |

## 3. Riesgos abiertos

| Riesgo | Recomendación | Responsable |
|---|---|---|
| No hay aviso de privacidad ni autorización del titular. El candidato envía su CV por correo, pero no se le informa la finalidad ni el uso de un proveedor de IA. | Redactar el aviso de privacidad y responder automáticamente a cada correo con él. **Requiere revisión legal.** | Product Owner + asesoría legal |
| Los perfiles se envían a Anthropic para el ranking con IA y para el asistente (transferencia a un encargado). | Firmar o aceptar el DPA de Anthropic y declararlo en el aviso de privacidad. El modo demostración no envía datos fuera. | Product Owner |
| Cifrado en reposo: depende del disco o volumen donde corre Postgres. | En producción usar un volumen o servicio de base de datos administrado con cifrado en reposo activado. | Operaciones |
| `reporte_lote.json` duplica los perfiles del último lote en disco. | Queda cubierto por la purga y lo usa la interfaz de prueba `app.py`; eliminarlo cuando se retire esa interfaz. | Equipo |
| Todos los recruiters ven todos los candidatos. | Aceptado mientras haya un solo equipo de reclutamiento (ver `docs/security-review.md`). | Product Owner |
| Rectificación: el titular puede pedir corregir un dato, pero no hay endpoint de edición. | Hoy se atiende reprocesando el CV corregido (el pipeline actualiza el perfil por `email_id`). | Equipo |

## 4. Procedimiento ante una solicitud de un titular

1. Ubicar el `email_id` del candidato (vista **Candidatos** del dashboard, filtro por nombre).
2. **Consulta:** entregar el perfil (`GET /profiles/{email_id}`).
3. **Supresión:** un admin ejecuta `DELETE /profiles/{email_id}` y guarda la respuesta como constancia.
4. Los backups vencen solos según `BACKUP_RETENTION_DAYS` (ver `docs/runbook.md`): informar al titular de ese plazo.
