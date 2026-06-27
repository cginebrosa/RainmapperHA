# Rediseño del Control Panel de Rainmapper

Quiero rediseñar la pantalla existente del Control Panel de Rainmapper.

Tú tienes acceso al repo real de la aplicación, así que NO reconstruyas la pantalla desde cero salvo que sea absolutamente necesario. Primero inspecciona el código actual y localiza la implementación real del Control Panel, sus datos, llamadas API, handlers, acciones, estados, enlaces y componentes existentes.

El objetivo es refactorizar la pantalla actual, que ahora es demasiado larga y difícil de gestionar, hacia una UI más moderna, compacta y organizada por pestañas, usando el prototipo adjunto sólo como referencia visual.

Imagen de referencia visual:

docs/ui/rainmapper-control-panel-tabs-prototype.png

Importante:
- Conserva toda la funcionalidad existente.
- Conserva todas las llamadas actuales al backend/API.
- Conserva todos los campos, acciones, botones, enlaces, estados y textos funcionales existentes.
- No inventes nuevos contratos de backend.
- No elimines ninguna capacidad actual.
- No cambies la lógica de ejecución, actualización, generación de mapas, visores, logs o errores salvo que sea imprescindible.
- Usa el prototipo como referencia visual y de layout, no como especificación funcional exacta.
- Si el prototipo no muestra algún dato o acción que sí existe en el código actual, debe conservarse igualmente.

## Problema actual

La pantalla actual del Control Panel muestra demasiada información en una sola página vertical:

- Acciones principales.
- Estado general.
- Datos de versión, status, acción actual, started, finished, duración, progreso, exit code, next schedule.
- URLs o rutas de visores/mapas.
- Estado de fuentes de datos.
- Acciones por fuente.
- Listas de errores/deshabilitados.
- Botones para enable/disable.
- Visores.
- Mapas generados.
- Último log.

El resultado es una página muy larga que obliga a hacer mucho scroll y dificulta encontrar rápidamente lo importante.

## Objetivo del rediseño

Crear una UI compacta tipo dashboard SaaS dark mode, organizada por pestañas:

- Resumen.
- Fuentes de datos.
- Visores.
- Mapas.
- Logs.
- Errores.

La pestaña principal será `Resumen`, que debe dar una visión rápida del estado general y permitir acceso a las acciones principales sin perder funcionalidad.

## Dirección visual

Usar la estética actual de Rainmapper:

- Dark mode.
- Fondo principal dark navy / charcoal.
- Cards ligeramente más claras que el fondo.
- Bordes sutiles.
- Esquinas redondeadas.
- Acento principal azul/cyan.
- Estados OK en verde.
- Errores o acciones destructivas en rojo.
- Warnings en ámbar si existen.
- Tipografía compacta y clara.
- Layout más denso, pero legible.
- Evitar una página vertical enorme.
- Priorizar tarjetas, tablas compactas y pestañas.

## Layout general

