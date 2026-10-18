# 01 - Descripción general del producto (sesión con Claude)

> Transcripción de la sesión de definición del producto con Claude actuando como Product Owner especialista en sector Salud – Hogar Gerontológico.

---

## Prompt 1 — Usuario

Como Product Owner (PO o PDO) especialista en sector Salud - Hogar Gerontologico, crea una breve descripcion para este nuevo proyecto.

Software de gestion de hogar gerontologico - Inventario material de medicamento para un hogar gerontologico.

**Descripcion de funcionalidad:**

Inventario medicamentos

1. Manejo e inventario de medicamentos, poder hacer a/b/c (alta, baja, cambios) medicamentos y filtrado para facilitar esta operacion.
2. ABC de existencias por entidad (persona o el mismo negocio), cada paciente tiene su existencia de medicamentos y asimismo el asilo cuenta como entidad.
3. Filtrar medicamentos por paciente y por nombre de medicamento o principio activo
4. Inventariar por paciente, a demanda (fecha inicio y fin) -Existencia vs registrados-, reporte de medicamentos mensual
5. Establecer niveles de acceso: Solo lectura, lectura y escritura. Definen que puede hacer el usuario en las acciones anteriores.

**Descripcion no funcional:**

Es un proyecto para una empresa pequeña, que pueda ser accesible desde cualquier lugar mediante cliente web, debe ser seguro porque maneja datos personales (nombre, fecha nacimiento) y medicamentos que consume.

Antes de empezar, como product owner, pregúntame qué más necesitas saber para definir el proyecto

---

## Respuesta 1 — Claude

Antes de redactar la descripción del proyecto necesito aclarar algunos puntos. Las preguntas están agrupadas por tema y marqué con ⭐ las que más impacto tienen en el alcance del MVP.

### 1. Contexto del negocio y usuarios
1. ⭐ **¿Cuántos residentes tiene el hogar hoy y cuántos espera tener a 2-3 años?** (con esto dimensiono el volumen y el costo de la infraestructura)
2. ⭐ **¿Quiénes van a usar el sistema?** Por ejemplo: dirección o administración, enfermería, cuidadores, médico geriatra, farmacia o compras, familiares. ¿Cuántos usuarios habría por perfil?
3. ¿Se trabaja por turnos (mañana, tarde, noche)? ¿Hay entrega de turno que deba quedar registrada?
4. ¿Es una sola sede o podría haber varias en el futuro?

### 2. Medicamentos e inventario
5. ⭐ **¿Qué datos mínimos necesita cada medicamento?** Por ejemplo: nombre comercial, principio activo, presentación, concentración, vía de administración, laboratorio, **lote y fecha de caducidad**.
6. ⭐ **¿En qué unidad se controla la existencia?** ¿Por caja, blíster, tableta, ml o dosis? ¿Hay que convertir entre unidades (una caja = 30 tabletas)?
7. ¿Hay medicamentos controlados (psicotrópicos, estupefacientes) que exijan un registro especial o una bitácora regulatoria?
8. ¿Además de medicamentos se manejan otros insumos (material de curación, pañales, suplementos)? ¿Entran en este alcance?
9. ¿Necesitan alertas de **stock mínimo** y de **próxima caducidad**?

### 3. Existencias por entidad (paciente / hogar)
10. ⭐ **¿Cómo entran los medicamentos de cada paciente?** ¿Los trae la familia, se compran con cargo al paciente, o los aporta el hogar? ¿Hace falta registrar quién los entregó?
11. ¿Se pueden **transferir** existencias entre entidades? Por ejemplo, el hogar le presta a un paciente o se reasigna un medicamento sobrante de un residente que se fue o falleció.
12. ¿Qué tipos de **baja** existen? Administración (consumo), caducidad, merma o rotura, devolución a la familia, defunción o egreso.

### 4. Administración y consumo
13. ⭐ **¿El sistema debe registrar la administración diaria de medicamentos (quién, cuándo, qué dosis), o solo el inventario?** Esto define si el alcance incluye un registro de administración tipo MAR (*Medication Administration Record*) o si solo es un control de existencias.
14. ¿Se registran las **prescripciones o pautas médicas** de cada paciente (dosis y frecuencia)? Sin ese dato no se puede calcular el "consumo esperado".

### 5. Inventario y reportes
15. ⭐ **En "Existencia vs Registrados", ¿qué compara exactamente?** ¿El conteo físico contra lo que dice el sistema? ¿O lo que se consumió contra lo prescrito?
16. ¿En qué formato necesitan los reportes (PDF, Excel, solo pantalla)? ¿Quién los recibe? (dirección, médico, familia, autoridad sanitaria)
17. ¿El reporte mensual debe tener un formato fijo, por ejemplo uno exigido por alguna autoridad?

