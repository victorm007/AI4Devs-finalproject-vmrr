# Spec Delta

## ADDED Requirements

### Requirement: Sin índice sobre el usuario del conteo

La FK `conteo_fisico.usuario_id` NO DEBE (MUST NOT) tener índice: ninguna consulta de la sección 3.3 filtra por ella (ADR-0018).

#### Scenario: La FK de usuario de conteo_fisico sin índice (segunda revisión de TK-01, bloqueante 1)

- **GIVEN** la base migrada
- **WHEN** se listan los índices cuya primera columna es `conteo_fisico.usuario_id`
- **THEN** no hay ninguno

### Requirement: Cierre y captura en paralelo

Un renglón capturado mientras otra transacción cierra el mismo conteo NO DEBE (MUST NOT) quedar en un conteo cerrado: el cierre espera a la captura, o la captura espera al cierre y entonces la base la rechaza. Las 2 transacciones corren como `app_user`.

#### Scenario: Cerrar un conteo mientras se captura un renglón (segunda revisión de TK-01, menor 5)

- **GIVEN** el conteo 2 del Hogar, `EN_PROCESO`, y una transacción que insertó en él un renglón sin confirmarlo
- **WHEN** otra transacción intenta cerrar el conteo 2
- **THEN** el cierre espera a que la primera termine: con `lock_timeout`, falla por tiempo de espera del bloqueo

#### Scenario: Capturar un renglón mientras se cierra el conteo (segunda revisión de TK-01, menor 5)

- **GIVEN** el conteo 2 del Hogar y una transacción que lo cerró sin confirmarlo
- **WHEN** otra transacción inserta un renglón en el conteo 2
- **THEN** la captura espera a que termine el cierre
- **AND** cuando el cierre se confirma, la base rechaza el renglón con "El conteo 2 está cerrado"

## MODIFIED Requirements

### Requirement: Migraciones reversibles de conteos

Las migraciones de `conteos` DEBEN (MUST) revertirse hasta `zero` sin errores y volver a aplicarse. Al revertir cada migración de `fn_detalle_conteo_cerrado`, la función DEBE (MUST) volver a la versión anterior.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero` y después `migrate`
- **THEN** ambas terminan sin errores, y `conteo_fisico` y `detalle_conteo` desaparecen al revertir y vuelven al aplicar

#### Scenario: La función del conteo cerrado vuelve a su versión anterior (segunda revisión de TK-01, menor 1)

- **GIVEN** la base migrada
- **WHEN** se revierte `conteos` hasta `0002_triggers` y después se vuelve a migrar
- **THEN** con `0002`, `fn_detalle_conteo_cerrado` mira un solo conteo (la variable `v_conteo`), sin `FOR SHARE`
- **AND** al volver a migrar, mira por separado el conteo de `OLD` y el de `NEW`, con `FOR SHARE` y sin `v_conteo`
