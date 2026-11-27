# Hook de secretos: límites aceptados y pendientes

`.claude/hooks/bloquear_secretos.py` revisa cada `git commit` y cada `git push` que ejecuta Claude, y los niega si entra un secreto, un correo, un dato personal o un `.env`. Qué bloquea y qué cuenta como ejemplo está en `CLAUDE.md` ("Datos que no salen del proyecto"). Este documento guarda lo que el hook **no** resuelve, para retomarlo con lo que traigan los tickets TK y HB-10.

## Por qué cada revisión le encuentra casos nuevos

Entre el commit `af5c714` y el `0d1dfba` hubo 3 revisiones adversariales del hook, y cada una encontró casos nuevos (PR #2):

| Revisión | Lo que encontró |
|---|---|
| `af5c714` | La lista de permitidos se compara por subcadena: `app-ci` dejaba pasar `hogar-app-cifrado1`. El hook no reconocía `PASSPHRASE` |
| `c2e88fd` | `gpg --passphrase valor` no se detectaba, la comilla invertida cortaba el valor, el correo de la lista se comparaba por subcadena y había un falso positivo con la prosa de una tabla (`` `DB_PASSWORD`: Contraseña de ... ``) |
| `0d1dfba` | Las frases en minúsculas o con espacios pasaban, el valor en la línea siguiente no se veía, `add_argument("--password", required=True)` se bloqueaba y la opción solo cubría 3 claves |

No es descuido de cada ronda. El hook decide, **línea por línea y con expresiones regulares**, si un texto es un secreto. Eso solo se puede hacer con certeza para los tokens con forma fija (claves privadas, AWS, GitHub, Anthropic, JWT...). Para todo lo demás (una contraseña asignada a `DB_PASSWORD`, una frase de paso), el valor no tiene forma propia, y lo que lo distingue de un ejemplo depende del contexto:

- **El tipo de archivo:** en Python, `DB_PASSWORD = clave` asigna una variable. En Markdown, `` `DB_PASSWORD`: clave de app_user `` es prosa. En un `.env`, `DB_PASSWORD=clave` es un valor real.
- **La forma del valor:** si va entre comillas, si es solo de minúsculas o si tiene espacios.
- **Las líneas de alrededor:** el valor puede estar en la línea siguiente, y el hook no la ve.

Cada regla que quita un falso positivo abre un hueco, y cada regla que cierra un hueco agrega falsos positivos. Por ejemplo:

- Tratar un valor en minúsculas como nombre de variable quitó los falsos positivos del código y de la prosa, pero deja pasar `--passphrase correcthorsebattery`.
- Evaluar completo un valor entre comillas atrapa `"mi frase de paso larga"`, pero bloquearía una frase de prosa entre comillas.

Son 2 tipos de error que se compensan, y no hay un punto en el que las 2 lleguen a cero. Por eso cada revisión encuentra casos de un lado o del otro, y lo seguirá haciendo.

**Consecuencia:** el hook es una red de seguridad, no una garantía. Las barreras reales son estas:
- los secretos nunca se escriben en el repositorio, porque viven en `.env`, fuera de Git (`.gitignore`);
- los scripts reciben las frases de paso por un descriptor o un archivo (`--passphrase-fd`, `--passphrase-file`), nunca como argumento (guía de HB-10);
- el PR se revisa;
- `secreto-ok` marca una excepción a propósito.

Cuando se cambie el hook, se decide qué error se acepta, y la decisión queda en un test.

## Límites aceptados

Estos casos pasan a propósito. `LIMITES_ACEPTADOS` de `tests/test_bloquear_secretos.py` los fija: si un cambio cierra alguno, el test falla, y entonces se quita de la lista y de esta tabla.

| Límite | Ejemplo que pasa | Por qué se acepta |
|---|---|---|
| Un valor sin comillas y solo de minúsculas | `gpg --passphrase correcthorsebattery` | No se distingue de un nombre de variable (`"--passphrase", frase`) ni de una palabra de la prosa. Entre comillas sí se bloquea |
| El valor en otra línea | `"--passphrase",` y el valor en la línea siguiente, o una continuación con `\` | El hook revisa línea por línea, como llegan en el `diff`. Para verlo haría falta analizar el archivo completo |
| Una comilla en medio de un valor sin comillas | `DB_PASSWORD=ab` seguido de una comilla invertida y el resto | El valor se corta en la comilla, como con las comillas simples y dobles, y quedan menos de 8 caracteres |
| Una palabra con mayúscula inicial seguida de más texto | `` `DB_PASSWORD`: Hogarseguro y ... `` | Es la forma de la prosa en las tablas de la documentación (`` `CLAVE`: Contraseña de ... ``). Un valor solo, sin texto detrás, sí se bloquea |
| Valores que empiezan por `-`, `/`, `./`, `../` o `~/`, o con la forma `nombre=...` | `--private-key ./llave.pem`, `required=True)` | Son otra opción, una ruta o un argumento con nombre, no el valor de la clave |
| Claves con otro nombre | `CLAVE=...`, `CONTRASENA=...`, `FRASE=...` | El hook solo reconoce los nombres en inglés de `CLAVES` (`PASSWORD`, `PASSPHRASE`, `SECRET`, `TOKEN`, `API_KEY`...), que son los que usa el proyecto (`.env.example`) |
| La lista de permitidos se compara por subcadena, salvo los correos | Una entrada corta dejaría pasar cualquier valor que la contenga | Por eso solo admite valores públicos completos y largos (`CLAUDE.md`). Hoy solo tiene un correo, que se compara completo |

## Pendientes

Se retoman cuando los tickets traigan código nuevo, porque cada uno agrega formas de escribir claves que hoy no existen en el repositorio:

| Pendiente | Cuándo | Cómo se cierra |
|---|---|---|
| Revisar el hook con el código real de cada ticket. Por ejemplo, la configuración de TK-01 y TK-02, los tests de servicios con sus usuarios o los scripts de respaldo de HB-10 | Al cerrar cada TK y HB-10 | Si el hook bloquea una línea legítima o la revisión encuentra un valor que pasó, se agrega el caso a `BLOQUEA`, `PERMITE` o `LIMITES_ACEPTADOS`, y a este documento |
| Nombres de clave en español (`CLAVE`, `CONTRASENA`, `FRASE`) | Si algún ticket los introduce | Agregarlos a `CLAVES`, con sus tests. Hoy no hace falta: las variables del proyecto están en inglés |
| Un escáner dedicado en el CI, como `gitleaks` o `detect-secrets`, con entropía y archivos completos | Después del MVP, o antes si un límite de la tabla deja pasar algo real | Decidirlo con un ADR (una dependencia más y su versión fija), como complemento del hook: el hook revisa antes del commit y el escáner, en el PR |
| Los scripts de HB-10 reciben las frases de paso por `--passphrase-fd` o `--passphrase-file`, nunca como argumento | Al escribir los scripts (HB-10, parte A) | Revisión del PR de HB-10. La guía ya lo hace así en el código de referencia |

## Cómo se cambia el hook

1. **Primero los tests**, en `tests/test_bloquear_secretos.py`: el caso que debe bloquearse va en `BLOQUEA` (con `# secreto-ok`, para que el propio hook deje commitear el test), el que debe pasar va en `PERMITE` y el límite que se acepta va en `LIMITES_ACEPTADOS`. Se comprueba que fallen: `python -m pytest tests/test_bloquear_secretos.py`.
2. **El cambio** en `bloquear_secretos.py`, hasta el verde de `python -m pytest tests` y `python scripts/verificar.py --herramientas`.
3. **Todo el repositorio:** `python .claude/hooks/bloquear_secretos.py --escanear-repo` debe terminar en `0 hallazgo(s)`. Si encuentra algo, el cambio produjo un falso positivo (o descubrió un dato real).
4. **Este documento**, si cambia un límite o se cierra un pendiente.
