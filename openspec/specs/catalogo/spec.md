# catalogo Specification

## Purpose

Define el catálogo de Medicamentos: presentaciones, principios activos y medicamentos, sin duplicados aunque cambien mayúsculas o acentos, y con búsqueda por nombre que usa su índice.

## Requirements

### Requirement: Búsqueda sin mayúsculas ni acentos

La base DEBE (MUST) tener instaladas las extensiones `btree_gist`, `pg_trgm` y `unaccent`, y la función `f_unaccent`, que quita los acentos y se puede usar en índices.

#### Scenario: Extensiones instaladas (HB-05, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se listan las extensiones
- **THEN** aparecen `btree_gist`, `pg_trgm` y `unaccent`

#### Scenario: f_unaccent quita los acentos (HB-05, criterio 1)

- **GIVEN** la base migrada
- **WHEN** se evalúa `f_unaccent(lower('Losartán ÁCIDO Ñandú'))`
- **THEN** el resultado es `losartan acido nandu`

#### Scenario: Búsqueda desde el ORM con el índice trigram (HB-05, criterio 5)

- **GIVEN** la búsqueda parcial de Medicamentos activos por nombre comercial desde el ORM
- **WHEN** se obtiene su plan de ejecución
- **THEN** el plan usa `ix_medicamento_nombre_trgm`

### Requirement: Medicamento sin duplicados

No DEBEN (MUST NOT) existir 2 Medicamentos con el mismo nombre comercial, presentación y concentración, sin distinguir mayúsculas ni acentos, aunque uno esté dado de baja. El formulario DEBE (MUST) avisarlo con un mensaje antes de llegar a la base.

#### Scenario: Duplicado rechazado por la base (HB-05, criterio 3)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se guarda "LOSARTAN" 50 MG en tableta
- **THEN** la base lo rechaza por `uq_medicamento_nombre_pres_conc`

#### Scenario: El formulario avisa el duplicado (HB-05, criterio 3)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se valida "losartan" 50 mg en tableta con `full_clean()`
- **THEN** el error es un mensaje de validación que empieza con "Ya existe un medicamento", no una excepción de la base

#### Scenario: Otra concentración no es duplicado (HB-05, descripción técnica)

- **GIVEN** el Medicamento "Losartán" 50 mg en tableta
- **WHEN** se guarda "Losartán" 100 mg en tableta
- **THEN** se guarda y existen 2 Medicamentos

### Requirement: Principio activo sin duplicados

No DEBEN (MUST NOT) existir 2 principios activos con el mismo nombre sin distinguir mayúsculas ni acentos.

#### Scenario: Principio activo duplicado (HB-05, descripción técnica)

- **GIVEN** el principio activo "Ácido acetilsalicílico"
- **WHEN** se guarda "acido acetilsalicilico"
- **THEN** la base lo rechaza por `uq_principio_activo_nombre`

### Requirement: Textos obligatorios y tipo válido

La base DEBE (MUST) rechazar los nombres y concentraciones que sean solo espacios, y un tipo de Medicamento distinto de `GENERICO` u `ORIGINAL`.

#### Scenario: Nombre comercial solo con espacios (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un Medicamento cuyo nombre comercial es solo espacios
- **THEN** la base lo rechaza por `ck_medicamento_textos`

#### Scenario: Tipo fuera de GENERICO y ORIGINAL (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un Medicamento con tipo `OTRO`
- **THEN** la base lo rechaza por `ck_medicamento_tipo`

#### Scenario: Principio activo y presentación vacíos (HB-05, criterio 4)

- **GIVEN** la base migrada
- **WHEN** se inserta un principio activo solo con espacios o una presentación sin nombre
- **THEN** la base los rechaza por `ck_principio_activo_nombre` y `ck_presentacion_nombre`

### Requirement: Esquema con los nombres del readme

Las tablas, restricciones e índices del catálogo DEBEN (MUST) llevar los nombres exactos de las secciones 3.1 y 3.3. Las FK de la tabla puente NO DEBEN (MUST NOT) tener índices propios, porque ya los cubren el `UNIQUE` y `ix_mpa_principio_medicamento`.

#### Scenario: Índices con su definición (HB-05, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se consulta la definición de cada índice
- **THEN** `ix_medicamento_nombre_trgm` es GIN sobre `f_unaccent(lower(...))` con `gin_trgm_ops` y `WHERE activo`
- **AND** `ix_principio_activo_trgm` es GIN sobre `f_unaccent(lower(...))` con `gin_trgm_ops`
- **AND** `ix_mpa_principio_medicamento` cubre `(principio_activo_id, medicamento_id)`
- **AND** `uq_medicamento_nombre_pres_conc` es único e incluye `presentacion_id`

#### Scenario: Sin índices duplicados en la tabla puente (HB-05, descripción técnica)

- **GIVEN** la tabla `medicamento_principio_activo`
- **WHEN** se listan sus índices
- **THEN** solo existen su llave primaria, `uq_mpa_medicamento_principio` e `ix_mpa_principio_medicamento`

### Requirement: Presentaciones semilla

Las migraciones DEBEN (MUST) crear las 8 presentaciones semilla y poder revertirse por completo.

#### Scenario: Las 8 presentaciones (HB-05, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se listan las presentaciones
- **THEN** son tableta, cápsula, jarabe, gotas, ampolleta, parche, crema e inhalador

#### Scenario: migrate catalogo zero revierte todo (HB-05, criterio 6)

- **GIVEN** la base migrada
- **WHEN** se ejecuta `./scripts/migrate.sh catalogo zero`
- **THEN** desaparecen las tablas del catálogo, `f_unaccent` y las 3 extensiones
- **AND** `./scripts/migrate.sh` las vuelve a crear

### Requirement: La aplicación registra en el catálogo

`app_user` DEBE (MUST) poder registrar en las tablas del catálogo sin ser su dueño.

#### Scenario: app_user registra un principio activo (HB-05, descripción técnica)

- **GIVEN** una sesión que actúa como `app_user`
- **WHEN** inserta un principio activo
- **THEN** el registro queda guardado
