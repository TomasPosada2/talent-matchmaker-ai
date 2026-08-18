# Talent Matchmaker AI — Sprint Review

Equipo: Tomás Posada · Mateo Arango · Sara Jaramillo

## Product Goal

Reemplazar la preselección manual de candidatos —hoja de cálculo, memoria, criterio
informal— por un sistema que ingiere hojas de vida, extrae la información con
evidencia verificable y, más adelante, compara candidatos contra una vacante
devolviendo un ranking que se puede justificar línea por línea.

Ningún campo se inventa: si el dato no está en el documento de origen, queda en
`null`. Este principio de anti-alucinación es el criterio de aceptación de *todo*
el producto, no solo de un sprint puntual.

## Cómo funciona hoy (arquitectura de Sprint 1)

La bandeja de entrada se simula como una carpeta local (`data/inbox_simulado/`):
cada subcarpeta es un correo con su `metadata.json` y sus adjuntos. Esto valida
el pipeline completo sin depender de credenciales de Gmail/IMAP reales — la
interfaz de detección queda aislada para reemplazar esa simulación sin tocar el
resto del pipeline.

```
HU-01 Detección de correo con CV
   -> HU-02 Validar y extraer adjunto
   -> HU-03 Extraer texto (PDF/DOCX)
   -> HU-04/05 Estructurar + evidencia
   -> HU-06 Validar contra schema
```

`HU-07` orquesta el lote completo y mide la tasa de éxito. `HU-08` atrapa
errores en cada etapa para que un CV roto no tumbe el resto del lote.

## Sprint 1 — Sprint Goal (cerrado)

> "Demostrar que el sistema detecta un correo con CV adjunto, extrae el texto y
> devuelve un perfil estructurado en JSON donde cada campo apunta a su
> evidencia textual de origen, sobre un lote de prueba de 20 hojas de vida.
> No incluye ranking — sin ingesta ni parsing confiables, el matching es humo."

**Definition of Done**

- [x] Pipeline end-to-end (HU-01 a HU-08) corriendo sobre la bandeja simulada
- [x] Salida JSON validada contra un schema fijo (HU-06)
- [x] Cada campo extraído incluye su evidencia textual (HU-05)
- [x] Un CV roto no tumba el resto del lote (HU-08)
- [x] 9 pruebas unitarias automatizadas, 9/9 en verde
- [~] Tasa de éxito reportada — "válido contra el schema" no siempre es "correcto" (ver Sprint 2)

**Resultados verificados**

```
$ python run_batch.py
Total correos en bandeja:        25
Candidatos a procesar:           21
Procesados con éxito:            20
Fallidos:                        1
Ignorados (sin adjunto):         2
Descartados (formato inválido):  2
Tasa de éxito:                   95.2%

Casos fallidos:
  - email_025: CV escaneado sin texto legible (sin OCR en este sprint)
```

Corrido con semilla fija (42): coincide con el resultado de referencia
documentado en el README del proyecto.

## Sprint 2 — Proceso

Sprint Goal: dejar el Product Backlog **consolidado, refinado y corregido**.
Cómo se hizo:

1. **Documentar el cierre real de Sprint 1** — correr el pipeline de nuevo, no
   confiar solo en el README: 9/9 tests y las métricas del lote verificadas de
   primera mano.
2. **Auditar el código, no solo el reporte** — preguntar qué esconde un
   "20/20 exitoso": ¿el schema valida forma o valida verdad?
3. **Traducir cada hallazgo en una historia priorizada** — ningún defecto
   queda como comentario suelto.
4. **Revisar las limitaciones ya conocidas** — lo que el README listaba como
   "limitaciones" (OCR, heurística de nombre, Gmail/IMAP, dashboard) se vuelve
   backlog explícito.
5. **Consolidar todo en un único Product Backlog** priorizado.

### Hallazgos de la auditoría (paso 2)

El schema valida *forma*, no *verdad*. "JSON válido" no es lo mismo que "dato
correcto". Se encontraron dos defectos donde el pipeline reporta éxito con
datos equivocados:

