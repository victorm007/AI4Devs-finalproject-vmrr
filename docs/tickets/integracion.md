# Integración de TK-01, TK-02 y TK-03

> **Readme:** sección 6, "Orden de ejecución", "Puntos de integración" y "Prueba de integración final".
>
> **Quién la hace:** quien integra el último de los 3 tickets (normalmente TK-03), en su rama, después de `git rebase main` y antes del *merge*. Desde entonces la prueba corre en CI en cada PR.

**Objetivo:** demostrar que las 3 capas funcionan juntas. Lo que registra el servicio (TK-02), guardado con las reglas y permisos de la base (TK-01), aparece correctamente en la pantalla (TK-03), y los saldos siguen cuadrando con los movimientos.

---

## 1. Antes de empezar

```bash
git switch main && git pull
git log --oneline -5          # deben estar los merges de TK-01 y TK-02
git switch feature/TK-03-pantalla-existencias
git rebase main               # resuelve conflictos con las reglas de "Archivos que tocan varios tickets"

set -a && . ./.env && set +a
dj()    { docker compose exec web python manage.py "$@"; }
dtest() { docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" web pytest "$@"; }
dpsql() { docker compose exec db psql -U app_owner -d "$POSTGRES_DB" "$@"; }
```

Comprueba los puntos de integración antes de escribir la prueba:

| # | Comprobación | Comando | Esperado |
|---|---|---|---|
| 1 | Los *fixtures* de TK-01 existen | `dtest --fixtures apps/inventario \| grep -E "datos_demo\|como_app_user"` | Aparecen los 2 |
| 2 | Solo `services.py` escribe en inventario | `git grep -nE "(Movimiento\|Existencia)\.objects\.(create\|bulk_create\|update)" -- app/apps ':!*/tests/*' ':!*/migrations/*'` | Solo `services.py` |
| 3 | Las migraciones están en orden y sin huecos | `dj showmigrations inventario conteos accounts` | Todas con `[X]`, sin duplicados de número |
| 4 | Los grupos tienen los permisos | `dj shell -c "from django.contrib.auth.models import Group; print(sorted(Group.objects.get(name='Solo lectura').permissions.values_list('codename', flat=True)))"` | Incluye `view_existencia` |

---

## 2. La prueba: `app/apps/inventario/tests/test_integracion.py`

