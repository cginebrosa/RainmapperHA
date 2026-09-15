# Active Context

Cierre del **13/09/2026**. Esta es la ventana operativa, no un histórico.
Basta leer `codex-start-here.md` y este documento para retomar; `todo.md` amplía
prioridades. Los anexos se consultan al trabajar en su componente, no como
lectura inicial obligatoria.

## Objetivo y siguiente acción

Continuar el **Mapa de predicción**, complementario al Predictor actual.
**La preview ya muestra terreno/meteorología reales y candidatas ecológicas;
no calcula todavía probabilidades reales.** El filtro mantiene
los hospedadores específicos cuando la ficha los requiere; por decisión posterior
del usuario admite fichas de prado/ribera por hábitat revisado aunque falten árboles.
Sin hábitat ni hospedadores utilizables hay abstención. UI única «Terreno».

**Siguiente acción concreta:** agrupación derivada Rovelló, preservando fichas,
IDs y observaciones → integrar motor compartido en servidor local/HA → validar
cálculo completo → comparar con worker.

**Disponibilidad de predicción, aclaración del usuario 13/09:** el catálogo de
compatibles puede contener especies sin modelo por falta de observaciones. Su captura
del Predictor muestra nueve etiquetas: Ou de reig, Aereus, Edulis, Pinícola,
Rossinyol, Llanega negra, Marçot, Rovelló y Múrgola negra. Es una instantánea aportada,
no una lista fija que deba codificarse. Al conectar el motor, cruzar compatibilidad
con disponibilidad real y aplicabilidad de los modelos, conservando abstención.
`mushroom_predictor_ui.trained_species_ids` (línea 360 comprobada) lee respuesta
preparada o modelos instalados cruzados con informe no omitido; sin informe devuelve
IDs instalados. No atribuir toda indisponibilidad a pocas observaciones sin motivo
registrado. Decisión de UI del usuario: **una única lista de compatibles**, primero las que
tienen probabilidad calculada, **de mayor a menor para el día seleccionado**,
y al final las que carecen de cálculo, con el texto
«Sin probabilidad calculada». Motivo adicional solo si está acreditado; no asignar
0 % ni separarlas en otro desplegable. Pendiente de conectar al estado real del motor.
Rovelló no puede prestar el modelo de un miembro a otro que carezca de modelo.

**pH descargado e integrado en preview, 13/09/2026:** por decisión del usuario,
selección con la **media OpenLandMap**, conservando SoilGrids para comparar y para
retención de agua. Los 21 rangos provisionales siguen aplicados en perfiles locales,
sin cambios de hospedadores/altitudes ni ajuste de rangos a estos puntos.
[Tabla y política](mushrooms/prediction-map-species-ph-proposal-es.md).

Datos en `mushroom-map-GIS/openlandmap-ph/spain-v20250204/`: nueve GeoTIFF,
376.526.984 bytes (368 MiB), `manifest.json` y `acquisition.json` completos.
Recortes de península/Baleares, Canarias y territorios norteafricanos; comprobados
nueve puntos, sin afirmar ausencia de huecos en toda España. **No repetir descarga.**
Media 30 m, intervalo Q16–Q84 (68 %) a 120 m, profundidad 0–30 cm, periodo 2020–2022.
Lector offline `mushroom_map_ph.py`: cuatro datasets abiertos como máximo, stat de
integridad por lectura, búsqueda acotada del píxel válido más cercano cuando falta
la media. Radio **1.000 m editable en el manifiesto**, distancia visible; sin dato
cercano se abstiene, sin sustituirlo silenciosamente por SoilGrids.

Preview reiniciada conservando argumentos y puerto 65517, añadiendo
`--openlandmap-ph mushroom-map-GIS/openlandmap-ph/spain-v20250204/manifest.json`
y `--ecology-ph-source openlandmap`. Cabecera «pH estimado» sin profundidad;
Terreno muestra estimado/mínimo/máximo de ambas fuentes, profundidad e incertidumbre.
Merlès `42.01347,1.97098`: **6,7 [5,6–7,9]**; Olvan `42.06220,1.93614`:
**6,6 [5,7–7,6]**. SoilGrids sigue devolviendo 7,6 en ambos puntos.
Aereus y caesarea compatibles; **edulis y pinophilus también**, debido a las
ventanas actuales de hospedadores/altitud/pH. Sigue pendiente su revisión ecológica;
no presentar la nueva fuente como validada por coincidir con Sporas o estos setales.

