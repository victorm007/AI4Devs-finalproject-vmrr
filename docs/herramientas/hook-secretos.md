# Hook de secretos: límites aceptados y pendientes

`.claude/hooks/bloquear_secretos.py` revisa cada `git commit` y cada `git push` que ejecuta Claude, y los niega si entra un secreto, un correo, un dato personal o un `.env`. Qué bloquea y qué cuenta como ejemplo está en `CLAUDE.md` ("Datos que no salen del proyecto"). Este documento guarda lo que el hook **no** resuelve, para retomarlo con lo que traigan los tickets TK y HB-10.

## Por qué cada revisión le encuentra casos nuevos

En el PR #2, el hook pasó 4 revisiones adversariales seguidas. Cada una encontró casos nuevos, y cada arreglo se hizo en el commit siguiente:

| Revisión del commit | Lo que encontró | Arreglado en |
|---|---|---|
| `af5c714` | La lista de permitidos se compara por subcadena: `app-ci` dejaba pasar `hogar-app-cifrado1`. El origen era otro: en Markdown, la comilla invertida queda pegada al valor y el marcador `ci` dejaba de reconocerlo. Además, el hook no reconocía `PASSPHRASE` | `c2e88fd` |
| `c2e88fd` | `gpg --passphrase valor`, con un espacio, no se detectaba. Una comilla invertida en medio de un valor lo cortaba. Había un falso positivo con la prosa de una tabla (`` `DB_PASSWORD`: Contraseña de ... ``). El correo de la lista se comparaba por subcadena | `0d1dfba` |
| `0d1dfba` | 1 mayor: las frases solo de minúsculas o con espacios pasaban, y el valor en la línea siguiente no se veía. 5 menores, entre ellos un falso positivo con `add_argument("--password", required=True)` y la opción que solo cubría 3 claves | `bbffef3` |
| `bbffef3` | 2 mayores: la regla que quitó el falso positivo de `required=True` dejaba pasar un secreto en base64 con relleno (`...=`), y `--escanear-repo` no veía los archivos nuevos. Además, falsos positivos con identificadores entre comillas y huecos sin documentar | El commit siguiente |

No es descuido de cada ronda. El hook decide, **línea por línea y con expresiones regulares**, si un texto es un secreto. Eso solo se puede hacer con certeza para los tokens con forma fija (claves privadas, AWS, GitHub, Anthropic, JWT...). Para todo lo demás (una contraseña asignada a `DB_PASSWORD`, una frase de paso), el valor no tiene forma propia, y lo que lo distingue de un ejemplo depende del contexto:

- **El tipo de archivo:** en Python, `DB_PASSWORD = clave` asigna una variable. En Markdown, `` `DB_PASSWORD`: clave de app_user `` es prosa. En un `.env`, `DB_PASSWORD=clave` es un valor real.
- **La forma del valor:** si va entre comillas, si es solo de minúsculas o si tiene espacios.
- **Las líneas de alrededor:** el valor puede estar en la línea siguiente, y el hook no la ve.

Cada regla que quita un falso positivo abre un hueco, y cada regla que cierra un hueco agrega falsos positivos. Por ejemplo:

- Tratar un valor en minúsculas como nombre de variable quitó los falsos positivos del código y de la prosa, pero deja pasar `--passphrase correcthorsebattery`.
- Evaluar completo un valor entre comillas atrapa `"mi frase de paso larga"`, pero bloquea `PASSWORD_FIELD = "password"`. <!-- secreto-ok: el falso positivo, citado -->

- La revisión de `bbffef3` lo mostró en un solo commit: la regla que quitó el falso positivo de `required=True` abrió el hueco del relleno de base64.

Son 2 tipos de error que se compensan, y no hay un punto en el que los 2 lleguen a cero. Por eso cada revisión encuentra casos de un lado o del otro, y lo seguirá haciendo.

**Consecuencia:** el hook es una red de seguridad, no una garantía. Las barreras reales son estas:
- los secretos nunca se escriben en el repositorio, porque viven en `.env`, fuera de Git (`.gitignore`);
- los scripts reciben las frases de paso por un descriptor o un archivo (`--passphrase-fd`, `--passphrase-file`), nunca como argumento (guía de HB-10);
- el PR se revisa;
- `secreto-ok` marca una excepción a propósito.