**BUG-01 — 5 de los 20 "exitosos" tienen datos mezclados.**
Cuando el CV usa una tabla para la experiencia laboral, `text_extractor`
agrega el texto de las tablas *después* de todos los párrafos, sin respetar
su posición real en el documento. Resultado: `experiencia` queda en `null` y
ese contenido se cuela dentro de `habilidades`.

```
Afectados: email_004, email_008, email_012, email_016, email_020
habilidades.valor: "Power BI, Docker, R\nAsistente Administrativo\nBurbano-Castillo"
                                        ^ esto no son habilidades
```

**BUG-02 — El teléfono se puede "alucinar" desde un rango de años.**
El regex de teléfono acepta cualquier secuencia larga de dígitos. Si el CV no
trae teléfono pero sí un rango como `(2018-2021)`, el sistema lo reporta como
número de contacto.

```
texto: "...en ACME S.A. (2018-2021)"
telefono.valor: "2018-2021"   <- inventado
```

Ambos quedan priorizados **Alta** en el Product Backlog: construir el agente
de matching sobre datos con estos defectos propagaría el error.

## Sprint 2 — Sprint Goal (cerrado)

> "Dejar el Product Backlog de Talent Matchmaker AI consolidado, refinado y
> corregido: con el resultado de Sprint 1 documentado, los defectos
> encontrados en auditoría traducidos a historias priorizadas, y el trabajo
> futuro de matching/ranking desglosado y listo para planear."

**Definition of Done**

- [x] Resultado de Sprint 1 documentado con métricas verificadas (código corriendo, 9/9 tests)
- [x] Auditoría técnica de Sprint 1 realizada y convertida en historias de backlog (BUG-01, BUG-02)
- [x] Backlog priorizado por severidad e impacto (Alta / Media / Baja)
- [x] Trabajo futuro de matching (agente + tools) desglosado en historias con criterio de aceptación

## Product Backlog (consolidado)

| ID | Historia | Prioridad | Estado |
|---|---|---|---|
| HU-01…08 | Ingesta, extracción y estructuración trazable de CVs | — | Hecho · Sprint 1 |
| BUG-01 | Orden de tablas en DOCX rompe secciones (experiencia se pierde) | Alta | Backlog priorizado |
| BUG-02 | Regex de teléfono confunde rangos de años con números | Alta | Backlog priorizado |
| HU-09 | Estructurar la vacante (job description) como input del agente | Alta | Backlog priorizado |
| HU-10 | Tool: consultar los perfiles estructurados del Sprint 1 | Alta | Backlog priorizado |
| HU-11 | Tool: verificar si un requisito tiene evidencia real en el perfil | Alta | Backlog priorizado |
| HU-12 | Agent loop (Thought → Action → Observation) con límite de pasos | Alta | Backlog priorizado |
| HU-13 | Ranking final justificado con evidencia citada por candidato | Alta | Backlog priorizado |
| HU-14 | Manejo de errores del agente (tool falla, LLM alucina un requisito) | Media | Backlog priorizado |
| HU-15 | OCR para CVs escaneados como imagen | Media | Backlog futuro |
| HU-16 | Heurística de nombre más robusta ante plantillas atípicas | Media | Backlog futuro |
| HU-17 | Conexión real a bandeja de correo (Gmail/IMAP) | Baja | Backlog futuro |
| HU-18 | Panel/dashboard para reclutadores | Baja | Backlog futuro |

## Sprint 3 — Sprint Goal (inicia)

Construir un agente de matching que, apoyado en **tools** sobre los perfiles
trazables de Sprint 1, compare cada candidato contra una vacante y produzca un
**ranking explicable**. Cada decisión del agente debe poder justificarse con
la misma evidencia textual que ya exige Sprint 1, siguiendo el patrón de
*agent loop* (Thought → Action → Observation).

Arranca directo del backlog priorizado: BUG-01 y BUG-02 se cierran primero,
antes de construir matching sobre datos incorrectos.