Validación de este incremento: 39 pruebas de ecología/consultas/contrato + 21 de
lectores GDAL, prueba de navegador escritorio/móvil y ruta meteorológica correctas;
API real de preview comprobada en ambos puntos. Payload adicional de pH en los nueve
puntos: 372–380 bytes JSON. Perfiles, catálogo, mappings y observaciones conservan
sus huellas previas; sin runners, entrenamiento, precálculo, reconstrucción ni
publicación HA. [Registro verificable](reports/prediction-map-openlandmap-ph-implementation-2026-09-13.json).

Mappings locales ICGC y pruebas del filtro completados en este incremento:
787 códigos exactos (4 cubiertas, 783 geología) comparten 77 combinaciones editables
en `mushroom_gis_mappings.json`; cinco filas MVC50 originales conservadas.
272 códigos geológicos y 37 cubiertas quedan explícitamente sin equivalencia
utilizable. La revisión local conserva todas las descripciones y decisiones;
no forzar las pendientes ni repetirla. No hay equivalencias fijas en Python.
Mezclas conservan varios materiales y la unión sin duplicados de tendencias de
suelo; nunca generan pH ni vetos. No deducir árboles de una cubierta genérica.
No adelantar pruebas de rendimiento del motor usando solo tiempos del lector geográfico.

## Decisiones que debe conservar la implementación

- Un solo motor Python, el ya existente, para HA y worker. «Local» = servidor;
  no inferencia científica en navegador. El IDW visual del navegador es otro cálculo.
- Punto con sus propias entradas, incluso dentro de un área conocida. Misma
  selección semanal del Predictor, pero porcentajes pueden diferir si cambian
  entradas/evidencia. Igualdad exigible con entradas, modelos y política iguales.
- Hasta siete días: continuidad `weekly_lag_event_v2`, familia `lag_event` común
  h1–h7 y corte común, veto diario sin cambiar familia; conservar el fallback
  diario existente cuando no haya familia común. No inventar otro selector.
- Un MapLibre reutilizado, dos rutas: actual meteorológica intacta y nueva
  `/protected/prediction-map/index.html`. Diana/dardo bajo IDW. Clic/hover de
  estación conservan popup meteorológico; clic fuera consulta el punto con
  modal cancelable «Calculando predicción» y resultado en popup anclado.
- Municipio/coordenadas, altitud/pH y arbolado en cabecera (árboles a ancho
  completo). Detalle de terreno/geología desplegable. Máximo 60 días observados
  en popup, aunque el motor use 90/365. Sin previsión meteorológica en UI ahora;
  viento opcional observado en estación identificada, no interpolado al punto.
- Preview sin autenticación real; usuario ficticio no se escribe en `devices.json`.
  Ajustes de prueba en JSON temporal aislado. Futuro selector local/worker debe
  guardarse con los demás ajustes del dispositivo, no en un almacén alternativo.
- Fichas: ventanas amplias de meses/hosts/hábitats/altitud/pH. Unión de asociaciones
  como alternativas. Meses principales y secundarios admiten compatibilidad;
  orientación no es requisito. Desconocidos/placeholders no se vuelven ceros.
- Hospedadores: ficha **pino negro** acepta GIS **pino negro o pinos**, no **pino
  rojo**. Ficha **pinos** acepta cualquier especie del género. Aplicar la
  jerarquía explícita igual para todos: padre de género ↔ descendiente sí;
  hermanos específicos o géneros distintos por familia, no. Basta una alternativa.
- Especie que necesita host sin coincidencia identificada: no incluirla.
  **Decisión posterior del usuario:** prado/ribera revisado puede admitir las
  fichas no ectomicorrícicas que acepten ese hábitat, aunque no haya árboles.
  Reemplaza la abstención global por falta de árboles. Sin hábitat ni hosts:
  `terrain_context_missing`, nunca ausencia física demostrada ni 0 %.
- UI bajo un único concepto **Terreno**, incluyendo altitud, pH y etiquetas de
  árboles/hábitat. La separación de IDs es interna para no sustituir pinos por
  prados. Materiales y posibles suelos múltiples en el detalle de Terreno.
- Vocabulario en catálogo local; equivalencias editables en mappings locales.
  Prohibido codificar correspondencias científicas o listas de especies en Python.
- Mantener salmonicolor/quieticolor unido. Rovelló: agrupar en datos derivados
  deliciosus, sanguifluus, vinosus y salmonicolor/quieticolor, conservando IDs y
  observaciones originales. Una curva del grupo si encaja una ficha completa;
  no fusionar observaciones, sumar curvas ni renombrar solo el modelo deliciosus.
