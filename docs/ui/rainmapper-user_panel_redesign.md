# Rediseño del mantenimiento de usuarios de Rainmapper

Quiero ajustar el rediseño actual de la pantalla de mantenimiento de usuarios de Rainmapper.

Tienes acceso al source code real de esta página y también a la imagen adjunta como referencia visual.

IMPORTANTE:
- No rediseñes toda la pantalla.
- No cambies la estructura general del accordion de usuarios.
- No cambies backend/API/endpoints.
- No elimines ninguna funcionalidad existente.
- El cambio debe centrarse específicamente en las secciones de Permissions y Security del usuario expandido.
- Mantén el estilo dark mode actual de Rainmapper.

Problema actual:
En la pantalla actual, la sección Security ocupa demasiado espacio vertical y horizontal para las pocas acciones que contiene:
- New password
- Show typed password
- Set password
- Reset password
- Delete user

En cambio, la sección Permissions necesita más espacio y una estructura más escalable para poder añadir futuros permisos sin que la UI crezca demasiado hacia abajo.

Objetivo del rediseño:
1. Reducir el espacio ocupado por Security.
2. Dar más espacio visual y estructural a Permissions.
3. Preparar Permissions para futuros permisos.
4. Mantener todos los handlers y lógica actual.
5. Mantener todos los campos y acciones actuales.

Referencia visual:
Usa la imagen adjunta como referencia. El concepto deseado es:
- User details arriba, en una fila compacta.
- Permissions como una sección ancha, en grid de tarjetas pequeñas.
- Security como un panel estrecho lateral.
- Devices debajo, sin cambios funcionales.
- Audit puede quedar como bloque compacto debajo de Permissions o integrado en la zona inferior.

Cambios concretos deseados:

## 1. User details

La sección User details debe ocupar una fila compacta superior.

Debe contener los campos existentes actuales:
- Name
- Email
- Role
- Status
- Max devices
- Save user

Requisitos:
- Mantener los mismos valores, bindings, validaciones y handlers actuales.
- No cambiar el comportamiento del botón Save user.
- Reducir altura vertical respecto al layout actual si es posible.
- Layout recomendado:
  - Campos en una sola fila en desktop si cabe.
  - Save user al final de la fila.
  - En pantallas estrechas puede pasar a dos filas.

Ejemplo conceptual:

Name | Email | Role | Status | Max devices | [Save user]

## 2. Permissions

La sección Permissions debe pasar de lista vertical a grid de permisos.

Objetivo:
- Que haya más espacio disponible para permisos actuales y futuros.
- Que añadir nuevos permisos no obligue a crecer demasiado hacia abajo.
- Que cada permiso sea visualmente identificable.

Permisos actuales que deben conservarse:
- Heatmap access
- Metric selector access
- Estimated field access

No hardcodees el layout de forma que sólo soporte estos tres permisos. Si el código actual ya tiene una estructura de permisos, úsala. Si los permisos están definidos explícitamente, organízalos en una estructura interna clara para que sea fácil añadir más.

Diseño deseado:
- Card principal llamada “Permissions”.
- Header con título, texto corto y opcionalmente acción “Select all” si es sencilla y segura.
- Dentro, grid responsive de permission cards.
- En desktop: 3 columnas si cabe.
- En pantallas medianas: 2 columnas.
- En pantallas pequeñas: 1 columna.

Cada permission card debe mostrar:
- Icono o placeholder visual.
- Nombre del permiso.
- Descripción corta.
- Toggle/switch a la derecha.
- Estado actual del permiso.

Ejemplo conceptual:

[Icon] Heatmap access
       Allow the Heatmap button and Heatmap settings.
                                      [toggle]

[Icon] Metric selector access
       Allow the metric selector button and layer metric settings.
                                      [toggle]

[Icon] Estimated field access
       Allow the IDW button and estimated field settings.
                                      [toggle]

Requisitos funcionales:
- Los toggles deben usar exactamente el mismo estado/lógica actual que los checkboxes existentes.
- No cambiar nombres de campos enviados al backend.
- No cambiar el payload de guardado.
- Si actualmente los permisos se guardan con Save user, mantenerlo.
- Si actualmente se guardan de otra forma, conservar ese comportamiento.
- Los permisos activos deben seguir reflejándose en los chips de la fila resumen.
- Los permisos inactivos no deben mostrarse como chips en la fila cerrada, igual que ahora.

Preparación para futuros permisos:
- Dejar el código preparado para añadir nuevos permisos añadiendo una entrada a una lista/configuración.
- Cada permiso debería poder definir:
  - key
  - label
  - description
  - icon opcional
  - color/accent opcional
  - getter/setter o binding al campo real actual

No inventes permisos nuevos en producción si no existen. En el mockup visual pueden aparecer placeholders o ejemplos, pero en el código real sólo deben mostrarse permisos reales existentes salvo que haya una configuración explícita para placeholders desactivada.

## 3. Security

La sección Security debe compactarse mucho.

