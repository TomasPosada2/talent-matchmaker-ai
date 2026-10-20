# Plan de pruebas de aceptación con reclutadores (UAT) — issue #68

**Estado: plan listo; falta ejecutar las sesiones.** Las sesiones requieren
reclutadores reales y no se pueden automatizar. Este documento deja todo
preparado para correrlas y registrar el resultado.

## 1. Objetivo

Confirmar, con personas que reclutan en su día a día, que el sistema:

1. reemplaza la preselección manual sin perder candidatos relevantes;
2. produce rankings cuyas justificaciones el reclutador entiende y comparte;
3. se puede usar sin capacitación técnica.

## 2. Participantes y preparación

- **Participantes:** 3 a 5 reclutadores. Al menos uno debería usar lector de
  pantalla o navegar solo con teclado (ver [accessibility.md](accessibility.md)).
- **Duración:** 45 minutos por sesión; un facilitador y un observador que
  toma notas.
- **Entorno:** el stack desplegado ([runbook.md](runbook.md)) con los datos
  de `scripts/seed_demo.py`. Solo CVs sintéticos: **no usar CVs reales**
  mientras no exista el aviso de privacidad ([privacy.md](privacy.md)).
- **Cuentas:** un usuario recruiter por participante, creado desde
  **Administración**.
- **Antes de cada sesión:** el participante clasifica a mano 10 CVs del lote
  de demostración contra la vacante de ejemplo ("Analista de datos (demo)").
  Esa clasificación es la referencia para el escenario 4.

## 3. Escenarios

| # | Tarea para el participante | Criterio de aceptación |
|---|---|---|
| 1 | Inicia sesión con la cuenta entregada. | Lo logra sin ayuda en menos de 1 minuto. |
| 2 | Encuentra a los candidatos que saben Python y tienen experiencia como analistas. | Usa los filtros y llega a la lista correcta sin ayuda. |
| 3 | Crea la vacante "Desarrollador Backend" con 4 requisitos. | La plantilla queda guardada y aparece en **Plantillas guardadas**. |
| 4 | Genera el ranking de "Analista de datos (demo)" (modo demostración; modo IA si hay llave). Compara el top 5 con su clasificación manual. | Al menos 4 de los 5 primeros coinciden con su top 5, o el participante acepta la diferencia después de leer la evidencia. |
| 5 | Abre el primer candidato y explica por qué quedó primero. | Lo explica solo con la evidencia mostrada, sin abrir el CV. |
| 6 | Encuentra un requisito que el primer candidato **no** cumple. | Lo identifica en "Requisitos sin evidencia". |
| 7 | Revisa la analítica y nombra la habilidad más común. | Responde correctamente. |
| 8 | (Solo admin) Crea una cuenta y elimina los datos de un candidato. | Completa ambas tareas y entiende que la supresión no se puede deshacer. |
| 9 | Repite los escenarios 1 a 3 desde un celular. | Puede completarlos (diseño responsive, #60). |

## 4. Medición

Por cada escenario se registra: completado (sí / con ayuda / no), tiempo y
comentarios literales. Al final, el participante responde:

| Pregunta | Escala |
|---|---|
| ¿Confiarías en este ranking para decidir a quién entrevistar? | 1 (nada) – 5 (totalmente) |
| ¿La evidencia mostrada es suficiente para justificar la decisión ante tu jefe? | 1 – 5 |
| ¿Cuánto tiempo crees que te ahorraría por vacante? | Minutos (abierta) |
| ¿Qué te falta para usarlo en tu trabajo real? | Abierta |
| System Usability Scale (SUS), 10 preguntas estándar | 0 – 100 |

## 5. Criterios de salida (go / no-go)

El sistema pasa la UAT si:

- [ ] Los escenarios 1 a 7 se completan sin ayuda en al menos el 80 % de los intentos.
- [ ] El promedio de "¿confiarías en este ranking?" es 4 o más.
- [ ] El SUS promedio es 68 o más (por encima del promedio de la industria).
- [ ] No queda abierto ningún defecto de severidad alta.

Cada defecto encontrado se registra como issue en GitHub con la etiqueta
`uat` y su severidad.

## 6. Registro de sesiones

| Fecha | Participante (rol) | Escenarios completados | Confianza (1-5) | SUS | Defectos abiertos |
|---|---|---|---|---|---|
| | | | | | |

**Decisión final (go / no-go):** _pendiente_ — Firma del Product Owner: ________