### 6. Seguridad, accesos y normativa
18. ⭐ **¿En qué país opera el hogar?** De esto depende la ley de protección de datos de salud que aplica (en México la LFPDPPP y la NOM-004 sobre expediente clínico; en Colombia la Ley 1581; en España el RGPD/LOPDGDD, etc.).
19. ¿Los dos niveles (solo lectura / lectura y escritura) son globales, o deben aplicarse **por módulo** o **por paciente**? Por ejemplo, un cuidador que solo ve a sus pacientes asignados.
20. ¿Necesitan **bitácora de auditoría** (quién cambió qué y cuándo)? En salud suele ser obligatoria.
21. ¿Algún usuario debe poder **aprobar** operaciones sensibles (bajas, ajustes de inventario)?

### 7. Restricciones del proyecto
22. ¿Hay presupuesto o preferencia de hosting (nube pública, servidor local)? ¿Ya cuentan con alguna tecnología?
23. ¿Se usará desde **celular o tablet** en piso, o principalmente desde computadora?
24. ¿Hay un sistema o Excel actual del que haya que **migrar datos**?
25. ¿Fecha objetivo para el MVP? ¿Se debe integrar con algo (facturación, farmacia, expediente clínico)?

Si quieres avanzar rápido, con las preguntas ⭐ (1, 2, 5, 6, 10, 13, 15 y 18) ya puedo armar una primera versión de la descripción y asumir valores razonables para el resto, que dejaría marcados como supuestos para validarlos contigo.

---

## Prompt 2 — Usuario (respuestas)

### 1. Contexto del negocio y usuarios
- **¿Cuántos residentes?** *20*
- **¿Quiénes van a usar el sistema?** Administrador, corte mensual.
- **¿Turnos / entrega de turno?** No.
- **¿Una sola sede?** *Si*

### 2. Medicamentos e inventario
- **Datos mínimos del medicamento:** Genérico u original; lote no.
- **Unidad de control:** Por dosis.
- **Medicamentos controlados:** Sí, pero no llevan registro especial.
- **Otros insumos / alertas de stock mínimo y caducidad:** No.

### 3. Existencias por entidad (paciente / hogar)
- **¿Cómo entran los medicamentos?** Sí hace falta registrar quién los entregó.
- **Transferencias entre entidades:** Sí a esos casos, y retiros del inventario por administración.
- **Tipos de baja:** Consumo, caducidad, merma, rotura, devolución a la familia, defunción, egreso.

### 4. Administración y consumo
- **¿Registro de administración (MAR) o solo inventario?** Control de existencias.
- **¿Se registran pautas?** Sí se registra dosis y frecuencia.

### 5. Inventario y reportes
- **"Existencia vs Registrados":** Conteo físico vs registros.
- **Formato de reportes:** Para administrador/dirección, solo en pantalla.
- **¿Formato fijo?** No.

### 6. Seguridad, accesos y normativa
- **País:** México.
- **Niveles de acceso / bitácora:** Nivel de acceso global; no se necesita bitácora de auditoría.
- **¿Aprobación de operaciones sensibles?** No.

### 7. Restricciones del proyecto
- **Hosting:** Servidor local.
- **¿Celular o computadora?** Sí, celular y computadora.
- **¿Migración de datos?** No.
- **Fecha / integraciones:** No se debe integrar con otros módulos o software externo. La fecha es el 22 de octubre para lo que se pide en el `readme.md` (todo lo referente a documentación).

---

## Respuesta 2 — Claude

Con tus respuestas ya puedo definir el proyecto. Abajo está la descripción con la estructura del `readme.md`: la sección 0.3 (descripción breve) y las secciones 1.1 y 1.2. Al final listo los supuestos que tomé y las contradicciones que encontré.

### 0.3. Descripción breve del proyecto

**Gestión de Medicamentos – Hogar Gerontológico** es una aplicación web responsive (computadora y celular) que controla el inventario de medicamentos de un hogar de adultos mayores. Lleva las existencias **por entidad**: cada residente tiene su propio inventario y el hogar cuenta como una entidad más. Registra entradas (con quién entregó el medicamento), transferencias entre entidades y bajas por motivo. Permite filtrar por paciente, nombre comercial o principio activo, y hacer conteos físicos que se comparan contra lo registrado. Corre en un servidor local, tiene acceso por usuario con dos niveles (solo lectura / lectura y escritura) y protege los datos personales y de salud de los residentes según la LFPDPPP de México.

### 1.1. Objetivo

Hoy el control de medicamentos de los residentes es manual, y eso deja huecos: no se sabe con certeza cuánto medicamento hay de cada paciente, quién lo trajo, qué pasó con el sobrante de un residente que egresó o falleció, ni si lo físico coincide con lo registrado.

