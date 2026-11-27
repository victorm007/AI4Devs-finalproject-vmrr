---
name: implementar-ticket
description: Procedimiento obligatorio para implementar un ticket HB o TK, o cualquier cambio de backend, frontend, infraestructura o configuración de la aplicación. Explora, propone un plan con las piezas de contrato y se detiene a esperar aprobación. Después escribe los tests con test-writer, comprueba el rojo, los congela por su huella, implementa con implementer hasta el verde, comprueba la huella y cierra sin commitear. Usar siempre que una tarea toque la aplicación, aunque nadie lo pida.
argument-hint: "[HB-NN | TK-NN | descripción del cambio]"
---
# Un ticket, de la spec al verde

Este orden no se cambia: **explorar → plan → (aprobación) → tests → rojo → congelar → implementar → verde → huella intacta → cierre**.

`<tmp>` es el directorio temporal de la sesión. El shell no conserva funciones, así que cada comando define lo que usa:

```bash
set -a && . ./.env && set +a
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
```

## 0. Antes de empezar

- Rama: la que indica la sección Git de `CLAUDE.md`.
- Apunta `git status --short`: esos cambios no son de esta tarea y nadie los toca.
- Elige el perfil. Si el ticket mezcla perfiles, aplica los dos.

| Perfil | Tickets | Tests | Rojo y verde |
|---|---|---|---|
| Infraestructura | HB-01 a HB-04 | HB-01 y HB-02: `<tmp>/<ticket>/verificacion.sh`, fuera del repositorio. HB-03 y HB-04: pytest (`infra`) y comandos | El script o `dtest` |
| Backend | HB-05 a HB-07, TK-01, TK-02, API y servicios | `test_modelos`, `test_esquema`, `test_privilegios`, `test_services`, `test_concurrencia`, `test_selectors`, contratos con `jsonschema` | `dtest <rutas>` |
| Frontend | HB-08, HB-09, TK-03 y pantallas | `test_views_*`, `test_admin*`, `test_templatetags`, `app/e2e/` | `dtest <rutas>` y Playwright |
| Operación | HB-10 | Parte A: `tests/test_respaldos.py`, `tests/test_candado.py` y el caso de ShellCheck de `tests/test_verificar.py`, en el equipo y fuera de `web` (los scripts corren en el *host* y hablan con `docker compose`). Partes B y C: los comandos de la sección 5 de la guía, en el servidor y en la máquina de la demo | `python -m pytest tests/test_respaldos.py tests/test_candado.py tests/test_verificar.py`; las partes B y C no tienen rojo de pytest |

## 1. Explorar

Lee la ficha del ticket y las secciones aplicables de `readme.md`, el cambio de OpenSpec (`openspec/changes/<id>-*`) si existe, la guía completa, los ADR aceptados que apliquen, los puntos de integración y el código y los tests que ya existen.

El código de las guías nunca se ha ejecutado. Si la guía contradice al readme, manda el readme y se avisa.

Fija las **piezas de contrato**, los nombres que los tests y la implementación deben compartir:

| Perfil | Piezas de contrato |
|---|---|
| Infraestructura | Servicios, redes, volúmenes y puertos; variables de entorno; roles de BD; nombres de settings; cabeceras; comandos con su salida esperada |
| Backend | Tablas, columnas y tipos; nombres exactos de `ck_`, `uq_`, `ex_`, `fk_`, `ix_`, `fn_`, `tg_` y `v_`; módulo y firma de cada función pública; excepciones con su `code` y mensaje literal; datos del mock; rol con el que corre cada test |
| Frontend | Nombre de URL y ruta; vista, plantillas y permiso; claves del contexto; campos del formulario; textos visibles literales; `id`, `data-test` y cabeceras HTMX; usuarios del mock |
| Operación | Scripts, sus opciones y códigos de salida; variables `RESPALDO_*` y `RESTAURAR_BASE`; mensajes de error literales; bases auxiliares (`hogar_ensayo`); *targets* del `Makefile`; rutas del servidor (`/opt/hogar`, `/var/backups/hogar`, `/mnt/respaldos`) |

## 2. Plan, y DETENTE

**Si falta el cambio de OpenSpec, créalo antes de esta parada con la skill `/openspec-propose`**, con el nombre `<id-en-minúsculas>-<slug>`, y valídalo con `openspec validate <cambio> --strict`. Es lo único que se escribe antes de la aprobación. Ignora la invitación final de esa skill a aplicar el cambio: después de la aprobación se sigue con el paso 3, nunca con `/openspec-apply-change`.

Presenta:

1. **Tabla de pasos:** paso de la guía → responsable (`implementer` en preparación, `test-writer` o `implementer`) → archivos → comando de verificación.
2. **Tabla de cobertura:** Scenario o criterio → test → rojo esperado.
3. **Lista de archivos que se congelarán**, incluidos `conftest.py`, `pruebas.py` y tests de otras apps.
4. **Tests que nacen en verde o se omiten,** con su motivo y cómo se validarán.
5. **Piezas de contrato,** ADR y puntos de integración afectados.
6. **Decisiones abiertas y lo que queda fuera.**
7. **Comandos destructivos del cierre.** Si la sección 5 de la guía pide `docker compose down -v`, decláralo aquí y di que borra la base local.

**Detente y espera la aprobación explícita.** Sin ella no lances subagentes ni crees código o tests. Si piden cambios, actualiza el plan y el cambio de OpenSpec y vuelve a detenerte.

## 3. Tests: subagente `test-writer`

