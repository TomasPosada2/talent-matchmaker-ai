# Retrospectiva del proyecto y traspaso — issue #70

> Borrador preparado a partir del historial del repositorio, los issues y
> los PRs. Las secciones marcadas **(equipo)** las completa el equipo en la
> reunión de retrospectiva: reflejan percepciones que no salen del código.

## 1. Qué se entregó

| Sprint | Objetivo | Resultado | Pruebas automatizadas |
|---|---|---|---|
| 1 | Ingesta trazable de CVs: correo → perfil JSON con evidencia | 20/21 CVs del lote de prueba (95,2 %) | 9 |
| 2 | Auditar el Sprint 1 y consolidar el backlog | Se encontraron BUG-01 (tablas DOCX) y BUG-02 (teléfono inventado a partir de años) | 9 |
| 3 | Agente de ranking explicable con tools | Ranking con evidencia citada; BUG-01/02 corregidos | — |
| 4 | Robustez y calidad del ranking | OCR, prompt injection, confianza, golden set, CSV/PDF | 62 |
| 5 | Integración real | Gmail OAuth, PostgreSQL, API con JWT, ClamAV, notificaciones | 138 |
| 6 | Experiencia del recruiter | Dashboard: login, roles, filtros, vacantes, ranking, analítica | 174 |
| 7 | Endurecimiento y lanzamiento | CI/CD, Docker, OWASP, privacidad, monitoreo, backups, carga, accesibilidad, documentación | 215 |

Al cierre del Sprint 7 el sistema corre completo con `docker compose up`, y
se verificó de punta a punta con ClamAV y PostgreSQL reales
([runbook.md](runbook.md), [performance.md](performance.md)).

## 2. Qué funcionó bien

- **La auditoría del Sprint 2.** El equipo no se quedó con el "20/20
  exitoso" y encontró dos defectos que habrían contaminado cada ranking.
  Fue la decisión de mayor impacto del proyecto.
- **El principio de no inventar datos se sostuvo hasta el final.** Cada
  capa (extracción, schema, tools del agente, dashboard) lo respeta, y el
  golden set lo protege contra regresiones.
- **Interfaces estables.** La bandeja simulada del Sprint 1 tenía la misma
  interfaz que Gmail; en el Sprint 5 se conectó Gmail sin tocar el resto
  del pipeline.
- **Cobertura de pruebas creciente** en cada sprint: de 9 a 215.
- **(equipo)** …

## 3. Qué se puede mejorar

Observaciones a partir del historial:

- **El trabajo se concentró al final de cada sprint.** 11 commits el
  15-sep, 7 el 29-sep y 7 el 19-oct; casi nada en los días intermedios.
  Integrar en pasos pequeños reduce el riesgo de cierre.
- **El Sprint 6 rompió el flujo de ramas y PR.** Los sprints 4 y 5 usaron
  `sprint-N` → PR → `main`; el 6 se subió directo a `main`. Por eso el
  tablero y los issues quedaron desactualizados y se subieron scripts de un
  solo uso (`scripts/integrate_*.py`). El Sprint 7 volvió al flujo con PR y
  CI obligatorio.
- **El sistema nunca se había probado completo junto.** Cada pieza tenía
  pruebas con dobles, pero hasta el Sprint 7 nadie había visto un CV pasar
  por ClamAV y PostgreSQL reales hasta el dashboard. Al hacerlo apareció un
  defecto que las pruebas no detectaban (`requirements.txt` sin salto de
  línea final).
- **Los issues del Sprint 7 tenían una sola línea, sin criterios de
  aceptación**, a diferencia del estándar del Sprint 2. Conviene refinar
  antes de planear.
- **Funcionalidades a medio integrar:** la exportación a CSV/PDF (#42)
  existe como librería, pero no se puede usar desde la API ni el dashboard;
  la analítica (#58) no incluye *time-to-hire* ni embudo porque el sistema
  no registra el estado de cada candidato.
- **(equipo)** …

## 4. Acciones para un próximo ciclo

| Acción | Por qué |
|---|---|
| Mantener la regla "todo entra por PR con CI en verde" | Evita repetir lo del Sprint 6. |
| Exigir criterios de aceptación antes de pasar un issue a *To Do Next* | Es el estándar que funcionó en el Sprint 2. |
| Hacer una prueba de punta a punta (`seed_demo.py`) como parte de la *Definition of Done* | Detecta lo que las pruebas con dobles no ven. |
| Mover el tablero de GitHub junto con cada PR | El tablero fue la fuente de información menos confiable del proyecto. |

## 5. Traspaso

### Para quien opere el sistema

- Despliegue, backups, restauración y diagnóstico: [runbook.md](runbook.md).
- Alertas y métricas: [monitoring.md](monitoring.md).
- Solicitudes de candidatos sobre sus datos: [privacy.md](privacy.md), sección 4.

### Para quien continúe el desarrollo

- Arquitectura y decisiones: [architecture.md](architecture.md).
- Flujo: rama → PR → CI (ruff, pytest, pip-audit, build de Docker) → merge.
- Backlog recomendado, en orden de prioridad:
  1. Ejecutar la UAT con reclutadores ([uat-plan.md](uat-plan.md)) y el aviso de privacidad con asesoría legal.
  2. Paginar `GET /profiles` y usar un pool de conexiones ([performance.md](performance.md)).
  3. Ranking con IA asíncrono y con cuota por recruiter ([security-review.md](security-review.md), A04).
  4. Exponer la exportación CSV/PDF en la API y el dashboard (#42).
  5. Registrar el estado del candidato (preseleccionado, entrevistado, contratado) para medir *time-to-hire* y el embudo (#58).
  6. Mover el contador de intentos de login a PostgreSQL para poder usar varias réplicas de la API.

### Accesos y secretos que hay que transferir **(equipo)**

| Recurso | Dueño actual | Nuevo dueño | Transferido |
|---|---|---|---|
| Repositorio de GitHub y tablero de Projects | TomasPosada2 | | ☐ |
| Proyecto de Google Cloud (OAuth de Gmail) | | | ☐ |
| Llave de API de Anthropic | | | ☐ |
| Servidor o VM y dominio | | | ☐ |
| Webhook de alertas | | | ☐ |
| Ubicación de las copias externas de los backups | | | ☐ |