El producto le da a la **administración / dirección** del hogar un inventario confiable y consultable desde cualquier dispositivo. Separa con claridad qué medicamento pertenece a cada residente y cuál al hogar, y facilita el **corte mensual** de existencias.

### 1.2. Características y funcionalidades principales

1. **Catálogo de medicamentos (alta / baja / cambio)**
   - Datos: nombre comercial, principio activo, tipo (genérico u original), presentación y concentración.
   - Búsqueda y filtrado por nombre o principio activo.
   - No se lleva control por lote.
2. **Gestión de entidades**
   - Alta, baja y cambio de residentes: nombre, fecha de nacimiento y estado (activo, egresado o fallecido).
   - El hogar existe como entidad propia.
3. **Existencias por entidad, controladas en dosis**
   - **Entradas:** se registra quién entregó el medicamento (familiar, el hogar, otro).
   - **Transferencias** entre entidades (de hogar a residente, de residente a hogar, o entre residentes), por ejemplo para reasignar el sobrante tras un egreso o una defunción.
   - **Bajas por motivo:** consumo o administración, caducidad, merma, rotura, devolución a la familia, defunción y egreso.
4. **Pauta del residente**
   - Se registra la dosis y la frecuencia de cada medicamento por paciente.
   - Es solo informativa: no incluye registro de administración (MAR).
5. **Filtros combinados** por paciente, nombre de medicamento y principio activo.
6. **Inventario físico y reportes en pantalla**
   - Conteo físico a demanda por paciente y por rango de fechas (inicio y fin), comparado contra lo registrado, con las diferencias resaltadas.
   - Reporte mensual de movimientos y existencias para la dirección.
7. **Usuarios y niveles de acceso globales**
   - *Solo lectura:* consulta y reportes.
   - *Lectura y escritura:* todas las operaciones anteriores.
8. **Seguridad**
   - Autenticación con contraseña cifrada, sesiones con expiración y HTTPS.
   - Acceso por rol en el backend.
   - Respaldos de la base de datos en el servidor local.
   - Aviso de privacidad conforme a la LFPDPPP.

**Fuera de alcance (MVP):** registro de administración por turno (MAR), alertas de stock mínimo y de caducidad, control por lote, insumos que no son medicamentos, multisede, exportar a PDF o Excel, integraciones externas y bitácora de auditoría.

### Supuestos y puntos a validar
1. **Servidor local frente a "accesible desde cualquier lugar" y celular.** Estos dos requisitos chocan. Si el servidor es local, para entrar desde fuera del hogar hace falta exponerlo de forma segura: HTTPS con dominio y proxy inverso, o una VPN. Asumo que se publica con HTTPS. Si solo se usará dentro de la red del hogar, dime y lo simplifico.
2. **Baja por caducidad sin guardar la fecha de caducidad.** Como no hay alertas, asumo que la baja por caducidad se registra a mano cuando alguien detecta el medicamento vencido.
3. **Sin bitácora de auditoría.** Aun así, cada movimiento guardará el usuario que lo registró y la fecha. Ya lo necesitamos para saber quién entregó cada medicamento y cuesta poco. Te lo recomiendo como trazabilidad mínima, por tratarse de datos de salud.
4. **Volumen y sedes** (no los respondiste). Asumo una sola sede, menos de 100 residentes y pocos usuarios, entre 5 y 10.
5. **Usuarios.** Asumo que el Administrador da de alta a los demás usuarios y les asigna su nivel.

¿Quieres que escriba estas secciones (0.3, 1.1 y 1.2) en el `readme.md`? Después seguiría con las historias de usuario (sección 5) para la entrega del 22 de octubre.

---

## Prompt 3 — Usuario

1. Considera por lo pronto con un servidor local, es posible subir la solución en un servicio de hosting.
2. Asumes correctamente.
3. Acepto trazabilidad mínima.
4. Solo una sede, 20 residentes, y pocos usuarios de 1 a 3.
5. Asumes correctamente.

Sí, escribe las secciones.

---

## Respuesta 3 — Claude

Ya escribí las secciones 0.3, 1.1 y 1.2 en `readme.md` con todas tus respuestas.

- **0.3 Descripción breve:** un párrafo que resume el producto. Dice que se instala en un servidor local y que más adelante se puede pasar a un servicio de hosting.
- **1.1 Objetivo:** el problema que resuelve, el valor para la dirección y el contexto de uso: una sede, unos 20 residentes y de 1 a 3 usuarios.
- **1.2 Características y funcionalidades principales:** tiene tres bloques.
   - **Funcionales:** catálogo, entidades, existencias en dosis (entradas, transferencias y bajas por motivo), pauta, filtros, inventario físico y reportes, niveles de acceso y la trazabilidad mínima aceptada.
   - **No funcionales:** acceso desde celular y computadora, despliegue, seguridad, privacidad según la LFPDPPP y escala.
   - **Fuera de alcance (MVP):** lo que no entra en la primera versión.