Cuando se cambie el hook, se decide qué error se acepta, y la decisión queda en un test.

## Límites aceptados

Estos casos pasan a propósito. `LIMITES_ACEPTADOS` de `tests/test_bloquear_secretos.py` tiene al menos un caso por fila, en el mismo orden; la fila 9 se prueba aparte, en `test_limite_lista_de_permitidos_por_subcadena`. Si un cambio cierra alguna, el test falla: entonces se quita de la lista y de esta tabla.

| # | Límite | Ejemplo que pasa | Por qué se acepta |
|---|---|---|---|
| 1 | Un valor sin comillas y solo de minúsculas | `gpg --passphrase correcthorsebattery` | No se distingue de un nombre de variable (`"--passphrase", frase`) ni de una palabra de la prosa. Entre comillas sí se bloquea |
| 2 | El valor en otra línea | `"--passphrase",` y el valor en la línea siguiente, o una continuación con `\` | El hook revisa línea por línea, como llegan en el `diff`. Para verlo haría falta analizar el archivo completo |
| 3 | Una comilla en medio de un valor sin comillas | `DB_PASSWORD=ab` seguido de una comilla invertida y el resto | El valor se corta en la comilla, como con las comillas simples y dobles, y quedan menos de 8 caracteres |
| 4 | Una palabra con mayúscula inicial seguida de más texto | `` `DB_PASSWORD`: Hogarseguro y ... `` | Es la forma de la prosa en las tablas de la documentación (`` `CLAVE`: Contraseña de ... ``). Un valor solo, sin texto detrás, sí se bloquea |
| 5 | Un valor que empieza por `-`, `/`, `./`, `../` o `~/`, o, sin comillas, con la forma `nombre=algo` | `--private-key ./llave.pem`, `required=True)` | Son otra opción, una ruta o un argumento con nombre, no el valor de la clave. El relleno de base64 (`...=` o `...==` al final) sí se bloquea, y entre comillas `nombre=algo` también |
| 6 | Paréntesis, corchetes o llaves en el valor, también en una frase entre comillas | `--passphrase "mi frase (2026) larga"` | Así se reconocen las llamadas y los índices del código (`env("DB_PASSWORD")`, `os.environ[...]`) |
| 7 | Comillas escapadas dentro del valor | `DB_PASSWORD = "ab\"cdefghijkl"` | El valor entre comillas termina en la primera comilla, y lo que queda antes no llega a 8 caracteres |
| 8 | Claves con otro nombre, o el valor pasado de otra forma | `CONTRASENA=...`, `mysql -p valor`, `-passin pass:valor`, `Authorization: Bearer valor` | El hook solo reconoce los nombres en inglés de `CLAVES` (`PASSWORD`, `PASSPHRASE`, `SECRET`, `TOKEN`, `API_KEY`...), que son los del proyecto (`.env.example`), como asignación (`CLAVE=valor`) o como opción larga (`--clave valor`) |
| 9 | La lista de permitidos se compara por subcadena, salvo los correos | Una entrada `valor-publico-largo` deja pasar cualquier valor que la contenga | Por eso solo admite valores públicos completos y largos (`CLAUDE.md`). Hoy solo tiene un correo, que se compara completo |

## Falsos positivos aceptados

Estos casos se bloquean aunque no sean secretos. Los fija `FALSOS_POSITIVOS_ACEPTADOS` del mismo test. Mientras no cambie la regla, la línea se marca con `secreto-ok`.

| Falso positivo | Ejemplo | Por qué se acepta |
|---|---|---|
| Un identificador entre comillas | `PASSWORD_FIELD = "password"` | Entre comillas, el valor es un literal, aunque sea solo de minúsculas: así se bloquea `DB_PASSWORD = "hogarapp2026"` | <!-- secreto-ok: los ejemplos de esta tabla, citados -->
| Un mensaje de error con un código que lleva el nombre de la clave | `"password_mismatch": "Las contraseñas no coinciden."`, el patrón de `error_messages` en los formularios de Django | La clave termina en `PASSWORD...`, y el mensaje es un valor entre comillas de más de 8 caracteres | <!-- secreto-ok: los ejemplos de esta tabla, citados -->

## Pendientes

Se retoman cuando los tickets traigan código nuevo, porque cada uno agrega formas de escribir claves que hoy no existen en el repositorio:

| Pendiente | Cuándo | Cómo se cierra |
|---|---|---|
| Revisar el hook con el código real de cada ticket. Por ejemplo, la configuración de TK-01 y TK-02, los tests de servicios con sus usuarios o los scripts de respaldo de HB-10 | Al cerrar cada TK y HB-10: el cierre de `implementar-ticket` corre `--escanear-repo` | Lo que se encuentre se anota aquí (sección siguiente). Después, en un commit aparte, se agrega el caso a `BLOQUEA`, `PERMITE`, `LIMITES_ACEPTADOS` o `FALSOS_POSITIVOS_ACEPTADOS`, y a este documento |
| Los mensajes de error de los formularios (`error_messages` con códigos como `password_mismatch`) | Si TK-02 o TK-03 escriben formularios con mensajes propios | Si aparecen varios, decidir una regla (por ejemplo, que un valor con espacios en un archivo `.py` dentro de un diccionario sea texto), con sus tests. Si es uno, basta `secreto-ok` |
| Nombres de clave en español (`CLAVE`, `CONTRASENA`, `FRASE`) | Si algún ticket los introduce | Agregarlos a `CLAVES`, con sus tests. Hoy no hace falta: las variables del proyecto están en inglés |
| Un escáner dedicado en el CI, como `gitleaks` o `detect-secrets`, con entropía y archivos completos | Después del MVP, o antes si un límite de la tabla deja pasar algo real | Decidirlo con un ADR (una dependencia más y su versión fija), como complemento del hook: el hook revisa antes del commit y el escáner, en el PR |
| Los scripts de HB-10 reciben las frases de paso por `--passphrase-fd` o `--passphrase-file`, nunca como argumento | Al escribir los scripts (HB-10, parte A) | Revisión del PR de HB-10. La guía ya lo hace así en el código de referencia |

### Casos encontrados en los tickets

Aquí se anotan los casos que el hook bloqueó sin ser secretos, o que dejó pasar, durante un ticket: el ticket, el archivo, la forma de la línea (nunca el valor real) y si se marcó con `secreto-ok`.

| Ticket | Archivo | Caso | Qué se hizo |
|---|---|---|---|
| — | — | Todavía ninguno | — |

## Si el hook bloquea durante un ticket

El hook no se cambia dentro de un ticket. Los tests del ticket están congelados, y un cambio del hook es otra unidad de trabajo, con sus propios tests:

1. **Si es un dato real**, se cambia el dato (`CLAUDE.md`, "Cuando bloquea").
2. **Si es un ejemplo legítimo**, la línea se marca con `secreto-ok`, el caso se anota en "Casos encontrados en los tickets" y se reporta en el cierre del ticket.
3. **Si el hook dejó pasar un valor real**, se quita el valor y el caso se anota de la misma forma.
4. **El hook se cambia después**, en un commit aparte, con el procedimiento de la sección siguiente.

## Cómo se cambia el hook

1. **Primero los tests**, en `tests/test_bloquear_secretos.py`:
   - el caso que debe bloquearse va en `BLOQUEA`, con `# secreto-ok` para que el propio hook deje commitear el test;
   - el que debe pasar va en `PERMITE`;
   - el límite que se acepta va en `LIMITES_ACEPTADOS`, y el falso positivo que se acepta, en `FALSOS_POSITIVOS_ACEPTADOS`.

   Se comprueba que fallen: `python -m pytest tests/test_bloquear_secretos.py`.
2. **El cambio** en `bloquear_secretos.py`, hasta el verde de `python -m pytest tests` y `python scripts/verificar.py --herramientas`.
3. **Todo el repositorio:** `python .claude/hooks/bloquear_secretos.py --escanear-repo` recorre los archivos rastreados y los nuevos sin rastrear (no los ignorados). Debe terminar en `0 hallazgo(s)` y salir con código 0. Si encuentra algo, sale con 1: el cambio produjo un falso positivo, o descubrió un dato real.
4. **Este documento**, si cambia un límite o un falso positivo aceptado, o si se cierra un pendiente.
