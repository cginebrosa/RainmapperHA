# Capa de observaciones — implementación local, 23/09/2026

Autorizada por el usuario después de investigar los datos. Solicita despliegue
radial de coincidencias con fechas pequeñas, permiso por usuario desactivado por
defecto y control general móvil, también desactivado inicialmente.

## Resultado

- Botón de ojos, selector especie/recuento y setas. Fichas con los campos pedidos
  e identificador para distinguir registros. Coincidencias conservadas, no borradas.
- Spiderfy con conectores a posición real y fecha DD/MM/AAAA por observación;
  grupos grandes navegables de ocho en ocho. Sin alterar coordenadas originales.
- Capa independiente de histórico y predicción; no filtra por fecha ni solicita
  recálculos al worker. Recursos únicamente al activar la capa y elegir especie.
- `can_use_observations_map` en mantenimiento, auth y endpoints; apagado incluso
  para administradores. No se habilitó automáticamente a ningún usuario real/local.
- `maplibre_observations_mobile_enabled` en configuración general del complemento,
  schema, run.sh, traducción HA y opciones locales. False por defecto.

## Evidencia local

Copia local leída: 515 observaciones de 17 especies, todas con coordenadas válidas.
27 grupos con igual especie/coordenadas contienen 73 observaciones; 24 grupos
contienen fechas todas diferentes. Tres grupos coinciden también en fecha, ocho
registros: esto no demuestra duplicidad y no se han modificado.

Respuestas medidas en la implementación instalada: especies 1.573 bytes, página
más grande 4.982 bytes, suma de puntos de las 17 especies 30.530 bytes. La ficha
se consulta aparte; no viajan fotografías, notas ni documentación de entrenamiento.

Pruebas dirigidas iniciales: 26 OK (lectura/paginación/revisiones/límites, permisos
por rol, revocación, rutas independientes y opción móvil). Navegador completo OK:
fechas anteriores/posteriores al histórico, dos registros con misma fecha, líneas,
ficha con texto escapado, clic con predicción activa sin consulta, cambio de
viewport sin perder histórico, móvil bloqueado/habilitado, usuario sólo con
observaciones y retirada de capa al revocar permiso.

Log de navegador `/private/tmp/rainmapper-observations-browser.log`; imagen
`tmp/observations-map-20260923/spiderfy.png`. Los primeros intentos del test
necesitaron fijar escritorio explícitamente y esperar la activación asíncrona de
predicción antes del clic. No fueron fallos de las consultas de observaciones.

Smoke final: **1.744 pruebas, 52 skips, OK**, 76,990 s y comprobaciones adicionales
del script correctas. Log `/private/tmp/rainmapper-observations-smoke-final.log`.
Primera pasada: seis pruebas HTTP bloqueadas por sandbox y una expectativa del
buscador de Usuarios que necesitaba incorporar el nuevo permiso. Actualizada la
expectativa y repetido el smoke fuera del sandbox; final correcto.

HA local reconstruido/recreado: paridad efectiva de 223 archivos sin diferencias,
`tmp/observations-map-20260923/local-parity.json`. Config.js servido por HTTP
confirma `observationsMobileEnabled: false`. Worker conserva contenedor, fecha
de arranque e imagen. Observaciones privadas de repo/local y política de
suspensiones conservan las huellas registradas antes de este trabajo.

Sin bump, commit ni publicación. HA real permanece en 0.2.320 según confirmación
del usuario; no se escribe allí. No se reinició el worker ni se lanzaron trabajos
operativos. Esto no constituye la validación conjunta requerida para una release.

## Corrección posterior: GIS aceptado en la ficha

El usuario detecta «No informado» pese a haber guardado una recuperación GIS/DEM.
Confirmado: los campos `observed_*` estaban vacíos y los valores aceptados estaban
persistidos en `site_context.gis_recovery.values`. La capa sólo leía los primeros.
Ahora combina valores de campo y recuperación aceptada con `valid_recovery`, sin
consultar GIS ni modificar registros, y marca los aportes recuperados como
«GIS aceptado». No reutiliza recuperaciones cuyas coordenadas ya no coinciden.

