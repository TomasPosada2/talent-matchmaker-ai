# Pruebas de carga — Sprint 7, issue #62

Fecha: 2026-10-20. Entorno: Docker Desktop en Windows 11 (portátil de
desarrollo). Corre el stack completo de `docker-compose.yml`: PostgreSQL 16,
ClamAV 1.4 (clamd) y la API con un solo proceso de uvicorn.

```bash
docker compose run --rm api python scripts/load_test.py \
  --cvs 50 200 500 --api-url http://api:8000 --api-requests 500 --api-concurrency 20
```

El script genera CVs sintéticos (Faker), los pasa por el pipeline real
(escaneo ClamAV → extracción → estructuración → schema → PostgreSQL) y al
terminar borra los perfiles de prueba (prefijo `load_`).

## Pipeline de ingesta

| CVs | Exitosos | Duración | CVs/min | p50 por CV | p95 por CV | Máx. | Memoria pico |
|---|---|---|---|---|---|---|---|
| 50 | 50 | 6,6 s | 457 | 111 ms | 137 ms | 170 ms | 4,7 MB |
| 200 | 200 | 26,5 s | 454 | 113 ms | 141 ms | 306 ms | 5,2 MB |
| 500 | 500 | 65,6 s | 458 | 113 ms | 144 ms | 189 ms | 6,3 MB |

- **Escala de forma lineal:** el rendimiento se mantiene en unos 455 CVs/min
  y la latencia por CV no crece con el tamaño del lote.
- **Memoria estable:** el pipeline procesa un correo a la vez y no acumula
  documentos en memoria.
- **Capacidad:** el listener revisa Gmail cada 60 s con hasta 50 correos por
  ciclo, unos 7 s de trabajo. Le sobra capacidad para cualquier volumen
  realista de postulaciones.
- No incluye OCR: un CV escaneado como imagen pasa por Tesseract y tarda más.
  Los lotes de prueba son DOCX.

## API: `GET /profiles` con 520 perfiles

| Peticiones | Concurrencia | Errores | Req/s | p50 | p95 | Máx. |
|---|---|---|---|---|---|---|
| 500 | 20 | 0 | 24,7 | 810 ms | 1.046 ms | 1.553 ms |

Desglose de una petición aislada (62 ms en total):

| Parte | Tiempo |
|---|---|
| Abrir conexión a PostgreSQL | 8 ms (se hace dos veces: autenticación y consulta) |
| Buscar al recruiter del token | 9 ms |
| `listar_perfiles()` (520 filas JSONB) | 19 ms |
| Serializar la respuesta (331 KB) y el resto | ~18 ms |

**Conclusión:** con 20 clientes simultáneos las peticiones se encolan en el
único proceso de la API (p50 de 810 ms). Aun así no hubo errores, y 24
peticiones por segundo es unas 25 veces más de lo que genera un equipo de 10
recruiters navegando el dashboard.

## Riesgos detectados (backlog)

| Riesgo | Cuándo se vuelve problema | Recomendación |
|---|---|---|
| `GET /profiles` devuelve todos los perfiles (≈ 0,65 KB cada uno). | Con unos 5.000 perfiles la respuesta pasa de 3 MB y cada vista del dashboard tarda más de 1 s. | Paginar el endpoint y filtrar en SQL. Antes de eso, la purga de retención (#63) mantiene acotado el volumen. |
| Se abre una conexión nueva a PostgreSQL en cada consulta. | Con concurrencia alta. | Usar `psycopg_pool`. |
| Un solo proceso de uvicorn. | Si hay más de unos 20 usuarios simultáneos. | Añadir `--workers`, pero antes mover a PostgreSQL el contador de intentos de login, que hoy vive en memoria (`docs/security-review.md`, A07). |
| `POST /rankings` (Claude) es síncrono y puede tardar minutos con muchos candidatos. | Ya hoy, si se rankea todo el pool. | Ejecutarlo en segundo plano y notificar al terminar (la notificación por correo ya existe, #50). No se midió en esta prueba para no generar costo de API. |
