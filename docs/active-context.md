# Contexto activo — HA 0.2.326 publicada; instalación pendiente (27/09/2026)

Leer primero [codex-start-here.md](codex-start-here.md). Este documento basta para
retomar; [todo.md](todo.md) amplía prioridades. No reconstruir sesiones leyendo
informes históricos. Los antecedentes completos se conservaron en el
[archivo del repaso del 27/09](reports/session-context-before-refresh-2026-09-27.md).

## Estado y siguiente paso

- **HA 0.2.326 publicada y aceptada en local por el usuario.** Instalación real
  pendiente a cargo del usuario. Añade coordenadas, incertidumbre y foto ampliable
  a las fichas del mapa; incorpora los scripts de memoria ya validados. Tags y
  plataformas verificados; [release](reports/release-ha-0.2.326-2026-09-27.md).

- **HA real 0.2.325 instalada**, confirmada por el usuario y revalidada en
  `/Volumes/share/rainmapper/diagnostics/runtime_state.json` durante este repaso:
  `app_version=0.2.325`, arranque `2026-09-26T20:11:03.600Z`.
- **Worker 1.1.6 reconstruido y arrancado el 27/09 por petición del usuario**,
  sin nueva release HA. Imagen efectiva
  `sha256:79440107723a685b3e8eb32b2161a2ec0f9224f02cc7a09339101a4553eaa747`.
  122 archivos Python en paridad; 25 pruebas dirigidas correctas dentro de la
  imagen. Al verificar el arranque estaba `running/healthy`, `idle`, sin trabajos.
  Ese estado puntual no permite presumir que continúe libre: **revalidar antes
  de operarlo**, aunque los trabajos comprobados hayan terminado.
- Coordinador primario conservado: `http://100.111.77.48:8100`; adicional:
  `http://rainmapper-ha-ui:8100`. Identidad `worker_1a9a232c20fe2ee2`, M1 Personal.
  Configuración de ambos e identidad idénticas por hash antes/después; acceso
  autenticado a ambos correcto al arrancar. No cambiar destinos ni credenciales.
- **Ciclo del usuario completado y verificado el 27/09:** reconstrucción 2:05,
  V0 0:27, multiversión 10:04 (792/792 ajustes, 0 fallos); cinco versiones
  instaladas del lote `operational_20260926T223720Z`. Precálculo 9:39, revisión
  261 activa en HA/worker para 27/09–03/10, SHA idéntico leído en ambos SQLite.
  Worker sin reinicios/OOM, ambos carriles libres al comprobar. Pico cgroup
  6,86 GiB desde arranque, no RSS aislado ni pico atribuible a una fase.
  Hubo timeouts de comunicación recuperados. Codex no lanzó trabajos.
  [Resultados, tiempos y límites](reports/worker-evaluation-memory-2026-09-27.md).
  Rovelló/Els Ports reexaminado: RF–V3 da IFF 37 toda la semana; ver abajo.
- Pendientes aplazados: estado huérfano de HA tras perder worker; duración del
  precálculo (9 → 11 minutos). Ambos en TODO; no están corregidos por el rebuild.

## Corrección de memoria del worker

El contenedor anterior murió por OOM a las 22:58:59 del 26/09 (20:58:59 UTC),
salida 137. El trabajo `worker_job_XpH0Q6p3EQaUxiyF` llevaba unos ocho minutos,
aunque HA seguía mostrando `running`, 46 %, con lease caducada. Ese era el estado
observado durante el incidente, no el del nuevo contenedor ni una cola vigente.
Reconstrucción y V0 anteriores habían terminado; la caída ocurrió durante V6.

`biology-v5-lag.json`: 528.821.763 bytes, 3.493 muestras. No se recortan los
365 días ni el SMI. V2–V5 y V6 ahora comparten la misma entrada por contrato:
cargar `fixed`, evaluar sus consumidores, liberar; después lo mismo con `lag`.
Se comparte normalización por fuente y se conserva el orden final de resultados.
No hay caché permanente. El entrenamiento final es otro proceso con su propia
lectura; no confundir esta mejora con una única lectura en todo el pipeline.

Medición con archivos reales, **sin ajustar modelos**: pico RSS de carga V6
3,99 → 1,71 GiB (−57 %); lecturas por archivo 3 → 1. Las 25 pruebas incluyen
igualdad exacta de resultados sintéticos para 30/60/90 y 365 días. No demuestra
el pico completo ni garantiza por sí sola que el trabajo entero evite OOM.
[Implementación, medición, rebuild y límites](reports/worker-evaluation-memory-2026-09-27.md).