- Huecos de arbolado/SoilGrids aceptados; vegetación/ecología/geología francesa
  pendiente. No ampliar cobertura como requisito para continuar. Cartografía
  pesada en volumen persistente portable del worker, no en su imagen ni reconstruida
  desde HA. AWS/servidor doméstico son ideas futuras, sin decisión de infraestructura.

## Código y datos implementados

| Componente | Estado y entrada al código |
|---|---|
| Catálogo y fichas locales | `docker-data/mushroom-data/`: autoridad editable; 115 hosts y 21 fichas. No sustituir desde `mushroom-data/` del repo. Promoción posterior explícita. |
| pH en fichas | `ecology.ph_min/ph_max`, formulario V0/Enriched → Ecología → Suelos, guardado/importación/validación. **21 pares informados con rangos provisionales aceptados**; procedencia en `metadata.ph_window_review`. |
| Revisión aplicada | 25 relaciones de plantas y 12 de bosque añadidas; meses cambiados en 8 fichas, altitud en 13, nueve óptimos 0–0 pasados a desconocidos. No reejecutar la migración. |
| Mantenimiento | `rainmapper-app/app/mushroom_profiles_ui.py`, `web_server.py`, `rainmapper_core/mushroom_validation.py`, `scripts/validate-mushroom-data.py`, etiquetas ES/CA/EN. |
| Arbolado | `rainmapper_core/mushroom_map_forest.py`: MFE Catalunya, IDs por científico/alias inequívoco del catálogo local. Recarga etiquetas/IDs sin perder caché geométrica. |
| Filtro | `rainmapper_core/mushroom_map_ecology.py`: `EcologyReader`, `broad_species_windows_v2`, instantánea de tres JSON por consulta semanal. |
| Lectores residentes | `scripts/prediction-map-local-geography.py`, `prediction-map-local-weather.py`; `mushroom_map_terrain.py`, `mushroom_map_land.py`, `mushroom_map_municipalities.py`, `mushroom_map_weather.py` en core. |
| Ejecutor y transporte | `mushroom_map_execution.PointExecutor`, `mushroom_map_queries.QueryBroker`, `mushroom_map_worker.py` preparados; no activos en el worker instalado. |
| UI del filtro | `rainmapper_core/viewers/prediction-map/prediction-mode.js`: lista solo candidatas del día, «Predicción pendiente», sin curvas/porcentajes demo al recibir `ecology`. |
| Motor preparado, sin conectar | `mushroom_map_prediction.resolve_species_week` reutiliza selección existente. Adaptadores de retención/preparación hídrica 90/365 en lectores; índice candidato `mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite` no sustituye aún al de preview. |

El filtro considera meses, altitud inclusiva y hosts. No ectomicorrícicas necesitan
hábitat de mapping exacto revisado; ya se prueban con las fichas locales prado,
bosque caducifolio y ribera, incluso sin árboles identificados. Suelo/litología
aportan preferencias, no vetos nuevos. pH:
media OpenLandMap dentro de los límites inclusivos admite la dimensión; fuera
queda excluida provisionalmente y media ausente es desconocida. La incertidumbre
se muestra, pero no interviene en este filtro por decisión del usuario. El modo
anterior SoilGrids por intervalos sigue disponible explícitamente; no es fallback.

Reglas locales: 355.327 bytes entre perfiles/catálogo/mappings. Stat por consulta;
leer/hashear solo JSON pequeños cuando cambian. Límites: 32 fichas, 2 MiB/JSON,
512 reglas y 2.048 referencias de código, comprobadas antes de crear el índice.
Los códigos apuntan a 77 reglas compartidas, sin copiar listas por código/día.
La revisión detallada (767.220 bytes) queda fuera del payload operativo.
ForestReader adjunta la huella del catálogo leído; EcologyReader exige la misma
instantánea o devuelve `unavailable/host_catalog_mismatch`, sin reglas obsoletas.
No PDF/web/LLM, hashes de capas completas ni proceso por capa en cada clic.

## Estado operativo y validación

- Rama `inicial`, HEAD comprobado `fce06dd24507a17071755763cb24fb7da1a4ce85`.
  Trabajo posterior sin commit; muchos archivos nuevos sin seguimiento.
  `mushroom-data/mushroom_observations.json` tiene cambios previos del usuario:
  no editar, restaurar ni incluir ciegamente. No hubo commit/push en este cierre.
- Preview `http://127.0.0.1:65517/protected/prediction-map/index.html`: HTTP 200
  relanzada tras comprobar libre el puerto y ausente el PID histórico 84535.
  Sesión actual de herramienta 43057 (temporal); POST de consulta comprobado con
  política v2 y nueve candidatas en Olvan. Revalidar el proceso antes de operar.
  `tests/prediction_map_browser_check.mjs --preview --port 65517`.