27 pruebas dirigidas OK, navegador completo repetido OK con comprobaciones de
texto GIS en hosts y bosque. HA local reconstruido/recreado, 223 archivos con
paridad efectiva; ficha indicada comprobada dentro del contenedor. Huellas de
observaciones repo/local y suspensiones intactas respecto al inicio de esta
corrección. El smoke de 1.744 anterior no incluye esta última modificación.
Logs: `/private/tmp/rainmapper-observations-gis-tests.log` y
`/private/tmp/rainmapper-observations-browser.log`. Paridad posterior en
`tmp/observations-map-20260923/gis-local-parity.json`.

Ajuste posterior solicitado: hosts con `common_names` del idioma actual y bosque
con su etiqueta traducida; nombre científico como fallback si falta traducción.
Siete pruebas del módulo OK, incluyendo ca/es/en y fallback sin nombre común.
HA local reconstruido/recreado, HTTP 200, paridad efectiva de 223 archivos y
nombres catalanes comprobados en la observación dentro del contenedor. Sin cambios
de frontend ni nuevo smoke; verificación proporcional al formateo del servidor.

## Fase lunar reutilizable (24/09)

`rainmapper_core/lunar_phase.py` calcula fase continua y fracción iluminada,
sentido, categoría, hora de referencia y versión. Sin dependencias nuevas ni
acceso a datos. Adaptación aproximada de SunCalc 1.9.0, licencia dentro del módulo;
fechas sin hora a las 12 UTC, timestamps con zona explícita. Nueva ≤1% y llena
≥99% son categorías visuales, no instantes de eventos. No se modifica entrenamiento.

El detalle invoca la función sólo para esa observación; si la fecha es inválida,
el resto de la ficha permanece disponible. El frontend dibuja el terminador de
la luna según la fracción, junto a Fecha/Área, con relieve SVG y nombre ca/es/en.

Validación: 12 pruebas dirigidas (`tests.test_lunar_phase` y
`tests.test_mushroom_map_observations`) OK. Referencias independientes de
[USNO septiembre 2025](https://aa.usno.navy.mil/calculated/moon/phases?date=2025-09-01&format=p&nump=5&submit=Get+Data),
zona/fecha, entradas inválidas, valores numéricos y consulta sólo en detalle.
Navegador final OK con cuatro fases y captura visual, alineación sin overflow,
histórico/predicción activos y resto de casos del harness.
Log `/private/tmp/rainmapper-observations-moon-browser.log`; capturas
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-61GhoV/observations-moon-*.png`.

HA local reconstruido/recreado, HTTP 200; 224 archivos efectivos sin diferencias,
huella del manifiesto `9becbb6b89db385be113ab54e2469d9ec43816389936a65157ef7c4e0b23c517`.
Registro mostrado por el usuario consultado dentro del contenedor: fecha
2025-09-04, categoría waxing y fracción 0,8750658365. Huellas privadas y política
comparadas con `tmp/observations-map-20260923/moon-protected-before.json`, intactas.
Worker conserva ID/arranque/imagen; sin reiniciarlo ni lanzar trabajos. Ninguna
publicación nueva; no se presenta el smoke anterior como validación de esta fase.

Interacción posterior (24/09): setas y contadores alternan apertura/cierre.
La misma observación cierra su ficha incluso con petición pendiente; otra
observación la sustituye. El mismo contador repliega el grupo y su ficha sin
consulta HTTP. Navegador repetido OK con ambos tipos de icono, cancelación,
cambio de registro y reapertura del grupo. HA local reconstruido/recreado,
HTTP 200 y 224 archivos sin diferencias; manifiesto final
`33d91b11c01dab38081b99b1f165b67ed2cba5b1e19c1819880628d6153a0d97`.
Se reutiliza el log `/private/tmp/rainmapper-observations-moon-browser.log`.
