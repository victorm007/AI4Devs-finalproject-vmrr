# ADR-0005 · PostgreSQL 17 como última barrera de integridad

- **Estado:** Aceptado
- **Fecha:** 2026-11-16
- **Capabilities afectadas:** `accounts`, `catalogo`, `entidades`, `pautas`, `inventario`, `conteos`
- **Fuentes:** `readme.md` §2.1, §3.1, §3.2 ("Antipatrones evitados"), §3.3 ("Restricciones de integridad adicionales") y §6 (punto de integración 3 y criterios de revisión); `CLAUDE.md` ("Reglas de diseño que cruzan varias capas" y "Estándares y convenciones de base de datos")

## Contexto

Un error de código o un acceso directo a la base de datos no deben poder romper las reglas de negocio, como saldos negativos, Movimientos incoherentes con su tipo o una Pauta traslapada. Al mismo tiempo, el usuario nunca debe ver un error `500` por una regla de negocio: necesita un mensaje claro en el formulario.

## Decisión

- La base de datos es **PostgreSQL 17** y es la **última barrera, no la única**. Las reglas viven en `UNIQUE`, `CHECK`, `EXCLUDE`, claves foráneas, columnas generadas y *triggers*.
- **El servicio o el formulario valida primero**, para dar mensajes claros; la base de datos rechaza lo que se escape.
- Django genera la mayoría de las restricciones con `UniqueConstraint`, `CheckConstraint`, `ExclusionConstraint` y `GeneratedField`. Las extensiones, la función `f_unaccent`, los *triggers* y el `fillfactor` se agregan con `RunSQL`, cada uno con su `reverse_sql`.
- Los índices únicos por expresión (`uq_medicamento_nombre_pres_conc` y `uq_principio_activo_nombre`) se declaran como `UniqueConstraint` con expresiones en `Meta.constraints`, no con `RunSQL`, para que los formularios de Django (incluido `/admin/`) muestren el error junto al campo.
- Reglas que viven en *triggers* (§3.3): no se da de Baja un Medicamento con Existencias (`tg_medicamento_baja`); no entran Existencias a un Medicamento inactivo ni a un Residente egresado o fallecido, salvo correcciones (`tg_movimiento_validar_destino`); las Pautas solo se registran para Residentes y Medicamentos activos (`tg_pauta_validar`); un conteo cerrado no se modifica (`tg_conteo_cerrado` y `tg_detalle_conteo_cerrado`); los Movimientos son inmutables (`tg_movimiento_inmutable`, ver [ADR-0012](0012-movimientos-inmutables-y-correccion.md)).
- **`CHECK` solo para dominios fijos ligados a la lógica**, como el tipo de Movimiento o los estados. Las listas que cambian (`presentacion` y `motivo_baja`) son tablas de catálogo.
- **Los datos semilla se crean con migraciones de datos:** la Entidad Hogar, los 2 grupos con sus permisos, los motivos de Baja y las presentaciones más comunes.

## Alternativas consideradas

- **Restricciones solo en la aplicación:** se descartaron porque un error o un acceso directo a la base rompería las reglas (antipatrón, §3.2).
- **`ENUM` o `CHECK` para listas que cambian:** se descartaron porque cada valor nuevo exigiría una migración (antipatrón, §3.2).

## Consecuencias

**Positivas:**
- Ni un error de código ni un acceso directo pueden romper las reglas (§3.3).
- Cada restricción de la base tiene su excepción de dominio en el servicio. Por ejemplo, `uq_movimiento_corrige` se traduce a `MovimientoYaCorregido` (§6, punto de integración 3).

**Negativas:**
- Cada regla existe 2 veces, en la aplicación y en la base, y las 2 deben coincidir.
- Toda migración debe ser reversible y se revisa con `sqlmigrate` (§6, criterios de revisión).