La estructura deseada es:

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar                                                      │
│                                                              │
│ Rainmapper                                                   │
│ Panel                                                        │
│ Maps                                                         │
│ Datos                                                        │
│ Estaciones                                                   │
│ Alertas                                                      │
│ Tareas                                                       │
│ Meteocat                                                     │
│ AEMET                                                        │
│ Wunderground                                                 │
│ Logs                                                         │
│ Usuarios                                                     │
│ Ajustes                                                      │
├──────────────────────────────────────────────────────────────┤
│ Header                                                       │
│ Rainmapper | Panel de Control                                │
│ [Selector/app] [Actualizar ahora] [Última actualización]      │
├──────────────────────────────────────────────────────────────┤
│ Tabs                                                         │
│ Resumen | Fuentes de datos | Visores | Mapas | Logs | Errores│
├──────────────────────────────────────────────────────────────┤
│ Contenido de la pestaña activa                               │
└──────────────────────────────────────────────────────────────┘
```

## Sidebar

Conservar o adaptar la navegación existente.

La sección activa debe ser el Control Panel de Rainmapper.

Ejemplo de items:

```text
Panel
Maps
Datos
Estaciones
Alertas
Tareas
Meteocat
AEMET
Wunderground
Logs
Usuarios
Ajustes
```

No es obligatorio cambiar toda la navegación global si ya existe una sidebar compartida. Si la sidebar actual pertenece a Home Assistant o a otro contenedor, no reimplementarla innecesariamente.

## Header superior

Debe mostrar:

```text
Rainmapper    Panel de Control
[Rainmapper] [Actualizar ahora] [Última actualización: HH:MM:SS]
```

Requisitos:

- Mantener la acción actual de refresh/update.
- Si actualmente existe `Run update`, `Generate maps`, `Run all`, `App settings`, `Users`, conservar esas acciones.
- Las acciones principales pueden estar en el header o justo debajo como una barra de acciones.
- El botón más importante debe ser `Run all`.
- `Run update`, `Generate maps`, `App settings` y `Users` deben seguir siendo accesibles.

Barra de acciones recomendada:

```text
Acciones rápidas
[Run all] [Run update] [Generate maps] [App settings] [Users]
```

## Tabs principales

Crear las siguientes pestañas, siempre que encajen con la estructura real del código:

```text
Resumen
Fuentes de datos
Visores
Mapas
Logs
Errores
```

Si ya existe un sistema de tabs/componentes en el proyecto, reutilizarlo.

Si no existe, implementar tabs simples con estado local.

Estado sugerido:

```ts
const [activeTab, setActiveTab] = useState<"summary" | "sources" | "viewers" | "maps" | "logs" | "errors">("summary");
```

## Pestaña Resumen

La pestaña `Resumen` debe ser la vista principal.

Debe incluir:

### 1. Cards de resumen general

Mostrar tarjetas compactas:

```text
Estado
Versión
Próxima ejecución
Fuentes OK
Visores
Mapas generados
```

Ejemplo visual:

```text
┌────────────┐ ┌────────────┐ ┌─────────────────┐ ┌────────────┐ ┌──────────┐ ┌───────────────┐
│ Estado     │ │ Versión    │ │ Próxima ejecución│ │ Fuentes OK │ │ Visores  │ │ Mapas generados│
│ Idle       │ │ 0.2.145    │ │ 2026-06-27 05:00│ │ 4/4        │ │ 4        │ │ 7             │
└────────────┘ └────────────┘ └─────────────────┘ └────────────┘ └──────────┘ └───────────────┘
```

Estos datos deben salir del estado/API actual, no de datos inventados.

### 2. Tabla compacta de fuentes de datos

Mostrar una tabla resumen de fuentes:

```text
Fuente | Estado | Rows | Stations | Duración | Actualizado | Acción
```

Fuentes actuales vistas en pantalla:

- Meteoclimatic.
- Meteocat.
- Wunderground.
- AEMET.

Pero no hardcodear si el código actual ya genera esta lista dinámicamente.

Cada fuente debe conservar su acción actual, por ejemplo:

```text
Actualizar
Update only
```

### 3. Cards pequeñas de errores actuales

Mostrar resumen compacto de errores/deshabilitados:

```text
Wunderground 404
0 current / 6 disabled