## Meteocat: reparación ya aplicada; preservar datos nuevos

HA 0.2.325 corrige el recorte del primer día UTC que sobrescribía lluvia y otros
campos con horas parciales. Reparación aplicada en real el 26/09 a las 20:09 UTC,
con add-on parado por el usuario: 6.700 filas / 24.034 celdas de 01/08–25/09/2026,
incluidas 1.171 lluvias; otras fuentes preservadas. YB 09/09=54,8 y 16/09=7,1 mm;
W9=44,7 y 14,5 mm. No se certifica todo el histórico anterior al 01/08.
[Release](reports/release-ha-0.2.325-2026-09-26.md),
[diagnóstico y reparación](reports/meteocat-partial-days-2026-09-26.md).

La reparación introdujo mezcla de coma/punto en el CSV: validación insuficiente.
El runner posterior recuperó 1.498 filas y reescribió todo el CSV con coma; lector
real comprobado, 33.707 filas y cinco columnas float64. La auditoría posterior
conservó las 24.034 celdas reparadas y ninguna clave estación/fecha desapareció.
Total histórico tras runner: 5.550.605 filas. **No ejecutar
`tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py`**: su candidata es anterior
a esos datos nuevos. Evidencia `after-runner.json` y `runner-history-audit.json`
en ese directorio. Si se necesita confirmar el último runner completo, leer su
registro vigente: aquel NOK describía un intento anterior, no el CSV reescrito.

## Histórico, piloto IDW y rovelló con sequía

- Muestreo: 668 pares cercanos y 10.103 comparaciones mensuales. No aparece un
  déficit general de Meteocat frente a AEMET; 88 jornadas de siete estaciones
  coinciden con el API oficial. Hay datos de origen incompletos: DF 06/07/2025
  publica 0 mm con 28/48 lecturas. No confundirlos con nuestra pérdida corregida.
  La auditoría de agosto detectó diferencias menores desde 09/08 y pérdidas
  ≥5 mm desde 13/08; no asegurar que antes no exista ningún problema.
  [Método y límites](reports/weather-cross-source-sample-2026-09-26.md).
- Usuario autorizó un piloto **local**, con datos y salidas en `docker-data`.
  Última sincronización verificada: generación
  `20260926T204049825478Z-635f090343b7`, 5.550.605 registros; 6,6 MB descargados,
  resto reutilizado. No presumir que coincide con HA después de nuevos runners.
  24 referencias, 23.631 jornadas, 48 verificaciones contra IDW canónico.
  MAE diario 1,091417 → 1,091530 mm con reducción de peso; tampoco mejora el
  descarte. **Mantener IDW operativo actual**: el piloto no acredita una mejora.
  [Reglas, resultados y limitaciones](../local-apps/rainfall-qc/README.md).
- Rovelló/Els Ports: artefacto del precálculo 258, 26/09, IFF 78; modelo LR–V4
  del 24/09, anterior a la reparación. Reproducción algebraica de sus
  coeficientes: asociaciones con baja humedad/pocos días lluviosos compensan
  penalizaciones hídricas. Sus 33 entradas no incluyen agua disponible del suelo.
  Sin evidencia local de área; evidencia global 5/5 recomendaciones acertadas
  entre 19 observaciones (9 positivas), límite inferior Wilson 95 % 56,55 %.
  Seguimiento del 27/09: lote nuevo y revisión 261 seleccionan RF–V3, IFF 37
  constante. Sólo cambia el horizonte entre sus 27 entradas; ninguno de los
  200 árboles cambia de hoja en Els Ports. En Vallcebre cambia cuatro árboles,
  IFF 76,41→75,96, todos redondean a 76. Agua del suelo observada al corte, no
  proyectada diariamente. No confundir RF con LR ni atribuir toda la mejora a
  la reparación meteorológica: también cambian muestras, selección y fecha.
  [Informe y evidencia](reports/rovello-els-ports-dry-prediction-2026-09-26.md).

## GBIF y setales: entregado; decisiones que deben conservarse

Las funciones aceptadas por el usuario se publicaron en HA 0.2.324 y están
incluidas en 0.2.325. No son una implementación pendiente de publicar.
[Contrato y uso](../local-apps/gbif/docs/gbif-rainmapper-export-import-design.md),
[validación](reports/gbif-import-local-2026-09-25.md),
[release 0.2.324](reports/release-ha-0.2.324-2026-09-26.md).

