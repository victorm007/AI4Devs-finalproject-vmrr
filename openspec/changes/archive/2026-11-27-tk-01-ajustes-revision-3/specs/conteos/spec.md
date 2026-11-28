# Spec Delta

## MODIFIED Requirements

### Requirement: Cierre y captura en paralelo

Un renglón capturado o borrado mientras otra transacción cierra el mismo conteo NO DEBE (MUST NOT) dejar un conteo cerrado con un renglón de más o de menos: el cierre espera al cambio del renglón, o el cambio espera al cierre y entonces la base lo rechaza. Las 2 transacciones corren como `app_user`.

#### Scenario: Cerrar un conteo mientras se captura un renglón (segunda revisión de TK-01, menor 5)

- **GIVEN** el conteo 2 del Hogar, `EN_PROCESO`, y una transacción que insertó en él un renglón sin confirmarlo
- **WHEN** otra transacción intenta cerrar el conteo 2
- **THEN** el cierre espera a que la primera termine: con `lock_timeout`, falla por tiempo de espera del bloqueo

#### Scenario: Capturar un renglón mientras se cierra el conteo (segunda revisión de TK-01, menor 5)

- **GIVEN** el conteo 2 del Hogar y una transacción que lo cerró sin confirmarlo
- **WHEN** otra transacción inserta un renglón en el conteo 2
- **THEN** la captura espera a que termine el cierre
- **AND** cuando el cierre se confirma, la base rechaza el renglón con "El conteo 2 está cerrado"

#### Scenario: Borrar un renglón mientras se cierra el conteo (tercera revisión de TK-01, menor 1)

- **GIVEN** el conteo 2 del Hogar, con su renglón de Omeprazol, y una transacción que lo cerró sin confirmarlo
- **WHEN** otra transacción borra ese renglón
- **THEN** el borrado espera a que termine el cierre
- **AND** cuando el cierre se confirma, la base rechaza el borrado con "El conteo 2 está cerrado" y el renglón sigue en el conteo

### Requirement: Migraciones reversibles de conteos

Las migraciones de `conteos` DEBEN (MUST) revertirse hasta `zero` sin errores y volver a aplicarse. Al revertir cada migración de `fn_detalle_conteo_cerrado`, la función DEBE (MUST) volver a la versión anterior.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero` y después `migrate`
- **THEN** ambas terminan sin errores, y `conteo_fisico` y `detalle_conteo` desaparecen al revertir y vuelven al aplicar

#### Scenario: La función del conteo cerrado vuelve a su versión anterior (segunda revisión de TK-01, menor 1)

- **GIVEN** la base migrada
- **WHEN** se revierte `conteos` hasta `0004_fk_sin_indice`, después hasta `0002_triggers`, y se vuelve a migrar
- **THEN** con `0004`, `fn_detalle_conteo_cerrado` es la de `0003`: mira por separado el conteo de `OLD` y el de `NEW`, sin `FOR SHARE` ni `v_conteo`
- **AND** con `0002`, mira un solo conteo (la variable `v_conteo`), sin `FOR SHARE`
- **AND** al volver a migrar, mira por separado el conteo de `OLD` y el de `NEW`, con `FOR SHARE` en las 2 lecturas y sin `v_conteo`
