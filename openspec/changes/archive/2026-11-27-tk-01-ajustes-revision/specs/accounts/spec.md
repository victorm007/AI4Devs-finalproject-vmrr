# Spec Delta

## MODIFIED Requirements

### Requirement: Los 2 grupos y sus permisos

DEBEN (MUST) existir exactamente los grupos *Solo lectura*, con `view_*`, y *Lectura y escritura*, con `view_*`, `add_*` y `change_*`, sobre los modelos del catálogo (presentación, principio activo, medicamento y su tabla puente) y de residentes. Desde TK-01 tienen además los de inventario: los 2 grupos `view_existencia`, `view_movimiento` y `view_motivobaja`, y *Lectura y escritura* también `add_movimiento`. Ningún grupo recibe `delete_*` ni permisos sobre usuarios o grupos.

#### Scenario: Exactamente 2 grupos (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los grupos
- **THEN** son exactamente "Solo lectura" y "Lectura y escritura"

#### Scenario: Permisos de Solo lectura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Solo lectura"
- **THEN** son exactamente los 8 `view_*`: los de `presentacion`, `principioactivo`, `medicamento`, `medicamentoprincipioactivo` y `residente`, y los de `existencia`, `movimiento` y `motivobaja` (TK-01)

#### Scenario: Permisos de Lectura y escritura (HB-08, criterio 2)

- **GIVEN** la base migrada
- **WHEN** se listan los permisos de "Lectura y escritura"
- **THEN** son exactamente 19: los 15 `view_*`, `add_*` y `change_*` de esos 5 modelos, y `view_existencia`, `view_movimiento`, `view_motivobaja` y `add_movimiento` (TK-01)
- **AND** ninguno es `delete_*` ni `change_movimiento`, ni se refiere a usuarios o grupos

### Requirement: Solo el Administrador gestiona usuarios y grupos

Solo el Administrador (superusuario) DEBE (MUST) ver y gestionar "Usuarios" y ver "Grupos" en el panel; los demás reciben `403`. Nadie DEBE (MUST) poder borrar usuarios (la baja es `is_active = False`), ni crear, cambiar o borrar grupos a mano: su nombre y sus permisos solo los cambia una migración.

#### Scenario: Un usuario de grupo no ve usuarios ni grupos (HB-08, criterio 4)

- **GIVEN** un usuario de "Lectura y escritura" o de "Solo lectura" con sesión en el panel
- **WHEN** abre la lista de usuarios o la de grupos
- **THEN** la respuesta es `403`

#### Scenario: Nadie borra usuarios (HB-08, criterio 4)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** abre la página para borrar un usuario
- **THEN** la respuesta es `403`

#### Scenario: Los grupos no se crean ni se borran a mano (HB-08, descripción técnica)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** abre la página para crear un grupo, o la de borrar "Solo lectura"
- **THEN** la respuesta es `403`

#### Scenario: Los grupos no se cambian a mano (revisión de HB-08, hallazgo 5)

- **GIVEN** el Administrador con sesión en el panel
- **WHEN** envía el formulario de "Solo lectura" con otro nombre
- **THEN** la respuesta es `403` y el grupo conserva su nombre y sus 8 permisos (5 de HB-08 y 3 de TK-01)
- **AND** la página del grupo se puede consultar (`200`) en modo de solo lectura