Debe seguir incluyendo:
- Campo New password.
- Checkbox/toggle Show typed password.
- Botón Set password.
- Botón Reset password.
- Botón Delete user.

Diseño deseado:
- Security debe ser una card lateral estrecha a la derecha de Permissions, o una card compacta en la misma fila si el layout lo permite.
- No debe ocupar una columna enorme vacía.
- No debe dejar un área vertical vacía como ocurre ahora.
- Los botones deben agruparse de forma compacta.

Layout recomendado:

Security
[New password          ] [Show typed]
[Set password] [Reset password]
────────────────────────
[Delete user]

Requisitos:
- Mantener el handler actual de Set password.
- Mantener el handler actual de Reset password.
- Mantener el handler actual de Delete user.
- Mantener show/hide password.
- Delete user debe seguir siendo visualmente destructivo.
- Si Delete user ya tiene confirmación, conservarla.
- Si no tiene confirmación, añadir confirmación compacta reutilizando el patrón existente si lo hay.

## 4. Layout conjunto del usuario expandido

El usuario expandido debe organizarse así en desktop:

Fila 1:
- User details a ancho completo.

Fila 2:
- Permissions ocupando la mayor parte del ancho.
- Security ocupando una columna estrecha a la derecha.

Fila 3:
- Audit compacto si existe.
- Devices debajo, conservando la funcionalidad actual.

Ejemplo conceptual:

┌──────────────────────────────────────────────────────────────┐
│ User details: Name | Email | Role | Status | Max devices | Save│
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐ ┌──────────────┐
│ Permissions                                  │ │ Security     │
│ [perm card] [perm card] [perm card]          │ │ password...  │
│ [future...] [future...] [future...]          │ │ buttons...   │
└──────────────────────────────────────────────┘ └──────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Audit                                                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ Devices                                                      │
└──────────────────────────────────────────────────────────────┘

Responsive:
- En desktop, Permissions y Security van lado a lado.
- En pantallas estrechas, Security baja debajo de Permissions.
- El grid de permisos se adapta de 3 columnas a 2 y luego 1.

## 5. Estilo visual

Mantener el estilo actual:
- Dark mode.
- Cards con borde sutil.
- Bordes redondeados.
- Azul/cyan como acento principal.
- Verde para estados activos/OK.
- Rojo para acciones destructivas.
- Spacing compacto.
- No aumentar el alto total del usuario expandido.

Para los toggles:
- Preferible switch moderno en lugar de checkbox pequeño.
- Si ya existe un componente switch en el proyecto, reutilizarlo.
- Si no existe, implementar uno simple sin añadir dependencias pesadas.

## 6. Restricciones técnicas

Antes de tocar código:
1. Localiza el componente actual de User Management.
2. Identifica cómo se representan actualmente los permisos.
3. Identifica cómo se guardan los permisos.
4. Identifica los handlers actuales de:
   - Save user
   - Set password
   - Reset password
   - Delete user
5. Identifica si existe ya componente Modal/ConfirmDialog/Switch/Button/Card reutilizable.

No cambies backend.
No cambies endpoints.
No cambies nombres de campos enviados al backend.
No cambies la semántica de roles, status, max devices ni permisos.
No reescribas la pantalla completa.
No introduzcas librerías nuevas salvo que sea estrictamente necesario.

## 7. Componentes sugeridos

Si mejora la mantenibilidad, extrae o ajusta componentes como:

- ExpandedUserPanel
- UserDetailsCard
- PermissionsGrid
- PermissionCard
- SecurityCompactCard
- AuditCard
- DevicesCard

No es obligatorio crear todos si el código actual es más simple, pero evita duplicación y deja Permissions preparado para crecer.

## 8. Criterios de aceptación

El cambio se considera correcto si:

- Security ocupa claramente menos espacio que antes.
- Permissions tiene más espacio y usa un grid escalable.
- Los tres permisos actuales siguen funcionando exactamente igual.
- Los chips de permisos en la fila resumen siguen funcionando.
- Set password sigue funcionando.
- Reset password sigue funcionando.
- Show typed password sigue funcionando.
- Delete user sigue funcionando y mantiene confirmación si existe.
- Save user sigue funcionando.
- No se pierde ningún campo actual.
- No se cambia ningún contrato backend/API.
- El usuario expandido es más compacto o al menos no más alto que antes.
- El diseño se parece a la imagen adjunta en la distribución de Permissions y Security.
- El código queda preparado para añadir futuros permisos sin rehacer el layout.

## 9. Proceso obligatorio

Primero haz una fase de inspección y dame:

1. Archivo(s) implicados.
2. Cómo están modelados ahora los permisos.
3. Qué campos exactos se envían al guardar usuario.
4. Qué handlers se usan para seguridad.
5. Qué componentes existentes puedes reutilizar.
6. Plan concreto de cambios.
7. Riesgos o dudas antes de modificar.

No apliques todavía los cambios. Espera mi confirmación antes de implementar.