# Spec Delta

## MODIFIED Requirements

### Requirement: Migraciones reversibles de inventario

Las migraciones de `inventario` DEBEN (MUST) aplicarse en una base vacía y revertirse hasta `zero` sin errores, y volver a aplicarse.

#### Scenario: Revertir y volver a aplicar (TK-01, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `migrate conteos zero`, `migrate inventario zero` y después `migrate`
- **THEN** las 3 terminan sin errores, las tablas desaparecen al revertir y vuelven al aplicar

#### Scenario: Sin migraciones pendientes (TK-01, criterio 2)

- **GIVEN** los modelos de `inventario` y `conteos`
- **WHEN** se ejecuta `makemigrations --check --dry-run`
- **THEN** no detecta cambios