Wunderground parse errors
0 current / 9 disabled
```

Incluir link o botón:

```text
Ver detalles de errores
```

Ese botón puede llevar a la pestaña `Errores`.

### 4. Visores rápidos

Mostrar botones compactos para abrir visores:

```text
Leaflet viewer
MapLibre viewer
Heatmap experiment
Bokeh 21 días
```

Conservar exactamente los visores/enlaces existentes en el código actual.

### 5. Mapas recientes

Mostrar sólo los últimos mapas en el resumen, por ejemplo 3 o 4.

Cada fila:

```text
Nombre del mapa
Archivo · tamaño · fecha
[Open] [Download si existe]
```

Incluir link:

```text
Ver todos los mapas
```

Ese link debe cambiar a la pestaña `Mapas`.

### 6. Último log resumido

Mostrar una previsualización compacta del último log:

- Altura limitada.
- Scroll interno si hace falta.
- Botón `Abrir log completo`.

No mostrar el log completo en la vista principal si hace que la página sea demasiado larga.

## Pestaña Fuentes de datos

Debe contener el detalle completo de fuentes.

Objetivo: reemplazar las cards enormes actuales por una tabla o cards compactas.

Debe preservar:

- Nombre de fuente.
- Estado.
- Exit code.
- Rows.
- Stations.
- Duration.
- Updated.
- Mensajes de procesamiento.
- Acción individual `Update only` o equivalente.
- Cualquier campo adicional actual.

Diseño sugerido:

```text
Fuente | Estado | Exit | Rows | Stations | Duration | Updated | Mensaje | Acción
```

Si hay muchos detalles por fuente, permitir expandir una fila.

Comportamiento recomendado:

- La tabla muestra el resumen.
- Al expandir una fuente se muestran detalles técnicos o mensajes largos.
- Las acciones individuales siguen usando los handlers existentes.

## Pestaña Visores

Debe contener todos los enlaces a visores existentes.

Conservar:

- Leaflet viewer.
- MapLibre viewer.
- MapLibre heatmap experiment.
- Bokeh maps.
- Bokeh 21 days si existe.
- Cualquier visor adicional presente en el código actual.

Diseño sugerido:

```text
Visor | URL/Ruta | Descripción | Acción
```

Acciones:

```text
Open
Copy link si existe utilidad o es fácil
```

No cambiar las rutas generadas por backend.

## Pestaña Mapas

Debe contener la lista completa de mapas generados.

En la pantalla actual aparecen mapas como:

- 01 Tomap Last day.
- 02 Tomap Last week.
- 03 Tomap Last two weeks.
- 04 Tomap Last three weeks.
- 05 Tomap Last month.
- 06 Tomap Last two months.
- 07 Tomap Last three months.

No hardcodear: usar la lista real que ya venga del estado/API.

Diseño sugerido:

```text
Mapa | Archivo | Tamaño | Fecha generación | Acciones
```

Acciones:

```text
Open
Download si existe actualmente
Copy link si resulta útil
```

La pestaña `Resumen` sólo muestra los mapas recientes. La pestaña `Mapas` muestra todos.

## Pestaña Logs

Debe contener el log completo.

Requisitos:

- Mantener el contenido real del log actual.
- Mostrarlo en una zona tipo terminal/monospace.
- Altura amplia, con scroll interno.
- Botón `Open` o `Abrir log completo` si ya existe.
- Opcionalmente añadir `Copy log` si es sencillo y no rompe nada.
- No cargar logs de forma distinta si ya existe una mecánica actual.

Diseño:

```text
Último log
[Abrir log completo]