```python
"""Prueba de integración de TK-01 + TK-02 + TK-03 (readme, sección 6).

Cada escenario registra movimientos con services.py (TK-02), sobre el esquema y los
permisos de app_user (TK-01), y comprueba lo que muestra la pantalla de existencias (TK-03).
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import Usuario
from apps.inventario import services
from apps.inventario.exceptions import ExistenciaInsuficiente
from apps.inventario.models import Movimiento
from pruebas import ejecutar_sql

pytestmark = pytest.mark.integracion
URL = reverse("inventario:existencias")
HTMX = {"HX-Request": "true"}


@pytest.fixture
def cliente(client, como_app_user):
    """Navegador de consulta.demo. Toda la base se usa como app_user (punto de integración 4)."""
    client.force_login(Usuario.objects.get(username="consulta.demo"))
    return client


@pytest.fixture(autouse=True)
def todo_cuadra_al_terminar():
    """Punto de integración 8: los saldos siempre son la suma de los movimientos."""
    yield
    assert ejecutar_sql("SELECT count(*) FROM v_conciliacion_existencia") == [(0,)]


def pantalla(cliente, **filtros) -> list[tuple[int, str, Decimal]]:
    """Lo que la pantalla de existencias (TK-03) muestra con esos filtros."""
    respuesta = cliente.get(URL, filtros, headers=HTMX)
    assert respuesta.status_code == 200
    return [
        (e.entidad_id, e.medicamento.nombre_comercial, e.saldo)
        for e in respuesta.context["existencias"]
    ]


def test_lo_que_registra_el_servicio_aparece_en_la_pantalla(cliente, demo):
    carmen = demo.carmen.pk
    assert pantalla(cliente, entidad=carmen) == [
        (carmen, "Eutirox", 33), (carmen, "Exelon", 3), (carmen, "Paracetamol", 14),
    ]

    services.registrar_entrada(
        usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Eutirox"],
        cantidad="30", origen_entrada="FAMILIAR", entregado_por="Rosa Torres",
    )
    services.transferir(
        usuario=demo.operador, origen=demo.hogar, destino=demo.carmen,
        medicamento=demo.med["Omeprazol"], cantidad="0.5",
    )

    assert pantalla(cliente, entidad=carmen) == [
        (carmen, "Eutirox", 63), (carmen, "Exelon", 3),
        (carmen, "Omeprazol", Decimal("0.5")), (carmen, "Paracetamol", 14),
    ]
    html = cliente.get(URL, {"entidad": carmen}, headers=HTMX).content.decode()
    assert "0.5 dosis" in html                                  # filtro dosis de TK-03


def test_una_baja_rechazada_no_cambia_la_pantalla(cliente, demo):
    with pytest.raises(ExistenciaInsuficiente):
        services.dar_de_baja(
            usuario=demo.operador, origen=demo.maria, medicamento=demo.med["Atorvastatina"],
            cantidad=5, motivo=demo.motivo["CONSUMO"],
        )
    assert pantalla(cliente, q="atorvastatina") == [(demo.maria.pk, "Atorvastatina", 1)]


def test_lo_agotado_solo_aparece_con_incluir_sin_saldo(cliente, demo):
    services.dar_de_baja(
        usuario=demo.operador, origen=demo.maria, medicamento=demo.med["Atorvastatina"],
        cantidad=1, motivo=demo.motivo["CONSUMO"],
    )
    assert pantalla(cliente, q="atorvastatina") == []
    assert pantalla(cliente, q="atorvastatina", incluir_sin_saldo="on") == [
        (demo.maria.pk, "Atorvastatina", 0),
    ]
    html = cliente.get(URL, {"q": "atorvastatina", "incluir_sin_saldo": "on"}, headers=HTMX)
    assert "Agotado" in html.content.decode()


def test_una_correccion_se_refleja_en_la_pantalla(cliente, demo):
    entrada = services.registrar_entrada(
        usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Eutirox"],
        cantidad="30", origen_entrada="FAMILIAR", entregado_por="Rosa Torres",
    )
    services.corregir(usuario=demo.operador, movimiento=entrada)

    assert (demo.carmen.pk, "Eutirox", 33) in pantalla(cliente, entidad=demo.carmen.pk)
    assert Movimiento.objects.filter(corrige_a=entrada).count() == 1


def test_el_ultimo_movimiento_actualiza_la_fecha_de_la_pantalla(cliente, demo):
    antes = cliente.get(URL, {"entidad": demo.carmen.pk}, headers=HTMX).context["existencias"]
    fecha_antes = next(e.actualizado_en for e in antes if e.medicamento.nombre_comercial == "Exelon")

    services.registrar_entrada(
        usuario=demo.operador, destino=demo.carmen, medicamento=demo.med["Exelon"],
        cantidad="7", origen_entrada="FAMILIAR", entregado_por="Rosa Torres",
    )
    despues = cliente.get(URL, {"entidad": demo.carmen.pk}, headers=HTMX).context["existencias"]
    exelon = next(e for e in despues if e.medicamento.nombre_comercial == "Exelon")
    assert exelon.saldo == 10
    assert exelon.actualizado_en > fecha_antes
```

> Los escenarios usan `entidad_id` en lugar del nombre mostrado, para no depender del formato de `Entidad.__str__`.

---

## 3. Verificación completa sobre una instalación desde cero

Simula lo que pasará en el servidor del hogar: base nueva, migraciones como `app_owner`, la aplicación como `app_user`.

