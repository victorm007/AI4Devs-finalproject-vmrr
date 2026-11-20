# Spec Delta

## Purpose

Define el modelo de usuario propio de la aplicación y cómo se guardan y validan las contraseñas de sus usuarios.

## ADDED Requirements

### Requirement: Modelo de usuario propio

El proyecto DEBE (MUST) usar el modelo `accounts.Usuario`, guardado en la tabla `usuario`, desde la primera migración.

#### Scenario: Modelo y tablas del usuario (HB-03, descripción técnica)

- **GIVEN** la configuración del proyecto
- **WHEN** se consulta el modelo de usuario activo
- **THEN** `AUTH_USER_MODEL` es `accounts.Usuario`
- **AND** su tabla es `usuario` y la de sus grupos es `usuario_groups`

### Requirement: Contraseñas con Argon2

Las contraseñas nuevas DEBEN (MUST) guardarse con Argon2, y un *hash* PBKDF2 como los del dataset mock DEBE (MUST) seguir validándose.

#### Scenario: Contraseña nueva con Argon2 (HB-03, criterio 5)

- **GIVEN** un usuario nuevo con la contraseña `Prueba-larga-2026`
- **WHEN** se guarda
- **THEN** su *hash* empieza con `argon2$`
- **AND** la contraseña se valida

#### Scenario: Hash PBKDF2 del mock (HB-03, criterio 5)

- **GIVEN** un usuario cuyo *hash* es PBKDF2-SHA256, como los del dataset mock
- **WHEN** se valida su contraseña
- **THEN** la validación es correcta

### Requirement: Longitud mínima de la contraseña

Una contraseña DEBE (MUST) tener al menos 10 caracteres.

#### Scenario: Contraseña de 9 y de 10 caracteres (HB-03, descripción técnica)

- **GIVEN** los validadores de contraseña del proyecto
- **WHEN** se valida una contraseña de 9 caracteres y otra de 10
- **THEN** la de 9 se rechaza con el código `password_too_short`
- **AND** la de 10 se acepta
