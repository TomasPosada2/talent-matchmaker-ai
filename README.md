# Talent Matchmaker AI — Sprint 1

Implementación del **Sprint 1** del proyecto *Talent Matchmaker AI*.

**Meta del sprint:** demostrar que el sistema detecta un correo con CV adjunto,
extrae el texto y devuelve un perfil estructurado en JSON donde cada campo
apunta a la evidencia textual de origen, sobre un lote de prueba de 20 hojas
de vida. **No incluye ranking** — sin ingesta ni parsing confiables, el
matching es humo.

## Arquitectura (mapeada a las historias de usuario)

```
Bandeja simulada (carpeta local)
        │
        ▼
HU-01  email_detector.py       → detecta correos con adjunto CV válido
        │
        ▼
HU-02  attachment_handler.py   → valida y extrae el adjunto (tamaño, corrupción)
        │
        ▼
HU-03  text_extractor.py       → extrae texto de PDF/DOCX en orden
        │
        ▼
HU-04/05 profile_structurer.py → estructura campos + evidencia textual
        │
        ▼
HU-06  schema.py                → valida el JSON contra un esquema fijo
        │
        ▼
HU-07  pipeline.py (procesar_lote) → corre todo sobre el lote, mide tasa de éxito
        │
HU-08  manejo de errores integrado en cada etapa (no se cae el lote completo)
```

## Por qué "bandeja simulada" y no Gmail/IMAP real

Para el Sprint 1 se decidió simular la bandeja como una carpeta local
(`data/inbox_simulado/`), donde cada subcarpeta representa un correo con su
`metadata.json` (remitente, asunto, adjuntos) y los archivos adjuntos reales.
Esto permite validar el pipeline completo end-to-end sin depender de
credenciales de correo real. La interfaz de `email_detector.py` está aislada
para que, en un sprint futuro, solo haya que reemplazar cómo se listan los
"correos" (ej. usando la API de Gmail o IMAP) sin tocar el resto del pipeline.

## Estructura del proyecto

```
talent_matchmaker/
├── src/
│   ├── email_detector.py       # HU-01
│   ├── attachment_handler.py   # HU-02
│   ├── text_extractor.py       # HU-03
│   ├── profile_structurer.py   # HU-04, HU-05
│   ├── schema.py                # HU-06
│   └── pipeline.py              # HU-07, HU-08 (orquestador)
├── scripts/
│   └── generate_sample_inbox.py # genera 25 correos de prueba (20 CVs válidos + 5 casos borde)
├── tests/
│   └── test_pipeline.py         # 9 pruebas unitarias
├── data/
│   ├── inbox_simulado/          # se genera al correr el script
│   └── salida/                  # reporte_lote.json y perfiles.json
├── run_batch.py                 # punto de entrada
└── requirements.txt
```

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

### 1. Generar la bandeja simulada de prueba (20 CVs + 5 casos borde)

```bash
python scripts/generate_sample_inbox.py
```

Genera CVs sintéticos (datos ficticios vía Faker) en 4 plantillas distintas,
más casos borde: 2 correos sin adjunto, 2 con formato no soportado (.jpg),
1 con un .docx vacío.

### 2. Correr el pipeline completo (HU-07)

```bash
python run_batch.py
```

Imprime en consola el reporte de la corrida y guarda:
- `data/salida/reporte_lote.json` — métricas + detalle de fallos
- `data/salida/perfiles.json` — todos los perfiles estructurados válidos
- `data/salida/adjuntos_extraidos/` — copia trazable de cada adjunto procesado

### 3. Correr las pruebas unitarias

```bash
pip install pytest
python -m pytest tests/ -v
```

## Resultado de referencia sobre el lote de prueba

Con la bandeja generada por `generate_sample_inbox.py` (25 correos: 20 CVs
válidos + 5 casos borde), el pipeline reporta:

- **20/20** CVs válidos procesados con éxito (tasa de éxito sobre candidatos: ~95%,
  ya que se incluye a propósito 1 caso borde adicional — un .docx vacío — que
  falla de forma controlada, sin tumbar el resto del lote).
- 2 correos ignorados por no tener adjunto.
- 2 correos descartados por formato no soportado (.jpg).

## Formato de salida (schema fijo, ver `src/schema.py`)

```json
{
  "email_id": "email_001",
  "archivo_origen": "email_001__cv_1.docx",
  "nombre": {"valor": "María Torres", "evidencia": "María Torres"},
  "contacto": {
    "email": {"valor": "maria@example.com", "evidencia": "maria@example.com"},
    "telefono": {"valor": "3001234567", "evidencia": "3001234567"}
  },
  "educacion": {"valor": null, "evidencia": null},
  "experiencia": {"valor": "...", "evidencia": "..."},
  "habilidades": {"valor": "...", "evidencia": "..."}
}
```

Principio clave: si un campo no está presente en el texto del CV, queda en
`null`. El sistema **nunca inventa información** ni evidencia que no exista
literalmente en el documento origen.

## Extracción de campos: enfoque del Sprint 1

La estructuración (HU-04/HU-05) usa **reglas y expresiones regulares**
(detección de encabezados de sección + regex para email/teléfono), no un LLM.
Esto es intencional para el Sprint 1: primero se valida que la ingesta y el
parsing sean confiables y trazables sobre datos reales/sintéticos antes de
invertir en matching o ranking (que quedan fuera de este sprint, según la
meta definida).

## Limitaciones conocidas (para backlog de sprints futuros)

- No hay soporte de OCR: un CV escaneado como imagen se marca "no procesable"
  (HU-08), no se descarta el pipeline pero tampoco se extrae su contenido.
- La heurística de "nombre" (primera línea válida) puede fallar con plantillas
  de CV muy atípicas.
- No hay conexión a correo real (Gmail/IMAP) todavía — queda para un sprint
  posterior si el negocio lo requiere.
- No incluye ranking ni matching semántico (fuera del alcance de este sprint).