```bash
# 1. Instalación limpia (borra tu base de desarrollo)
docker compose down -v && docker compose up -d --build
./scripts/migrate.sh
docker compose cp app/fixtures/mock/. db:/tmp/mock/
dpsql -v ON_ERROR_STOP=1 -f /tmp/mock/cargar_mock.sql      # resumen: 28 movimientos, 13 existencias...

# 2. Calidad y suite completa (los 3 tickets + integración)
docker compose exec web ruff check . && docker compose exec web ruff format --check .
dj makemigrations --check --dry-run                          # No changes detected
dtest -q                                                      # todo en verde
dtest apps/inventario/tests/test_integracion.py -v           # los 5 escenarios en PASSED

# 3. Extremo a extremo en Chromium
docker compose exec -e DB_USER=app_owner -e DB_PASSWORD="$DB_OWNER_PASSWORD" \
    -e DJANGO_ALLOW_ASYNC_UNSAFE=true web pytest -m e2e e2e/ -q

# 4. Prueba de humo: servicio (TK-02) → base (TK-01) → pantalla (TK-03)
dj shell -c "
from apps.inventario import services
from apps.entidades.models import Entidad
from apps.catalogo.models import Medicamento
from apps.accounts.models import Usuario
services.transferir(usuario=Usuario.objects.get(username='operador.demo'),
                    origen=Entidad.objects.get(tipo='HOGAR'), destino=Entidad.objects.get(pk=103),
                    medicamento=Medicamento.objects.get(nombre_comercial='Paracetamol'), cantidad=10)
"
BASE=https://localhost; JAR=/tmp/hogar.cookies; CURL="curl -s -k"
login() { rm -f "$JAR"; $CURL -c "$JAR" "$BASE/accounts/login/" -o /dev/null
  local csrf; csrf=$(awk '$6 == "csrftoken" { print $7 }' "$JAR")
  $CURL -b "$JAR" -c "$JAR" -o /dev/null -w "login: %{http_code}\n" -X POST "$BASE/accounts/login/" \
    -H "Referer: $BASE/accounts/login/" --data-urlencode "csrfmiddlewaretoken=$csrf" \
    --data-urlencode "username=$1" --data-urlencode "password=$2"; }
login consulta.demo 'DemoLectura2026!'                                    # login: 302
$CURL -b "$JAR" -H "HX-Request: true" "$BASE/existencias/?entidad=103&q=paracetamol" | grep -o '24 dosis' | head -1
# 24 dosis   (14 + 10)
$CURL -b "$JAR" -H "HX-Request: true" "$BASE/existencias/?q=paracetamol" | grep -o '70 dosis' | head -1
# 70 dosis   (Hogar: 80 - 10)

# 5. La aplicación no puede reescribir el historial y todo cuadra
docker compose exec db psql -U app_user -d "$POSTGRES_DB" -c 'DELETE FROM movimiento'
# ERROR:  permission denied for table movimiento
dpsql -c 'SELECT count(*) FROM v_conciliacion_existencia'               # 0
```

---

## 4. Lista de integración (en el PR del último ticket)

- [ ] `git rebase main` sin conflictos pendientes; las reglas de "Archivos que tocan varios tickets" se respetaron.
- [ ] Los puntos de integración de la sección 6 siguen como están documentados; si alguno cambió, el readme está actualizado.
- [ ] `test_integracion.py` está en el repositorio y pasa en CI.
- [ ] Los 5 comandos de la sección 3 dan el resultado esperado; la salida de los pasos 2 y 4 está en la descripción del PR.
- [ ] El guion de demo de la sección 3.4 (pasos 1, 2, 3 y 5) se puede hacer en la pantalla nueva.

## 5. Si algo no integra

| Síntoma | Punto de integración | Qué revisar |
|---|---|---|
| La pantalla responde `403` a todos | 5 | Migración `inventario/0003_permisos_grupos` aplicada y el `permission_required` de la vista |
| `permission denied for table movimiento` al registrar | 4 | Algún `select_for_update()` o `update()` sobre `Movimiento` en `services.py` |
| La pantalla no muestra un movimiento recién registrado | 2 | El servicio actualiza `existencia` en la misma transacción; el selector no filtra de más (por ejemplo, `medicamento__activo`) |
| `v_conciliacion_existencia` no está vacía | 2 y 8 | Algún código fuera de `services.py` escribió en `existencia`; comando 2 de la sección 1 |
| `fixture 'demo' not found` en TK-03 | 7 | El `conftest.py` de `main` (TK-01) y que TK-03 no lo haya sobrescrito al resolver conflictos |
| Dos migraciones con el mismo número | — | Renumera la de tu rama después del *rebase* y vuelve a ejecutar `./scripts/migrate.sh` |
