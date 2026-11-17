---
name: push
description: Hace un git push seguro de la rama de trabajo actual (sin force, sin tocar main, verificando antes) y, con el argumento "pr", crea su pull request o actualiza el existente. Usar solo cuando el usuario lo pida, con /push, /push pr, "haz push", "sube la rama", "abre el PR" o "actualiza el PR".
---

# Push seguro y PR de la rama de trabajo

Solo se ejecuta **por petición del usuario**: nunca hagas push por tu cuenta al terminar otra tarea.

- `/push`: sube los commits de la rama actual. Si la rama ya tiene un PR abierto, el push lo actualiza y se deja un comentario con los commits nuevos.
- `/push pr`: lo mismo y, además, crea el PR si no existe, o actualiza su descripción si ya existe.

Reglas que nunca se rompen:
- No hagas push a `main` (ni a `master`), ni con la cabeza separada (*detached HEAD*).
- No uses `--force`, `--force-with-lease`, `+refspec`, `--all`, `--mirror`, `--tags` ni `--no-verify`. Si el usuario pide un force explícitamente, explícale el riesgo y usa solo `--force-with-lease`, y solo sobre su rama de trabajo.
- No hagas `git add`, `commit`, `rebase`, `merge` ni `pull` por tu cuenta: si hacen falta, propónlos y espera la respuesta.
- El hook `bloquear_secretos.py` revisa cada push. Si bloquea, sigue las reglas de `CLAUDE.md` (se cambia el dato, nunca se esquiva el hook) y no reintentes con el mismo contenido.

## 1. Estado de la rama

1. `git branch --show-current`. Detente si está vacío (*detached HEAD*), o si es `main` o `master`: el trabajo va en ramas `feature/*`.
2. `git remote get-url origin`. Detente si no hay `origin`.
3. `git status --short`. Si hay cambios sin commitear, avisa que **no** van en el push y sugiere `/commit`; continúa con los commits que ya existen.

## 2. Sincronizar sin reescribir

1. `git fetch origin --prune`.
2. Si existe `origin/<rama>`, cuenta lo que falta en cada lado: `git rev-list --left-right --count origin/<rama>...HEAD` (izquierda = commits del remoto que no tienes; derecha = los tuyos por subir).
   - **Remoto adelantado** (izquierda > 0): detente. Alguien subió commits que no tienes; propón `git pull --rebase origin <rama>` y espera confirmación.
   - **Nada que subir** (derecha = 0): dilo. Con `pr`, sigue al paso 5; si no, termina.
3. `git rev-list --count HEAD..origin/main`. Si es mayor que 0, avisa que la rama no está al día con `main`, que es un criterio de *merge* (readme, 7.3), y sugiere `git rebase origin/main`. No lo hagas tú.

## 3. Revisión previa

1. Muestra lo que se va a subir: `git log --oneline <base>..HEAD` y `git diff --stat <base>..HEAD`, con `<base>` = `origin/<rama>` si existe, o `origin/main` si la rama es nueva.
2. Corre `python scripts/verificar.py` (lo mismo que el *job* `lint` del CI):
   - Código 0: sigue.
   - Código 1 (errores de lint o de formato): detente y muestra los errores. Se corrigen con `python scripts/verificar.py --corregir` y un commit nuevo.
   - Código 3 (no hay ruff ni djLint): detente si el rango toca `app/` (`.py`, `.html` o `pyproject.toml`) y pide levantar el contenedor `web`; si no lo toca, sigue.

## 4. Push

- Sin upstream: `git push -u origin <rama>`. Con upstream: `git push origin <rama>`. Solo esa rama.
- Si el push es rechazado (*non-fast-forward*), no fuerces: vuelve al paso 2.2.
- Muestra el resultado: el rango subido y la rama remota.

## 5. Pull request (necesita GitHub CLI)

1. Comprueba `gh --version` y `gh auth status`.
   - **Si `gh` no está o no tiene sesión:** no intentes otra vía. Arma la URL de comparación a partir de `origin` (`https://github.com/<dueño>/<repo>/compare/main...<rama>?expand=1`). Con `pr`, escribe además el cuerpo del PR (punto 3) en un archivo del directorio temporal de la sesión y da su ruta completa. Indica cómo habilitarlo: `winget install --id GitHub.cli` y `gh auth login`. Termina.
2. `gh pr view <rama> --json number,url,state,title`:
   - **Abierto:** el push ya lo actualizó. Si subiste commits, agrega un comentario con la lista (`gh pr comment <n> --body-file -`). Con `pr`, regenera la descripción completa (`gh pr edit <n> --body-file <archivo>`) para que cubra todos los cambios de la rama.
   - **Cerrado o fusionado:** no lo reabras ni crees otro sobre la misma rama. Avísalo y pregunta cómo seguir.
   - **No existe:** sin `pr`, solo informa que la rama no tiene PR y que `/push pr` lo crea; el PR se abre una sola vez, al terminar la unidad de trabajo (`CLAUDE.md`). Con `pr`, créalo:
     ```bash
     gh pr create --base main --head <rama> --title "<tipo>(<scope>): <qué hace> (TK-NN)" --body-file <archivo>
     ```
3. **Cuerpo del PR:** la plantilla `.github/pull_request_template.md` llena por completo y en español: ticket e historia, qué cambia y por qué, cómo probarlo, tabla de archivos, puntos de integración y checklist marcado con lo que de verdad se cumplió. Borra los comentarios y las secciones que no apliquen.
   - Sin secretos ni datos personales. Escribe entre comillas invertidas cualquier `@algo` que no sea un usuario real de GitHub.
   - Termina con la línea `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
4. **Revisión adversarial** (después de crear el PR o de subir commits nuevos a uno abierto): invoca el subagente `adversarial-reviewer`. No tiene Bash, así que pásale la lista de archivos cambiados y el diff (`gh pr diff <n>`). Pídele que contraste el cambio con los ADR aceptados de `docs/adr/` y con los escenarios de `openspec/specs/` y del cambio de OpenSpec del ticket; mientras `openspec/specs/` no tenga specs, también con los criterios de aceptación del readme (secciones 5 y 6) y la guía del ticket. Registra sus hallazgos como comentario del PR (`gh pr comment <n> --body-file -`), como pide el readme (7.2).

## 6. Respuesta

- Si creaste o actualizaste un PR, responde **solo con su URL**: el resumen está en el PR (`CLAUDE.md`).
- Si solo hiciste push, responde en 1 a 3 líneas: la rama, cuántos commits subiste y los avisos que haya, como cambios sin commitear o la rama atrasada respecto de `main`.
