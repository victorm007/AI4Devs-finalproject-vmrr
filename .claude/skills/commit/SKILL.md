---
name: commit
description: Resume los cambios en staging (git diff --staged), redacta un mensaje tipo(scope): descripción en español y hace el commit directamente. Usar cuando el usuario pida /commit o "commitea lo que está en staging".
---

# Commit de lo que está en staging

1. Ejecuta `git diff --staged --stat` y `git diff --staged`.
   - Si no hay nada en staging, detente y avísalo (no hagas `git add` por tu cuenta).
2. Ejecuta `git branch --show-current`. Si es `main`, detente: el trabajo va en ramas `feature/*`.
3. Resume el cambio en 1–3 líneas para el usuario.
4. Redacta el mensaje:
   - Formato: `tipo(scope): descripción`.
   - `tipo` ∈ feat | fix | refactor | docs | test | chore.
   - `scope`: la app o área afectada (`inventario`, `api`, `ci`, `readme`…); omítelo (`docs: ...`) si el cambio es transversal.
   - Descripción en español, imperativo/presente, minúscula inicial, sin punto final, ≤ 72 caracteres en la primera línea.
   - Cuerpo opcional (tras una línea en blanco) solo si el cambio necesita explicar el porqué.
   - Termina con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
5. Commitea directamente, sin pedir confirmación, pasando el mensaje con heredoc (Bash):

   ```bash
   git commit -F - <<'EOF'
   tipo(scope): descripción

   Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
   EOF
   ```

   - No uses `--no-verify` ni `--amend`. Si un hook falla, informa el error y no reintentes saltándolo.
6. Muestra `git log --oneline -1` como confirmación. No hagas push.
