# ADR-0002 · Renderizado en el servidor con plantillas, Bootstrap 5 y HTMX

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `inventario`, `conteos`, `reportes`
- **Fuentes:** `readme.md` §2.1, §2.2, §2.5, §4.1 y §6 (TK-03, TK-04, HB-08 y criterios de revisión); `CLAUDE.md` ("Stack tecnológico estricto" y "Frontend y vistas")

## Contexto

Los usuarios trabajan desde una PC o un celular conectados a la wifi del hogar. El HTML debe llegar listo y rápido al celular, y la interactividad que hace falta es acotada: filtrar, buscar y paginar. Nginx aplica una política de seguridad de contenido (CSP) que bloquea el JavaScript en línea.

## Decisión

- Las páginas se **renderizan en el servidor** con plantillas de Django y **Bootstrap 5**.
- **HTMX** (2.0.x) actualiza fragmentos de página, como filtros, búsquedas y paginación, sin recargar la página completa. Si la petición viene de HTMX (`request.htmx`, de `django-htmx`), la vista responde solo el fragmento; si no, la página completa, para que la URL funcione sola, con el botón "Atrás" y al recargar.
- **Cero frameworks SPA** (React, Vue o Angular).
- **Sin JavaScript en línea**, para cumplir la CSP. Bootstrap y HTMX se sirven desde `static/`, no desde un CDN.
- ***Responsive*:** tarjetas `list-group` en el celular y tabla en el escritorio, sin desplazamiento horizontal a 390 px; un `<label>` en cada campo.
- **Doble envío en el MVP:** después de guardar se redirige (patrón *Post/Redirect/Get*) y el botón de enviar se desactiva al pulsarlo, sin tabla nueva.

## Alternativas consideradas

- **Una SPA:** descartada por la escala del problema (§2.1) y porque obligaría a descargar y compilar un *bundle* de JavaScript en el celular.

## Consecuencias

**Positivas:**
- En el celular, el HTML llega listo desde el servidor, sin descargar ni compilar un *bundle* de JavaScript (§2.1).
- CSRF por defecto en formularios y peticiones HTMX, y protección contra XSS por el *autoescape* de las plantillas (§2.5).

**Negativas:**
- No hay edición en tiempo real ni funcionamiento sin conexión (§2.1).
- Toda interactividad nueva tiene que resolverse con HTMX y sin JavaScript en línea.