- Preview usa GDAL `/opt/homebrew/bin/python3`, meteorología `.venv/bin/python`,
  `docker-data/Data`, `stations.txt`, `PublicData`; catálogo/perfiles/mappings
  bajo `docker-data/mushroom-data/`. Rutas GIS en `mushroom-map-GIS/` y `mushroom-GIS/`.
  Flags del filtro: `--profiles`, `--ecology-catalogs`, `--gis-mappings`, todos
  explícitos. Comando completo en el relevo técnico, solo si hace falta reiniciar.
- En el relevo anterior, `docker ps` mostró: HA local `rainmapperha:local-ha-ui`, puerto local 8101;
  worker `rainmapper-worker:1.1.1`, healthy, puerto local 8110. No acredita sus jobs
  ni paridad de código. HA local recibió el bloque anterior de mantenimiento pH;
  **el filtro último solo está activado en preview**, sin reconstruir contenedores.
- HA real `0.2.303`: versión confirmada anteriormente por el usuario, no
  revalidada en contenedor en este incremento. Share real: reparación posterior
  autorizada del catálogo de Barcelona, detallada abajo; sin publicación de código.
- Bloque fichas/pH: 26 + 22 pruebas, 42 editores renderizados en HA local y HTTP
  200; cuatro huellas efectivas verificadas en aquella entrega. No equivale a
  validar el filtro nuevo dentro de esa imagen.
- Filtro anterior (evidencia histórica): 14 pruebas ecológicas + 10 forestales con GDAL + 6 broker +
  12 mapa = 42. Chrome real: candidatas por día, ausencia/fallo sin ejemplos,
  móvil, estaciones y ruta meteorológica. No repetir por documentación sola.
- Incremento mappings: **74 pruebas Python** (51 filtro/validador/broker/mapa,
  18 forestal/land con GDAL, 5 opt-in sobre JSON locales) y Chrome correctos.
  Navegador: Terreno unificado, prado sin árboles, suelos múltiples, abstención,
  fechas, móvil, estaciones y ruta meteorológica. POST real de preview correcto.
- Puntos revalidados: Avià `42.06511,1.81822`, cubierta 111 (cultivos herbáceos),
  cero candidatas; Olvan `42.06397,1.93668`, cubierta 222, nueve; Ger
  `42.46291,1.82695`, cuatro; La Pera `42.0641,1.9387`, cubierta 226, nueve.
  Olvan añade Lepista/Macrolepiota por hábitat caducifolio. Son compatibilidades,
  no resultados del motor. Pinophilus en Olvan encaja por su ficha con Quercus.
- Medidas históricas M1 del filtro anterior: 582 ms primera, 33–73 ms siguientes, 2,3 ms
  repetida; 7,6–9,9 kB geográficos. No tiempos del motor ni benchmark RPi4.

## Riesgos y límites para continuar

1. Contrato aún `prediction_map_point_v1`, `data_mode=simulation`:
   `QueryBroker.finish()` exige los ejemplos exactos en `species`. El payload
   `ecology` los oculta en UI, no los convierte en predicción. Al integrar motor,
   evolucionar conjuntamente contrato, broker, ejecutor y validación UI.
2. Mappings agrupados nuevos son consumidos por el mapa y validados por el
   validador de datos. Consumidores GIS/editores legacy aún no expanden
   `exact_value_mapping_groups`; mantenimiento del bloque nuevo en JSON local.
   No promover a repo/HA ni asumir integración general. Fuentes/ediciones exactas
   y coherencia de catálogo forestal/ecológico ya comprobadas con pruebas.
3. Modelo disponible no acredita aplicabilidad a un punto nuevo. Conectar entradas,
   evidencia y materialización reales; preservar continuidad/fallback semanal.
4. pH provisional informado en las 21 fichas; no inferirlo de roca/textura. Ventanas amplias
   son política revisable, no límites biológicos universales demostrados.
5. Mapas/índices de `mushroom-map-GIS/` están excluidos de Git/Docker y solo en este
   Mac; clonar/exportar imagen no los traslada. Portabilidad sigue pendiente.
6. La falta de árboles permite candidatas solo si la ficha admite el hábitat
   revisado disponible. Francia sin vegetación/hábitat sigue absteniéndose.
   Que el municipio sea opcional no elimina requisitos ecológicos del filtro.