Si la guía pone preparación antes del rojo (dependencias, `Makefile`), lanza primero `implementer` limitado a esos pasos.

Copia la sección 3 de la guía a `<tmp>/<ticket>/encargo-tests.md`. En HB-01 y HB-02 copia también la sección 5, porque la tabla de la sección 3 remite a sus comandos. Lanza `test-writer` en primer plano con ese archivo, el cambio de OpenSpec, la tabla de cobertura, las piezas de contrato y las rutas permitidas. No le pases la sección 2 de la guía.

Al volver, revisa que cada Scenario tenga su test y ejecuta `python scripts/verificar.py --corregir` **antes de congelar**. Después de congelar ya no se usa `--corregir` sin indicar archivo.

## 4. Comprueba el rojo

Ejecuta cada archivo por separado: un error de recolección oculta los demás.

- Cada test nuevo debe fallar **por el motivo esperado**. Muestra el motivo.
- Un error de importación solo vale como rojo inicial.
- Un test que pasa sin estar declarado en el plan **detiene el proceso** y vuelve a `test-writer`.
- Un test omitido no cuenta como rojo.
- Los tests que ya existían siguen en verde. Si alguno ya fallaba antes de empezar, apúntalo.

## 5. Congela

```bash
git add -- <archivos del plan>
sha256sum <archivos del plan> | tee <tmp>/<ticket>/congelados.sha256
```

En HB-01 y HB-02 se congela solo `verificacion.sh`, sin `git add`. Muestra la huella en el chat y marca en `tasks.md` las tareas de tests y de rojo ya comprobadas.

## 6. Implementación: subagente `implementer`

Lánzalo en primer plano con el plan aprobado, las piezas de contrato, la lista congelada, los cambios ajenos y la tabla de avance de la guía. Trabaja hasta el verde; en HB-01 y HB-02, el verde es `verificacion.sh`.

Si `implementer` reporta que necesita recrear el volumen, ejecuta tú `docker compose down -v`, solo si el plan aprobado lo declara.

**Disputas:** llévalas tal cual a quien aprobó el plan. Si se aceptan, `test-writer` corrige el test y se repiten los pasos 4 y 5. Ni tú ni `implementer` cambian un test congelado.

## 7. Verde y huella intacta

```bash
sha256sum -c <tmp>/<ticket>/congelados.sha256
git diff --stat -- <archivos del plan>      # vacío
git status --short -- 'app/**/tests/**' 'app/**/conftest.py' 'app/e2e/**' app/pruebas.py   # nada fuera del plan
git diff -- app/pyproject.toml              # sin cambios en pytest ni en coverage
```

Después ejecuta tú la suite: `dtest -m "not e2e and not lento" --cov=apps --cov-fail-under=80`, más `-m lento` y Playwright si el ticket los usa. En HB-01 y HB-02 la suite es `bash <tmp>/<ticket>/verificacion.sh`, porque todavía no existen `dtest` ni la cobertura. En HB-10 (perfil Operación) la suite es `python -m pytest tests -q` más los comandos de la sección 5 de su guía, y el `git status --short` de la huella mira también `tests/` y `scripts/`. Valida los tests de regresión como indique la guía. **Si la huella no cuadra, el ticket no está terminado aunque todo esté en verde.**

## 8. Cierre

1. Si la guía pide permiso de ejecución para un script, como `db/init/01_roles.sh` en HB-01, ejecuta tú sus comandos `git add` y `git update-index --chmod=+x`, y comprueba `100755` con `git ls-files -s <script>`.
2. Ejecuta la sección 5 de la guía y marca la sección 6. `docker compose down -v` solo se ejecuta si el plan aprobado lo declara; si no lo declaró, no lo ejecutes y repórtalo como pendiente. Solo lo ejecutas tú, nunca un subagente.
3. Ejecuta `python scripts/verificar.py` y, desde HB-03, `dj makemigrations --check --dry-run`.
4. Desde HB-03, comprueba el umbral de cobertura del ticket. Si cambia la API, ejecuta `npx @redocly/cli lint docs/api/openapi.yaml`.
5. Confirma que `readme.md` está al día y que todas las tareas de `tasks.md` están marcadas.
   Ejecuta también `python .claude/hooks/bloquear_secretos.py --escanear-repo`. Si encuentra algo en el código nuevo, cambia el dato o, si es un ejemplo legítimo, lleva el caso a `docs/herramientas/hook-secretos.md` (pendientes) y repórtalo. Haz lo mismo si en el ticket viste un valor real que el hook dejó pasar. No cambies el hook dentro del ticket.
6. Ejecuta `/openspec-verify-change <cambio>`. Es una revisión adicional: no reemplaza la huella ni la suite. Si reporta un hallazgo crítico, vuelve al paso 6 con `implementer` y repite el paso 7.
7. Ejecuta `/openspec-archive-change <cambio>` y elige sincronizar las specs. Solo se archiva si no quedan disputas, hallazgos críticos ni comprobaciones pendientes; si quedan, deja el cambio sin archivar y repórtalo.
8. Informa: paso → archivos; Scenario → rojo → verde; huella; salida de la sección 5; resultado de la verificación y del archivado; disputas; desviaciones de la guía; lo que no se pudo comprobar.

Esta skill **no hace commit, push ni PR**. Las guías dicen "Haz un commit al terminar cada paso", pero aquí no aplica: esos commits dejarían la historia con commits rotos, con tests en rojo o pasos a medias (ancla de `CLAUDE.md`). Los tests congelados quedan en staging y los commits siguen la sección Git.