┌──────────────────────────────────────────────┐
│ terminal output...                           │
│ terminal output...                           │
└──────────────────────────────────────────────┘
```

## Pestaña Errores

Debe contener el detalle completo de errores/deshabilitados que ahora aparece en la pantalla larga.

En la pantalla actual hay:

- Wunderground 404.
- Wunderground parse errors.
- Listas de estaciones actuales.
- Listas de estaciones deshabilitadas.
- Botones:
  - Disable all.
  - Enable all.

Conservar:

- Current.
- Disabled.
- Listas completas.
- Altitud.
- Motivo de error si existe.
- Botones `Disable all` y `Enable all`.
- Cualquier acción adicional actual.

Diseño sugerido:

```text
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ Wunderground 404            │ │ Wunderground parse errors   │
│ 0 current / 6 disabled      │ │ 0 current / 9 disabled      │
│                             │ │                             │
│ Current                     │ │ Current                     │
│ None                        │ │ None                        │
│                             │ │                             │
│ Disabled                    │ │ Disabled                    │
│ - estación...               │ │ - estación...               │
│                             │ │                             │
│ [Disable all] [Enable all]  │ │ [Disable all] [Enable all]  │
└─────────────────────────────┘ └─────────────────────────────┘
```

Si las listas son largas:

- Usar scroll interno.
- O mostrar las primeras N y botón `Mostrar más`.

## Estado general detallado

Los campos actuales de estado general que deben conservarse en alguna pestaña o sección:

- Version.
- Status.
- Action.
- Started.
- Finished.
- Duration.
- Current step.
- Progress.
- Exit code.
- Next schedule.
- Bokeh maps.
- Leaflet viewer.
- MapLibre viewer.
- MapLibre heatmap experiment.
- Last published.

En la pestaña `Resumen`, mostrar los más importantes.

Los demás pueden ir en una sección expandible llamada:

```text
Detalles técnicos
```

O en una card compacta dentro de `Resumen`.

No eliminar ningún dato actual.

## Comportamiento

Preservar todos los handlers actuales:

- Run update.
- Generate maps.
- Run all.
- App settings.
- Users.
- Refresh.
- Update only por fuente.
- Open Leaflet viewer.
- Open MapLibre viewer.
- Open heatmap experiment.
- Open Bokeh maps.
- Open maps generados.
- Open last log.
- Disable all.
- Enable all.
- Cualquier otro handler existente.

Si alguna acción actualmente se implementa como link normal, mantenerla como link.

Si alguna acción actualmente llama API, mantener exactamente esa llamada.

## Confirmaciones

Para acciones potencialmente destructivas o masivas, añadir confirmación si no existe ya:

- Disable all.
- Enable all, si afecta a muchas estaciones.
- Run all, si lanza un proceso largo o costoso.
- Generate maps, si actualmente tarda mucho.

La confirmación debe ser compacta y no bloquear acciones simples como abrir visores o refrescar.

No añadir confirmaciones innecesarias que empeoren el uso diario.

## Loading y estados intermedios

Conservar o mejorar los estados existentes:

- Loading.
- Running.
- Idle.
- Error.
- Empty states.

Cuando hay una acción en curso:

- Deshabilitar botones que no deban ejecutarse simultáneamente.
- Mostrar feedback visual.
- Mantener los mensajes/status existentes.

## Responsive

No hace falta una versión móvil perfecta en esta primera fase, pero el layout debe ser razonablemente adaptable.

Para pantallas estrechas:

- Las cards de resumen pasan a 1 o 2 columnas.
- Las tablas pueden tener scroll horizontal.
- Las pestañas pueden hacer overflow horizontal.
- El log debe mantener scroll interno.

## Componentes sugeridos

Refactorizar en componentes si mejora claridad, por ejemplo:

```text
RainmapperControlPanelPage
├── ControlPanelHeader
├── QuickActionsBar
├── ControlPanelTabs
├── SummaryTab
│   ├── SummaryMetricCards
│   ├── SourcesSummaryTable
│   ├── CurrentErrorsSummary
│   ├── QuickViewersCard
│   ├── RecentMapsCard
│   └── LastLogPreview
├── SourcesTab
│   ├── SourcesTable
│   └── SourceDetailsRow
├── ViewersTab
│   └── ViewersList
├── MapsTab
│   └── GeneratedMapsList
├── LogsTab
│   └── LogViewer
├── ErrorsTab
│   ├── ErrorGroupCard
│   └── StationErrorList
├── StatusBadge
├── MetricCard
└── ConfirmDialog
```

No crear todos estos componentes obligatoriamente si el código actual es más simple, pero sí evitar que un único componente gigante siga creciendo.

## Estado local sugerido

Adaptar a la estructura real existente.

Ejemplo orientativo:

```ts
const [activeTab, setActiveTab] = useState("summary");
const [confirmAction, setConfirmAction] = useState(null);
const [expandedSourceId, setExpandedSourceId] = useState(null);
```

No duplicar estado que ya exista en el código.

## Criterios de aceptación

La refactorización se considerará correcta si:

- La pantalla deja de ser una página vertical enorme.
- La información queda organizada por pestañas.
- La pestaña `Resumen` permite entender el estado del sistema sin hacer scroll largo.
- Todas las acciones actuales siguen disponibles.
- Todos los datos actuales siguen visibles en alguna pestaña/sección.
- Las fuentes de datos se ven en formato compacto.
- Los errores/deshabilitados se gestionan desde una pestaña específica.
- Los mapas se gestionan desde una pestaña específica.
- El log completo se gestiona desde una pestaña específica.
- Los visores siguen siendo accesibles.
- No se rompe ningún contrato backend/API.
- No se pierde ninguna funcionalidad existente.
- El diseño se mantiene alineado con Rainmapper dark mode.
- El código queda más mantenible o al menos no más complejo que antes.

## Proceso de trabajo obligatorio

Antes de implementar cambios, haz una fase de inspección y dime:

1. Qué archivo(s) contienen actualmente el Control Panel.
2. Qué datos/campos actuales muestra la pantalla.
3. Qué acciones/handlers actuales existen.
4. Qué llamadas API o endpoints se usan.
5. Qué componentes propones crear o modificar.
6. Qué riesgos ves al adaptar el prototipo al código real.
7. Qué elementos del prototipo no coinciden exactamente con la implementación actual.

No apliques todavía la refactorización completa. Espera mi confirmación antes de modificar la UI.

---