7. Caso aportado por el usuario, pendiente de revisión ecológica: Santa Maria de
   Merlès `42.01347,1.97050`. Consulta reproducida el 13/09: edulis y pinophilus
   compatibles por Quercus secundario genérico (roble pubescente y encina),
   623,2 m frente a mínimo 600 y septiembre. En aquella reproducción aún no había
   límites pH en fichas (ya aplicados posteriormente); SoilGrids
   central 7,6, intervalo 5,0–8,3 a 0–5 cm. Suelo/litología son preferencias.
   El usuario conoce el setal y cuestiona ambas candidatas: revisar la suficiencia
   del contexto y las relaciones secundarias antes de interpretar compatibilidad
   como adecuación local. No se han cambiado fichas ni inventado umbrales de pH.
   [Reproducción](reports/prediction-map-merles-ecology-review-2026-09-13.json).
   Auditoría posterior solicitada: **las actualizaciones de ventanas sí están
   aplicadas**, 143 campos coinciden con el registro y hash idéntico en HA local.
   Suelo/litología de las fichas no cambiaron; esa auditoría precedió a la
   aplicación posterior de los 21 rangos de pH y la integración OpenLandMap.
   No confundir mappings GIS completados con revisión de afinidades por especie.
   Edulis y pinophilus pasaron de mínimo 1.000 a 600 m y añadieron Quercus genérico.
   [Aplicado frente a pendiente](reports/prediction-map-species-application-audit-2026-09-13.md).

## Restricciones y referencias de detalle

No lanzar runners, reconstrucción, entrenamiento o precálculo ni publicar HA.
No borrar caché antigua, backups, datos u observaciones ni cambiar URLs de worker.
Permisos/afinidades y meteorología actual se preservan. RPi4 compartida: límites
estrictos de RAM/CPU/IO. Comunicar progreso al menos cada minuto y responder
preguntas sin abandonar la tarea. No activar autenticación real en preview.

La revisión y los backups `.keep.json` ya aplicados se conservan. No volver a
aplicar scripts temporales de migración. No repetir descargas/auditoría SoilGrids:
54 retenciones + nueve pH terminadas, huecos aceptados. Migración general de
áreas/microáreas, exportación de volúmenes y Francia quedan detrás del mapa.

- Diseño central: [especificación](mushrooms/prediction-map-specification-es.md).
- Valores/decisiones de fichas: [revisión](mushrooms/prediction-map-species-literature-review-es.md).
- Backups/cambios locales: [informe de ventanas](reports/prediction-map-species-windows-2026-09-13.json).
- Mappings/backup/pruebas actuales: [informe](reports/prediction-map-mappings-2026-09-13.json).
  Backup: `docker-data/mushroom-data/backups/mushroom_gis_mappings.20260913T155605474176Z.keep.json`.
  Revisión: `docker-data/mushroom-data/gis-mapping-reviews/icgc-local-2026-09-13.json`.
- Incidencia independiente del runner: Barcelona `ESCAT0800000008011B`
  **corregida por petición expresa en los catálogos local y HA real** a
  `41.38,2.16,14m`. Catálogos nuevos, una sola fila modificada; particiones,
  receipts y Erinya `ESCAT2500000025515B` conservados. Backups pequeños en
  `Data/weather-history-repairs/20260913T161732073252Z` (local) y
  `20260913T161812132344Z` (real). No se ejecutó runner ni archivo de pending.
  Erinya sigue con la ubicación errónea que publica la fuente; usuario pide esperar.
- Cambio de código meteorológico acotado, **sin desplegar en HA**: decisión final
  del usuario acepta saltos cuyo destino esté dentro de España aproximada,
  incluidas Baleares/Canarias, aunque el origen también esté dentro. Sustituye
  la propuesta inicial de aceptar solo fuera→dentro. Regiones en
  `rainmapper_core/weather_coordinate_policy.json`, override editable
  `Data/weather_coordinate_policy.json`; metadata antigua no usa la excepción.
  36 pruebas writer/dataset correctas. Reparador manual con plan fijado a generación,
  backup, validación y publicación atómica; sin reescribir mediciones.
  [Registros, verificación y rutas](reports/weather-coordinate-conflict-2026-09-13.json).
- Filtro/datos/pruebas anteriores: [informe de compatibilidad](reports/prediction-map-ecology-2026-09-13.json).
- Comando y relevo técnico: [relevo 13/09](reports/prediction-map-handoff-before-compaction-2026-09-13.md).
- Evolución anterior archivada: [snapshot íntegro](reports/session-context-before-close-2026-09-13.md).

No hace falta leer los informes al arrancar; el siguiente trabajo está definido arriba.