### Texto final escrito en `readme.md`

#### 0.3. Descripción breve del proyecto
**Gestión de Medicamentos – Hogar Gerontológico** es una aplicación web responsive (computadora y celular) para controlar el inventario de medicamentos de un hogar de adultos mayores. Gestiona las existencias **por entidad** (cada residente tiene su propio inventario y el hogar es una entidad más), registra entradas indicando quién entregó el medicamento, transferencias entre entidades y bajas por motivo. Permite filtrar por paciente, nombre comercial o principio activo, y realizar conteos físicos comparados contra lo registrado. Se despliega inicialmente en un servidor local (con posibilidad de migrar a un servicio de hosting), con acceso por usuario en dos niveles (solo lectura / lectura y escritura) y protección de los datos personales y de salud de los residentes conforme a la LFPDPPP (México).

#### 1.1. Objetivo
En un hogar gerontológico el control manual de medicamentos genera incertidumbre: no se sabe con certeza cuánto medicamento hay de cada residente, quién lo entregó, qué ocurrió con el sobrante de un residente que egresó o falleció, ni si lo que hay físicamente coincide con lo registrado.

El producto ofrece a la **administración / dirección** del hogar un inventario confiable y consultable desde cualquier dispositivo, que separa claramente qué medicamento pertenece a cada residente y cuál al hogar, y facilita el **corte mensual** de existencias.

**Contexto de uso:** una sola sede, aproximadamente 20 residentes y de 1 a 3 usuarios del sistema.

#### 1.2. Características y funcionalidades principales

**Funcionales**

1. **Catálogo de medicamentos (alta / baja / cambio):** nombre comercial, principio activo, tipo (genérico u original), presentación y concentración. Búsqueda y filtrado por nombre o principio activo. No se controla por lote.
2. **Gestión de entidades:** alta, baja y cambio de residentes (nombre, fecha de nacimiento, estado: activo / egresado / fallecido). El hogar existe como entidad propia.
3. **Existencias por entidad (controladas en dosis):**
   - **Entradas:** registro de quién entregó el medicamento (familiar, el hogar, otro).
   - **Transferencias** entre entidades (hogar → residente, residente → hogar, residente → residente), por ejemplo para reasignar sobrantes tras un egreso o defunción.
   - **Bajas por motivo:** consumo / administración, caducidad, merma, rotura, devolución a la familia, defunción y egreso. La baja por caducidad se registra manualmente al detectar el medicamento vencido.
4. **Pauta del residente:** registro de dosis y frecuencia de cada medicamento por paciente (informativo; no incluye registro de administración por turno).
5. **Filtros combinados** por paciente, nombre de medicamento y principio activo.
6. **Inventario físico y reportes (en pantalla):**
   - Conteo físico a demanda por paciente y por rango de fechas (inicio y fin), comparando existencia física contra lo registrado y resaltando diferencias.
   - Reporte mensual de movimientos y existencias para la dirección.
7. **Usuarios y niveles de acceso globales:** el Administrador da de alta a los usuarios y les asigna su nivel.
   - *Solo lectura:* consulta y reportes.
   - *Lectura y escritura:* todas las operaciones anteriores.
8. **Trazabilidad mínima:** cada movimiento de inventario guarda el usuario que lo registró y la fecha/hora.

**No funcionales**

- **Accesibilidad:** cliente web responsive, utilizable desde computadora y celular.
- **Despliegue:** servidor local en el hogar; la solución debe poder migrarse a un servicio de hosting sin cambios de arquitectura.
- **Seguridad:** autenticación con contraseñas cifradas (hash), sesiones con expiración, comunicación por HTTPS, autorización por nivel de acceso validada en el backend y respaldos periódicos de la base de datos.
- **Privacidad:** tratamiento de datos personales y de salud (nombre, fecha de nacimiento, medicamentos) conforme a la LFPDPPP, con aviso de privacidad.
- **Escala:** dimensionado para una pequeña empresa (1 sede, ~20 residentes, 1 a 3 usuarios).

**Fuera de alcance (MVP)**

Registro de administración por turno (MAR), alertas de stock mínimo o caducidad, control por lote, insumos distintos a medicamentos, multisede, exportación a PDF/Excel, bitácora de auditoría completa e integraciones con sistemas externos.

**Siguiente paso sugerido:** para la entrega del 22 de octubre, seguir con la sección 5 (las 3 historias de usuario principales, con criterios de aceptación) y después con la sección 3 (modelo de datos en mermaid), que sale casi directo de lo ya definido.