- ZIP con citas que cumplen filtros, también fuera del encuadre, y fotos.
  Selector de carpeta origen y archivo destino, nombre editable y ZIP existente.
  Duplicados GBIF al exportar: Ignorar/Reemplazar; al importar: Mantener/Reemplazar.
- Importadas como Borrador/Revisar antes de usar; observador/origen GBIF,
  abundancia Normal y calidad provisional 0,75. Reemplazar conserva ID Rainmapper,
  sustituye datos/fotos y devuelve a revisión; restaura si estaba archivada.
- Incertidumbre original conservada: declarada o 500 m asignados si desconocida;
  existentes sin precisión muestran 0 por compatibilidad, sin migración masiva.
- GIS/DEM y microárea contenedora recuperados al importar, con progreso por cita;
  varios contenedores: centro más cercano. Cartografía separada de datos de campo.
- Alta automática opcional de setales, desmarcada inicialmente: examina todo el
  lote reutilizando altas previas. Radios área 500 m / microárea 495 m; ampliar
  el área por unión geométrica para mantener margen de 5 m, también si era manual.
  Sin recortar/fusionar ni reactivar zonas archivadas. Empates resueltos por ID.
- Origen `provenance.creation_source` manual/GBIF/futuro. Ampliar área manual
  conserva su origen. Nombres editables no cambian IDs ni asociaciones.
  Nombre del área usa municipio del snapshot si existe, con sufijo GBIF/ID;
  topónimo más cercano sigue pendiente de fuente verificada.
- SoilGrids por microárea, cobertura local (`ensure_missing=False`); si falta,
  queda pendiente. Importar no amplía descargas ni lanza modelos. Plan sellado,
  control de concurrencia y diario de guardado según contrato; no deshacer cambios ajenos.
- Lotes: hasta 100 citas / 120 MiB de fotos; ZIP máximo 128 MiB.
- Setales: búsqueda por coordenadas/Photon, navegación desde observación con
  marcador y detalle; círculos como polígonos editables. Sustituir/Añadir círculo,
  clic centro/borde y guardado explícito. Usuario acepta su funcionamiento.
- Pendientes: mapa cartográfico del plan (aplazado), nombres por topónimo y
  auditoría de observaciones que no encajan en sus zonas. No ejecutar por rutina.

## Decisiones vigentes que afectan al siguiente paso

**Consenso de recomendaciones (incluido desde 0.2.318):** Workers y trabajos →
Modelos de predicción → Desactivado / Solo comparar / Aplicar
(`legacy` / `shadow` / `prudent`). En Ou de reig, Edulis y Pinícola, cuando hay
recomendación favorable e IFF ≥60, consulta exactamente dos familias alternativas
fijas de la semana, posteriores al ganador en el ranking sellado. Aplicar exige
las dos disponibles y ≥60; si discrepan o faltan, se abstiene. Conserva ganador e
IFF, no suaviza diferencias espaciales. Aereus/deliciosus quedan fuera de este veto.
Ausencia de alternativas no es desacuerdo. Descartes por datos cuentan sólo
familias evaluadas; no las que el mapa no ejecutó. Conclusión verde/roja, ámbar si
faltan alternativas, debajo de temporada; un Detalle con perfiles visibles.

El usuario exige evitar más errores que aciertos perdidos. Rechazó la regla
global que evitaba 130 errores pero perdía 156 aciertos. La retrospectiva selectiva
39/10 motivó esta dirección, **no acredita ese balance futuro ni el selector
completo por área**: ámbito elegido tras ver datos, observaciones reutilizadas por
plazo y familias correlacionadas. Mantener modo reversible y medir con nuevas
observaciones/GBIF revisado antes de ampliar especies o activar por rutina.

**Querigut/rovelló:** el informe del lote real de septiembre reprodujo 99→90,
no encontró consenso general sobre esos IFF y detectó exclusiones por huecos de
lluvia/estado hídrico e imputación en V5/V6. Suelo/hosts GIS ausentes y estado
hídrico son problemas distintos; las microáreas inspeccionadas tenían retención
SoilGrids. No atribuirlo todo a Francia, ni tratar 99 como 99% de acierto.
El filtro de consenso no cubre deliciosus. Informe opcional:
`docs/reports/querigut-predictor-2026-09-21.md`; conclusiones de ese snapshot,
no prueba de los modelos actuales después de otros entrenamientos.

