# Modo histórico — validación local, 22/09/2026

Código sin bump/release sobre HEAD `dda52e8`; HA real no actualizado.
[Diseño central](../mushrooms/prediction-map-specification-es.md#modo-histórico-del-mapa-22092026).

## Validación

- 76 pruebas dirigidas iniciales y regresión adicional de coordenadas ausentes.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: 1.734 pruebas, 52 skips,
  OK; smoke completo correcto. Se actualizó una expectativa de búsqueda de usuarios
  por el permiso nuevo y se repitió la suite con éxito.
- `node tests/prediction_map_browser_check.mjs /private/tmp/rainmapper-maplibre.js
  /private/tmp/rainmapper-maplibre.css`: navegador con API fixture, 54 consultas
  de predicción y 5 históricas. Permisos independientes, calendario, fallback,
  ficha, fecha histórica en predicción, zoom 11→13→12→11 sin consultas, exclusión
  de cobertura, regreso a región cargada sin consultar, fallo y revocación.
- Imágenes HA local y worker reconstruidas; contenedores existentes recreados,
  worker idle en ambos carriles comprobado antes. Volúmenes/destinos conservados.
- `tmp/historical-map-20260922/parity.py`: 220 archivos HA y 125 worker comparados
  contra los COPY de sus Dockerfiles, cero diferencias. Imágenes efectivas:
  HA `sha256:0ebdcaecc8cb5de6325fb6de7a79933bdb6036d2aafdca3aca19636ffa3ca440`;
  worker `sha256:72639e326a726f403f443503fab82c5de51f39cfab1668e163a52a17b0e91e0b`.
- HTTP localhost 8101 devuelve 200; logs HA: modo serve y schedule false.

## Medición real acotada

`tmp/historical-map-20260922/benchmark.py`: lector residente dentro de ambos
contenedores, datos HA local y caché ya persistida del coordinador local del
worker. Sin acceder al coordinador real ni regenerar runtimes. Fecha 2026-09-18,
21 días, corte 2026-09-17; generación `20260921T235014433161Z-ff236da72107`.
Resultados completos en el JSON junto al script.

| Consulta | Estaciones con datos | Páginas | HA local | Worker | Respuesta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Zona pequeña, lector frío | 80 | 1 | 0,754 s | 0,708 s | 31,5 KiB |
| Misma zona, lector cargado | 80 | 1 | 0,169 s | 0,155 s | 31,5 KiB |
| Extensión excluyendo zona anterior | 28 nuevas | 1 | 0,116 s | 0,102 s | 11,7 KiB |
| Zona mediana | 234 | 3 | 0,494 s | 0,447 s | 92,1 KiB total |

Bounds pequeña `[1.7,42,2.2,42.5]`, extensión `[1.7,42,2.5,42.5]`, mediana
`[1.1,41.7,2.7,42.6]`. Catálogo selecciona 88, 32 y 297 estaciones; aparecen 80,
28 y 234 con datos. Hashes de las filas idénticos en ambos ejecutores. Extensión
lee sólo 2.423 filas diarias frente a 7.117 iniciales, sin recalcular las previas.

Tiempos del **Mac**, con protocolo del lector pero sin espera HTTP/worker/interfaz;
no son latencia de extremo a extremo ni medida RPi. Usuario confirmó una carga
real en Safari: 20/09/2026, 64 estaciones, 6,1 s. No habilitados automáticamente:
el usuario activó Carlos desde mantenimiento. Sin lanzar entrenamiento/precálculo;
no autoriza release.

## Correcciones durante la prueba del usuario

La estación `AEMET:0349` (Sant Julià de Vilatorta) tiene lat/lon nulos en registros
diarios de 2025. Reproducción: fecha 2025-09-21, 21d, bounds
`[1.423218,41.921656,2.576782,42.477123]`. API HTTP 200, pero el navegador rechazaba
la fila sin coordenadas (`history_invalid_response`), abortando toda la zona.
Ahora el lector usa la ubicación comprobada del catálogo si falta en el registro
y declara su procedencia. Prueba específica preserva lluvia y demás estaciones.

La ficha completa deja de reutilizar el modal general: aviso dentro del popup,
reintento y caché de ocho detalles. También se corrigió el estado activo de la
ficha al reemplazar el popup, el contraste del error, el selector estrecho en
móvil, el solapamiento de la etiqueta y la fecha visible de cabecera. Compatibilidad
sin `crypto.randomUUID`, con alternativa como en predicción; no se atribuye a esta
API la causa confirmada del fallo de datos.

Ajuste visual posterior: etiqueta «Modo histórico · DD/MM/AAAA». Cambio sólo
de presentación; verificado el texto `Modo histórico · 20/09/2026 · 6.1 s`, sintaxis
JS y diff; HA local reconstruido y paridad 220/125 sin diferencias. No se repite
el circuito científico ni se reinicia el worker por este formato.

### Calendario integrado posterior

Sustituido el input date nativo por calendario visible, con fondo blanco,
bordes/colores del buscador de topónimos y selección azul. Mes y año seleccionables
directamente; flechas de mes, atajos Ayer/Hace un año, semana de lunes a domingo,
fecha elegida DD/MM/AAAA y navegación por teclado (flechas, Home/End, PageUp/Down).
Fechas fuera de 2000–ayer deshabilitadas. Recorrer meses o seleccionar días no
calcula hasta Aplicar. Aviso de zona visible permanente y explicación desplegable.

Prueba navegador extendida OK: 29/02/2024→01/03/2024 con teclado, límite inferior,
fechas futuras, atajos, ausencia de consultas durante selección y regresión de
mapa/fallback/ficha/caché. Capturas revisadas a 360×640, 390×844 y 1280×900;
días de al menos 40 px, panel dentro de pantalla. JSON de etiquetas ES/CA/EN,
sintaxis JS y diff correctos. Log `/private/tmp/rainmapper-history-calendar-browser.log`.
HA local reconstruido/recreado, HTTP 200 y paridad efectiva 220/125 sin diferencias.
No cambia cálculo ni worker; sin reinicio del worker ni nueva release.

## Conservación y documentación pendiente

Prueba final real `tmp/historical-map-20260922/live.mjs`, sin fixtures de datos
meteorológicos ni de API (sólo fondo cartográfico neutro y librería local):
**OK, cero errores**. Fecha 2025-09-21, 141 estaciones en dos páginas con ambos
ejecutores. Cabecera/fecha/botón correctos, zoom sin petición adicional, ficha
de AEMET con coordenadas del catálogo sin modal, reapertura desde caché, vuelta
a hoy. Cinco consultas totales (dos worker, ficha, dos local). Cuenta temporal
retirada y registros de usuarios existentes iguales a los del inicio de la prueba.

Medida HTTP/interfaz completa: worker **48,268 s**, de los que el lector declara
328 ms de cálculo; local **0,641 s**, lector 374 ms. La espera adicional está fuera
del cálculo meteorológico; no se ha aislado aquí entre cola, sondeo, transporte
y preparación. No confundirla con los tiempos del lector. El worker conserva
sus asociaciones y no se ha cambiado la planificación para ocultar esa latencia.
Resultado en `tmp/historical-map-20260922/live.json`; captura `live-history.png`.

Hashes antes/después conservados:

- Observaciones privadas: `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
- Política/suspensiones local: `514386525a5b54872cb67dce72efa4a8bcab941bbcf381691500d23cf5cf4e92`.
- Usuarios antes de la activación manual: `4af0d4f3833c4b815452befba9e4b48baed8e7616322259e2b51ee541024ed70`.
  Después el usuario habilitó Carlos. Pruebas HTTP usan cuentas temporales vía
  mantenimiento, retiradas al terminar y comparando los registros existentes.
- Coordinador principal: `5a9d558d8237c843502ee8d19791e009f30707df972224fe6919fbc027a46b10`.
- Coordinadores adicionales: `22055bcf85d410f42a24e2d347467fd8f4e78499f47618f768dfeb26730cc5c0`.
- Ambos tokens verificados por hash; valores no expuestos ni alterados.

Principal `http://100.111.77.48:8100`, adicional `http://rainmapper-ha-ui:8100`.
Sin SSH/Tailscale, entrenamientos ni precálculos. Observaciones privadas fuera
del alcance. Cambios documentales del cierre anterior revisados y sin commit;
32 enlaces del archivo histórico trasladado corregidos. Sin commit/push.
