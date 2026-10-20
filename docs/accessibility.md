# Auditoría de accesibilidad del dashboard — issue #59

Referencia: WCAG 2.1 nivel AA. Alcance: `dashboard/` (Streamlit), revisado
pantalla por pantalla: login, Inicio, Candidatos, Rankings, Vacantes,
Analítica, Notificaciones y Administración. Fecha: 2026-10-20.

## Hallazgos y correcciones

| Criterio WCAG | Hallazgo | Corrección | Estado |
|---|---|---|---|
| 1.3.1 Información y relaciones | Las tablas (`st.dataframe`) se dibujan en un canvas que los lectores de pantalla no pueden recorrer. | Interruptor **Tablas accesibles** en el menú lateral: muestra las tablas como `<table>` HTML (`mostrar_tabla` en `dashboard/ui_style.py`). | Corregido |
| 1.1.1 Contenido no textual | El gráfico de puntajes del ranking (Analítica) no tenía alternativa en texto. | Tabla con los mismos datos debajo de cada gráfico. | Corregido |
| 1.3.1 / 2.4.6 Encabezados | Los títulos saltaban de h1 (`st.title`) a h3 (`st.subheader`). | Las secciones usan h2 (`st.header`), con un tamaño ajustado por CSS. | Corregido |
| 3.1.1 Idioma de la página | Streamlit declara `lang="en"` y el lector de pantalla pronunciaba el español con reglas del inglés. | Se fija `lang="es"` al cargar la página. | Corregido |
| 2.2.1 Tiempo ajustable / 3.3.1 Identificación de errores | Al vencer la sesión (60 min) solo aparecía "Error HTTP 401". | Mensajes que dicen qué hacer: "Tu sesión expiró… vuelve a ingresar"; 403, 409, 422 y 429 con su propio texto. | Corregido |
| 3.3.1 Identificación de errores | Tras el bloqueo por intentos fallidos, el login decía "error HTTP 429". | "Demasiados intentos fallidos. Espera 15 minutos…" | Corregido |
| 2.4.7 Foco visible | Ya había un contorno de 3 px en botones, campos y radios (Sprint 6). | — | Verificado |
| 2.3.3 Animaciones | Ya se respetaba `prefers-reduced-motion` (Sprint 6). | — | Verificado |
| 1.4.10 Reflow | Las columnas pasan a una sola en pantallas de menos de 768 px; las tablas tienen desplazamiento propio (#60). | — | Verificado |
| 3.3.2 Etiquetas | Todos los campos tienen etiqueta visible; los *placeholders* solo dan ejemplos. | — | Verificado |
| 1.4.1 Uso del color | Los estados (éxito, aviso, error) siempre llevan texto, no solo color. El modo demostración se anuncia con texto ("RESULTADOS SIMULADOS"). | — | Verificado |
| 1.4.3 Contraste | Se usan los temas claro y oscuro de Streamlit; los bordes propios (#64748b sobre blanco) tienen 4,8:1. | — | Verificado |

## Limitaciones conocidas

| Limitación | Motivo | Mitigación |
|---|---|---|
| Los gráficos (`st.bar_chart`) no son navegables con teclado. | Componente de Streamlit (Vega-Lite). | Cada gráfico tiene su tabla equivalente. |
| No hay enlace "saltar al contenido". | Streamlit no permite modificar la estructura de la página. | La navegación está en el menú lateral, que es el primer bloque enfocable. |
| No se probó con usuarios de lector de pantalla. | Fuera del alcance técnico. | Incluir a una persona usuaria de NVDA o VoiceOver en la UAT (#68). |

## Cómo se verifica

- `tests/test_dashboard_app.py` ejecuta el dashboard completo sin navegador
  (`streamlit.testing`) y comprueba el cambio a tablas accesibles, los
  mensajes de sesión expirada y de bloqueo, y la navegación según el rol.
- Revisión manual recomendada en cada release: recorrer el login y la
  pantalla de Rankings solo con teclado (Tab / Shift+Tab / Enter / espacio).
