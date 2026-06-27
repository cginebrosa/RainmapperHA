Quiero rediseñar la pantalla existente de mantenimiento de usuarios de Rainmapper.

Tú tienes acceso al código real actual del proyecto, así que no reconstruyas la pantalla desde cero salvo que sea absolutamente necesario. Primero inspecciona la implementación actual e identifica el modelo de datos existente, llamadas API, campos de formulario, permisos, validaciones, handlers y gestión de estado.

El objetivo es refactorizar la pantalla actual de mantenimiento de usuarios hacia una UI más moderna, compacta y basada en filas tipo accordion, usando el prototipo adjunto sólo como referencia visual.

Importante:
- Conserva toda la funcionalidad existente.
- Conserva todas las integraciones actuales con backend/API.
- Conserva todos los campos existentes, incluso si no aparecen explícitamente en el prototipo.
- Conserva la lógica actual de permisos y gestión de usuarios/dispositivos.
- No inventes nuevos contratos de backend.
- No elimines ninguna capacidad actual.
- Usa el prototipo como referencia visual y de layout, no como especificación funcional exacta.

Dirección de diseño:
- Interfaz dark mode tipo consola SaaS/admin moderna.
- Filas de usuario compactas.
- Comportamiento tipo accordion: sólo un usuario expandido a la vez.
- Las filas cerradas muestran un resumen del usuario.
- La fila expandida muestra edición de datos, permisos, seguridad y dispositivos.
- La creación de usuario debe moverse a un modal o drawer, en lugar de ocupar espacio permanente en la parte superior.
- La información de dispositivos debe ser compacta: mostrar información corta del dispositivo y truncar IDs/user agents largos, dejando el detalle completo disponible mediante title/tooltip o sección expandible.
- Las acciones destructivas deben estar visualmente separadas y requerir confirmación.

La dirección visual elegida es el diseño tipo lista accordion:
- Cada fila de usuario cerrada debe mostrar:
  - Avatar o iniciales.
  - Nombre.
  - Username.
  - Role.
  - Status.
  - Número de dispositivos.
  - Chips de permisos.
  - Last seen.
  - Icono de expandir/contraer.
  - Menú de acciones si resulta útil.

La sección expandida de un usuario debe incluir:

1. Card de detalles de usuario
   - Todos los campos editables existentes en la implementación actual.
   - Selector de role.
   - Selector de status.
   - Max devices.
   - Cualquier otro campo que ya exista en el código real.

2. Card de permisos
   - Heatmap access.
   - Metric selector access.
   - Estimated field access.
   - Cualquier permiso adicional que exista actualmente en el código.

3. Card de seguridad
   - Set password.
   - Reset password.
   - Cualquier funcionalidad existente relacionada con contraseña o estado de contraseña.
   - Delete user debe aparecer como acción destructiva clara.

4. Card de dispositivos
   - Lista de dispositivos existente.
   - Device ID.
   - Información de navegador/plataforma/dispositivo.
   - Fecha de creación.
   - Last seen.
   - Delete device.
   - Delete all devices.
   - Preservar cualquier comportamiento actual de gestión de dispositivos.

Requisitos del header:
- Mantener búsqueda de usuarios/dispositivos.
- Mantener refresh/manual refresh.
- Mantener contador de usuarios.
- Añadir o conservar botón Create user.
- Create user debe abrir un modal/drawer compacto usando la lógica actual de creación de usuario.

Búsqueda:
- Preservar el comportamiento actual de búsqueda.
- Si la búsqueda actual incluye dispositivos, mantenerlo.
- La UI debe dejar claro que la búsqueda aplica a usuarios o dispositivos.

Comportamiento:
- Sólo debe haber un usuario expandido a la vez.
- Por defecto se puede expandir el primer usuario o el usuario actualmente seleccionado si ya existe ese estado.
- Guardar debe usar la lógica actual de save/update.
- Refresh debe usar la lógica actual de refresh.
- Las acciones de borrado deben usar la lógica actual, pero añadiendo confirmación si no existe ya.

Estilo visual:
- Mantener dark theme de Rainmapper.
- Usar espaciado compacto.
- Usar bordes sutiles y cards con esquinas redondeadas.
- Usar azul/cyan como color principal.
- Estado enabled: punto verde + etiqueta.
- Estado disabled: punto gris + etiqueta.
- Badges de role:
  - admin: azul/cyan.
  - basic/free: gris neutro.
  - viewer/read-only: teal.
  - editor, si existe: violeta.
- Chips de permisos:
  - Heatmap: verde.
  - Metrics: azul.
  - Estimated: violeta.
- Botones destructivos:
  - rojo outline o rojo sólido según severidad.
  - Evitar que las acciones destructivas sean demasiado prominentes en la fila normal.

Enfoque de implementación:
1. Primero inspecciona la página/componente actual.
2. Identifica todos los campos y acciones actuales.
3. Prepara un plan corto de implementación antes de editar.
4. Refactoriza la UI en componentes más pequeños si tiene sentido, por ejemplo:
   - UserManagementPage.
   - UserRow.
   - ExpandedUserPanel.
   - UserDetailsCard.
   - PermissionsCard.
   - SecurityCard.
   - DevicesCard.
   - CreateUserModal.
   - ConfirmDialog.
5. Mantén el flujo de datos compatible con la implementación existente.
6. Evita reescrituras amplias no relacionadas con esta pantalla.
7. No cambies código backend/API salvo que sea estrictamente necesario.
8. Después de implementar, verifica que todas las operaciones anteriores de mantenimiento de usuarios siguen estando disponibles desde la UI.

Criterios de aceptación:
- Los usuarios existentes se muestran en filas compactas tipo accordion.
- Al expandir un usuario se muestran todos los campos editables y acciones disponibles.
- Create user ya no ocupa espacio permanente en la pantalla; se abre en modal o drawer.
- Todos los permisos actuales siguen siendo editables.
- Todas las acciones actuales de contraseña siguen disponibles.
- Todas las acciones actuales de dispositivos siguen disponibles.
- El comportamiento actual de refresh y search sigue funcionando.
- La UI es claramente más compacta que la actual.
- No se rompe ningún contrato existente con backend.
- No se pierde ningún campo ni acción actual.

Antes de hacer cambios, muéstrame:

1. Qué archivo(s) contienen la UI actual de mantenimiento de usuarios.
2. Qué campos y acciones existentes has encontrado.
3. Qué componentes propones crear o modificar.
4. Qué riesgos ves si el prototipo visual no coincide exactamente con el código real.

No apliques todavía la refactorización completa. Espera mi confirmación.