**Memoria (corregida desde 0.2.318):** verificación secuencial de respuestas y
recepción de artefacto por bloques, conservando SHA, límites y activación atómica.
Benchmark histórico con la misma copia en Mac: pico 825→304 MiB, 16,00→15,66 s;
no es medida del servidor RPi. Falta medir en real y explicar consumo inicial y
retención/cachés. No está demostrada una fuga. La percepción de lentitud tampoco
se aisló en un A/B con mismos datos/modelos. Ver informe de memoria si se retoma.

**Datos de lluvia:** copiar `Data/` no actualiza el GeoJSON de `PublicData/`.
La ficha de estación puede seguir mostrando el mapa generado antes; la predicción
puntual lee su histórico meteorológico por otro camino. Comprobar generación,
configuración y modelos antes de afirmar paridad entre HA real y local.

**Ciencia conservada:** SMI común regulado + PM + una capa 0–30 cm con IDW;
modelo simple sólo visual. Host/suelo GIS filtran compatibilidad en el mapa;
no inferir entradas entrenadas por el nombre del modelo: mirar sus columnas.
No cambiar IDW, suspensiones ni modelo operativo por intuición o por acuerdo visual.

## Publicado en 0.2.326 · ficha de observaciones del mapa (27/09)

Añadidas coordenadas latitud/longitud (seis decimales) e incertidumbre en metros
al detalle del visor de observaciones. **Petición expresa del usuario: mostrar
0 como «0 m», sin aclaraciones ni tooltip de compatibilidad.** La procedencia
se conserva internamente. Valores no nulos pueden indicar declarada/asignada/manual;
se usa `precision_origin` vigente, sin confundir el origen GBIF con una edición.
Sin migración de datos ni cambio de modelos. Etiquetas es/ca/en.

Etiqueta abreviada a **Incertidumbre / Incertesa / Uncertainty**. Si hay foto local,
la ficha muestra una miniatura de la primera foto asociada; al pulsarla ocupa
la misma ficha con «Volver a la observación». Altura ajustada al espacio del mapa.
Lectura autenticada con permiso de observaciones, por ID y revisión, sin exponer
rutas ni abrir URLs externas. Vistas JPEG en memoria (192/960 px), sin alterar
originales ni crear ficheros; cargas canceladas y URLs temporales liberadas al cerrar.

33 pruebas de API/observaciones correctas, incluida denegación de acceso a fotos,
rutas fuera del directorio, revisión antigua, límites y ausencia de archivo.
Batería `prediction_map_browser_check.mjs` correcta: miniatura, ampliación, vuelta
a datos y caso sin foto. Captura ampliada inspeccionada. HA local reconstruida y
recreada desde este código, hashes de módulo, adaptador, JS, CSS y etiquetas
idénticos al worktree; HTTP 200. Foto real local comprobada en el contenedor:
miniatura 144×192 / 9.940 bytes, ampliación 720×960 / 137.733 bytes.
Worker no reconstruido/reiniciado para esta UI. Usuario validó local y autorizó
publicar: imagen 0.2.326 disponible; instalación real pendiente. Smoke completo
correcto (1.829 pruebas, 52 omitidas). Código y documentación incluidos en el
commit de release; JSON privados de observaciones excluidos.

## Trabajo documental/Git y límites de actuación

- Base anterior a esta release: `63a3818`; release HA anterior `120e087`.
  Corrección worker, pruebas, laboratorio IDW y documentación posterior
  se cierran en el único commit de release 0.2.326.
- Privados preexistentes: `mushroom-data/mushroom_observations.json` modificado y
  `mushroom_observations.json` de la raíz sin seguimiento. **No incluirlos en Git,
  revertirlos ni usarlos para sobrescribir datos de HA.**
- Usar `docker-data` para nuevas copias/experimentos; el usuario tiene copia de
  `share/rainmapper` y rechaza respaldos adicionales en HA real. No limpiar datos,
  volúmenes o históricos ajenos. Conservar coordinadores, identidad y suspensiones.
- Montajes usados en la investigación reciente: `/Volumes/share` y
  `/Volumes/media-1`. Revalidar origen/montaje antes de acceder: los nombres
  históricos `/Volumes/share-1` o `/Volumes/media` no acreditan el destino actual.
- Instalar/parar/arrancar HA corresponde al usuario. Sin SSH salvo petición
  expresa; no usar Tailscale ni montar SMB por Tailscale. Conservar, sin sustituir,
  la URL Tailscale persistida que utiliza el worker.
- No lanzar entrenamiento, precálculo ni runner. No reiniciar un worker ocupado.
  Una revisión documental no autoriza desplegar ni publicar. Mantener updates
  breves cada minuto y responder al usuario sin abandonar la tarea activa.
