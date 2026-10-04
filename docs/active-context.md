# Contexto activo — actualización 04/10/2026

## Release actual: HA 0.2.333 publicada; pendiente instalación del usuario

El usuario autorizó publicar con «publicamos version de HA» después de la
validación local de la medición por recorridos y su convivencia con las consultas.
GHCR verificado: `0.2.333` y `latest`, mismo digest
`sha256:3980114db78a60a0d44a720d51773af7f311607567e20f43ad9455fb18630832`,
con manifests `linux/amd64` y `linux/arm64`.

- Medición A→B→C… en 2D/3D, línea provisional, vértices arrastrables, Deshacer y
  Nueva. Pulsar el último punto termina/reanuda. Icono después de norte y antes
  de Créditos; sin permiso específico.
- Distancia horizontal, relieve aproximado y desniveles acumulados; cálculo
  Mapzen/Terrarium acotado e independiente de la exageración visual.
- Panel compacto ES/CA/EN, ayuda plegada y acciones en una fila; móvil comprobado
  a 320, 360 y 390 px. Un recorrido terminado conserva sus resultados y permite
  consultar predicciones, estaciones e información del terreno.
- HA local reconstruida/recreada y ocho huellas revalidadas contra el código
  aceptado. Navegador completo correcto y smoke definitivo: 1.911 pruebas,
  55 omitidas. Después sólo bump/cache-busters y documentación.
- Una publicación supervisada, salida 0 y GHCR verificado. Limpiezas Docker ya
  autorizadas: retirada de etiqueta local 0.2.332 y 5,796 GB de caché recuperados.
  Fuentes, observaciones privadas y volúmenes conservados.

[Informe y evidencias](reports/release-ha-0.2.333-2026-10-04.md).
Siguiente paso: el usuario instala y prueba 0.2.333 en HA real. Última instalación
confirmada: 0.2.332. Codex no ha instalado ni reiniciado HA real ni operado sobre
el worker/coordinador. No repetir publicación, entrenamiento ni precálculo.
La discusión de utilidad para aereus/caesarea sigue pendiente; ningún k aprobado.

## Release anterior: HA 0.2.332 instalada y funcionando, confirmada por el usuario

El usuario confirmó que la capa de áreas y microáreas funciona en HA local y
autorizó publicar con «pues publicamos version de HA». GHCR verificado el 04/10:
`0.2.332` y `latest`, mismo digest
`sha256:6e48babc0868d84a76509bb95cd0418ff778d8926f59df8f7e74b623703717b2`,
con manifests `linux/amd64` y `linux/arm64`.

Botón debajo de Observaciones; capa independiente y compatible con las demás.
Comparte `can_use_observations_map` en interfaz y API; sólo carga geometrías y
nombres al activarse. HA local reconstruida/recreada y aceptada; seis huellas
revalidadas antes del bump. 28 pruebas dirigidas, navegador escritorio/móvil y
smoke de release correcto: 1.911 pruebas, 55 omitidas. Después sólo cambiaron
versiones/cache-busters y documentación. Sin operaciones sobre el worker.

El usuario autorizó expresamente las dos limpiezas automáticas de Docker del
script de publicación. Se retiró la etiqueta local HA 0.2.331 y Buildx informó
de 6,486 GB recuperados. Esa autorización no amplía la auditoría de disco ni
permite retirar fuentes, datos privados o carpetas históricas.

[Informe y evidencias](reports/release-ha-0.2.332-2026-10-04.md).
El usuario confirmó el 04/10 «instalada y funcionando» tras publicar 0.2.332.
Instalación y funcionamiento en HA real confirmados por el usuario; Codex no ha
instalado ni reiniciado HA real. Release cerrada; no repetir publicación ni
lanzar trabajos operativos.
La discusión científica sigue pendiente, sin nueva métrica aprobada.

## Contexto anterior (03/10/2026; histórico)

Leer [codex-start-here.md](codex-start-here.md) y este documento basta para
continuar. [todo.md](todo.md) amplía pendientes; ningún pendiente autoriza por sí
solo su ejecución. No hay una publicación ni un trabajo operativo que Codex deba
lanzar al reabrir.

## Release anterior: HA 0.2.331 publicada; pendiente instalación del usuario

El usuario confirmó «ya funciona» en local y autorizó publicar con «adelante».
Publicación completada el 03/10: `0.2.331` y `latest`, mismo digest
`sha256:be84ceaedf2289f73157b39661b7d4480c69c23de276d4d61a47dc5685dde90b`,
con manifests `linux/amd64` y `linux/arm64`. No instalar ni reiniciar HA real
por cuenta de Codex. Última versión real confirmada por el usuario: **0.2.330**;
no dar 0.2.331 por instalada hasta confirmación. No repetir publicación.

Incluye controles de círculos ES/CA/EN según idioma del dispositivo, edición
por centro/radio y encuadre visible. Reconoce anillos TerraDraw y WGS84/AEQD
GBIF; admite sus 16 decimales sin redondear el original al abrir. Se corrigió
el rechazo `Feature has invalid coordinates` detectado por el usuario en
Riudarenes. Navegador: ampliar/reducir/mover, guardar/reabrir, no-op exacto,
añadir/sustituir/descartar, tres idiomas, y datos locales intactos tras descartar.

También registra los cambios de organización geográfica ya validados en local
(y herramientas WU/GBIF). No migra carpetas ni datos en HA. Conserva los
`-todelete`; su retirada y los recorridos funcionales pendientes siguen separados.

Smoke de release sobre código definitivo: **1.859 pruebas / 55 omitidas**,
correcto; incluye regresión JS independiente con anillo sintético generado por
GDAL. Paridad revalidada antes del bump: nueve archivos afectados de HA local
y cuatro módulos compartidos del worker iguales al worktree. Las reconstrucciones
y pruebas locales precedentes seguían vigentes; sin nuevo código ejecutable
entre la aceptación, el smoke y la publicación, salvo bump/cache-busters mecánicos.
No se reinició el worker ni se lanzaron trabajos operativos.

[Informe de release y evidencias](reports/release-ha-0.2.331-2026-10-03.md).
Siguiente paso: el usuario instala 0.2.331 y comprueba la edición en HA real.

## Tarea actual: organización geográfica local

Autorizada el 28/09, implementada y validada **sólo en Mac, HA local y worker**.
Código incluido en 0.2.331; pendientes recorridos funcionales restantes y
aceptación para retirar antiguos. HA real ya usaba la raíz correcta.
[Plan, incidencias, evidencia y retirada de antiguos](mushrooms/geography-local-organization-plan-es.md).

El usuario confirmó el 03/10 la edición circular en local. Siguen sin
confirmación completa la asignación de observaciones, recuperación geográfica
en setales e importación GBIF; las comprobaciones técnicas y el registro
sintético GBIF no sustituyen esos recorridos. Conservar
ambos `-todelete` hasta completar la revisión funcional y acordar su retirada.
No lanzar entrenamientos ni precálculos para suplir estas pruebas.

- Operativa completa en `docker-media/rainmapper/geography/`; archivos y contratos
  activos conservados. Fuentes/expansión/preparaciones en `geography-sources/`.
- Raíces anteriores renombradas `mushroom-GIS-todelete/` y
  `mushroom-map-GIS-todelete/`: 5.891 archivos intactos. No borrar hasta la revisión
  y confirmación finales documentadas en el plan; no usarlas como fallback.
- Retirado montaje antiguo de HA local, herramientas WU/GBIF adaptadas.
  Imágenes existentes reconstruidas/recreadas, paridad 147 archivos HA/106 worker,
  URLs e identidad del worker intactas. Sin nuevos jobs operativos.
- Cuatro puntos antes/después idénticos en ambos contenedores; inventario de
  mapeos idéntico. Smoke 1.859 pruebas/55 omitidas y 51 dirigidas después de
  renombrar correctos. WU: apertura municipal; GBIF: un registro sintético.
- La implementación no modificó HA real; después se consultó en lectura el
  precálculo automático mediante los volúmenes montados. No hay release ni
  borrado autorizado por el mero hecho de que la validación local haya pasado.
- Cambios en worktree sin commit/push. Preservar documentación previa y
  observaciones privadas; no incluir estas últimas en un commit.

## Volúmenes montados: aclaración vigente del usuario (28/09)

Está permitido usar los volúmenes que el usuario haya montado, aunque sean por
Tailscale. Codex no debe montarlos por su cuenta. Verificar origen antes de leer;
esta autorización no implica SSH ni cambios/escrituras no solicitados.

Precálculo automático posterior a reorganización comprobado también directamente
en HA real mediante esos volúmenes: revisión **277**, trabajo
`worker_job_BPJgkkhMwTKo` en `complete`, error vacío, mismo artefacto/recibo en
estado deseado, SQLite activo y resultado del trabajo. Activación HA 15:19:22 UTC,
cierre 15:19:39 UTC; 11 min 40 s. Sin cambios remotos ni relanzamientos.
Revisión ampliada del mismo precálculo: 987/987 combinaciones especie–área–día
del trabajo presentes en SQLite, sin faltantes ni extras, del 28/09 al 04/10.
Telemetría: cálculo 578,045 s, publicación HA 99,823 s, transferencia estimada
2,277 s y activación worker 16,779 s. Limpieza registrada como completa a las
15:19:44 UTC. El diagnóstico de lote registra 228 solicitudes ejecutadas para
1.134 solicitudes totales. No se ha investigado aquí la causa del aumento de
duración respecto a otros ciclos ni vuelto a ejecutar el cálculo.

El usuario aplaza la investigación del disco hasta terminar esta revisión.
Mantener pendiente conciliar su bajada de 145–150 a 115,44 GB disponibles; la
auditoría parcial y los límites están en el plan geográfico. No limpiar nada.

Auditoría de geografía de HA real solicitada posteriormente y completada sólo
en lectura: 3.603 archivos, 16,11 GB lógicos; no aparece una gran copia sobrante
retirable directamente. Original MVC50 y originales SoilGrids siguen teniendo
consumidores; importaciones/históricos candidatos a archivar suman 4,02 MB.
[Informe y límites](reports/ha-geography-files-audit-2026-09-28.md).
HA ya usa `/media/rainmapper/geography`; esta organización no requiere migración
ni release HA. El usuario exige hablar antes de borrar: ningún archivo retirado.

## Estado operativo y evidencia

- **HA 0.2.330 instalada en HA real. Entrenamiento y precálculo terminados**,
  confirmados por el usuario al pedir este cierre. No se ha auditado de nuevo ese
  último ciclo real ni se atribuyen a él cifras del ciclo local. Tampoco se deduce
  de esa confirmación que el worker esté libre en una sesión futura.
- Release en commit `14398c0`, rama `inicial` (comprobados con `git log` al cerrar).
  Publicación previamente verificada: tags `0.2.330`/`latest`, amd64 y arm64,
  digest `sha256:e932c63ad4d207c64f8e2a634264a2ca5efe96ac782a73ba96a2f7b57e98b8fb`.
  No repetir build, publicación, instalación ni ciclo local.
- **Geografía real activada durante esta sesión**, ya no pendiente. Recibo
  `docker-data/territorial-validation/ha-register-mvc50.json`: generación
  `local-mvc50-20260928`, huella
  `sha256:e4252f943945412ae4cfc38f81d685778fbdbadb2351f9523620cf9e262ddbea`.
  El puntero está en `/media/rainmapper/geography/CURRENT.json`, junto a
  `generations/`, no dentro de ella.
- Dataset científico activado: 14 referencias, huella
  `sha256:64c6115afbc657246dea6b1aa738e1d4eaf9f7ba42a584ac5a606f9f11550649`.
  Recibo `ha-territorial-activation.json`: `activated=true`, configuración
  1.997 bytes, listado 2.992 bytes, cero bytes GIS copiados o hasheados al activar.
  `territorial-context.json` y `geography-dataset.json` están en la raíz geográfica.
  Esos recibos se han releído en el cierre; acreditan la activación realizada,
  no una inspección nueva de todos los archivos remotos.
- Índice preparado real:
  `/media/rainmapper/geography/mushroom-map-GIS/mvc50/prepared/mvc50-2019-11-v1.sqlite`.
  479.780.864 bytes, 116.468 entidades, SHA
  `7fd80b927641e1a335b72ca50c40a8ca1187f337ea53d6688fb3419bd96c7eb5`.
  Copia verificada al subir; no volver a hashearla sin causa nueva.
- Worker privado: último rebuild local de organización geográfica sobre 1.1.6. Conservar primario
  `http://100.111.77.48:8100` y adicional `http://rainmapper-ha-ui:8100`, identidad
  `worker_1a9a232c20fe2ee2` (M1 Personal). Revalidar reposo y URL persistida antes
  de cualquier operación; no cambiar destinos ni credenciales.
- Aceptación **local previa a release**, no resultados del último ciclo real:
  517 reconstrucciones, 792/792 ajustes, cinco versiones promovidas y precálculo
  activo; smoke 1.854 pruebas / 55 omitidas. Detalle en
  [release 0.2.330](reports/release-ha-0.2.330-preparation-2026-09-28.md).

## GIS: política entregada y caso Campins cerrado

Mapa normal/histórico, recuperación puntual GIS/DEM, muestras de microáreas y
reconstrucción comparten `territorial_sources_v1`, por campo:

| Campo | Primera fuente | Alternativa si no resuelve |
|---|---|---|
| Árboles | MFE25 | MVC50 |
| Bosque | MVC50 `LLVA_niv2t` | Cobertes 2024 |
| Sustrato | MVC50 `LLVA_Subst` | Geología 1:50.000 |
| Litología | Geología 1:50.000 | Ninguna |

Sólo mapeos aceptados; no inferir sustrato del nombre de un bosque ni del pH.
Conservar conflictos explícitos. La evidencia revisada/guardada no se sobrescribe
por consultar el mapa. Una observación antigua puede conservar su recuperación
anterior hasta revisión explícita. Un lector por reconstrucción, snapshots
sellados y caché de assets por contenido; no duplicar GIS por observación/modelo.
[Política y procedimiento](mushrooms/territorial-source-policy-es.md).

**Campins, decisión final del usuario: «pues así se queda».** Respuestas HA real
persistidas y releídas en `docker-data/territorial-validation/campins-*-point.json`:

- `41.72509, 2.47462`: MVC50 `Indiferent`; geología **Qv3**, abanico aluvial con
  gravas/bloques y matriz arenosoarcillosa. Sustrato no determinado.
- `41.72471, 2.47513`: mismo polígono MVC50; geología **POa**, arcosas,
  conglomerados y lutitas, resuelta por el mapping vigente como silícea.
- Ambas consultas tienen capas disponibles, sin huecos ni conflictos reportados.
  La diferencia no acredita pérdida de cobertura: son polígonos geológicos
  distintos. **No añadir Qv3→silíceo ni una regla por vecinos/alcornoques.**
  La leyenda ICGC no determina la composición de Qv3; investigación y fuentes
  en la decisión del 28/09. No queda una corrección pendiente de ese caso.

No borrar el MVC50 original bajo `mushroom-GIS/MVC50mil`: sigue pendiente auditar/
adaptar el inventario del mantenimiento de mapeos. La migración de consumidores
operativos no autoriza su retirada. Expansión España/Francia y reducción de otros
GIS/DEM son futuros, no cobertura ya entregada.

## Funciones y decisiones que no hay que rehacer

- Ficha de observación: coordenadas, altitud, Incertidumbre (0 se muestra **0 m**),
  Bosque, foto ampliable dentro del bocadillo y Cómo llegar a Google Maps; sin
  círculo de incertidumbre. Tabla de observaciones aprovecha la altura disponible.
  Casillas GBIF corregidas; microáreas GBIF nuevas copian notas DEM, sin migración
  automática de microáreas antiguas.
- **Comprobar predicción** abre la predicción histórica completa de siete días,
  con meteorología/SMI/terreno; consulta todas las especies y enmarca la observada.
  Conserva fecha global del mapa. Bloque breve: especie, fecha, abundancia y
  Usada para entrenar: SÍ verde / NO rojo. Estados sin modelo/trazabilidad siguen
  siendo distintos de NO. Trazabilidad por ID y modelo/día en SQLite.
- **Entrenamiento: mantener lo existente**, decisión final del usuario. Evaluación
  previa y ajuste final con todas las filas elegibles. No implementar interruptor,
  reparto persistente nuevo ni benchmark obligatorio. Una comprobación de una
  observación usada por el modelo final no es evaluación independiente; el IFF
  no es porcentaje de acierto. Detalles científicos en `decisions.md`.
- **IDW operativo sin filtro de consenso espacial.** Piloto local no acreditó
  mejora global (MAE 1,091417→1,091530 mm con reducción de peso).
  [Piloto](../local-apps/rainfall-qc/README.md). No confundirlo con el consenso
  de recomendaciones ya disponible (`legacy`/`shadow`/`prudent`): Ou/Edulis/Pinícola,
  dos familias alternativas; deliciosus/aereus fuera del veto. Revalidar modo real
  antes de interpretarlo; no ampliarlo/activarlo automáticamente.
- SMI operativo compartido: regulado + Penman–Monteith + una capa 0–30 cm;
  simple sólo visual. Mantener suspensiones. No cambiar contratos por intuición.

## Reparaciones previas que condicionan cualquier continuación

- Meteocat reparado en real el 26/09: primer día UTC parcial sobrescribía datos.
  Ventana reparada 01/08–25/09/2026, 6.700 filas / 24.034 celdas; otras fuentes
  preservadas. No certifica todo el histórico anterior. Mezcla decimal corregida
  después por runner; no volver a aplicar la candidata antigua
  `tmp/meteocat-repair-20260926/deploy_csv_decimal_fix.py`, perdería datos nuevos.
  [Evidencia](reports/meteocat-partial-days-2026-09-26.md).
- Copiar `Data/` no actualiza el mapa meteorológico de `PublicData/`. Para comparar
  local/real identificar generaciones, fuentes y modelos; no asumir sincronía.
- OOM worker corregido mediante reutilización de entradas V2–V6 por contrato,
  liberándolas tras su último consumidor. No se recortaron los 365 días/SMI.
  Ensayo de carga V6: 3,99→1,71 GiB; no es el pico integral del entrenamiento.
  [Informe](reports/worker-evaluation-memory-2026-09-27.md).
- Rovelló/Els Ports y curvas RF planas ya investigados: entradas hídricas al corte
  y poca sensibilidad de los árboles al horizonte; no imputar por defecto fallo
  de UI. IFF 37 del snapshot anterior no describe el último modelo real.
  [Informe](reports/rovello-els-ports-dry-prediction-2026-09-26.md).

## Próximos bloques, sólo cuando el usuario los priorice

1. **P1 recursos/operación:** estado huérfano después de perder worker y desglose
   del tiempo de entrenamiento/precálculo (crecimiento observado de 9 a 11 min).
   Usar metadatos existentes, no nuevos entrenamientos como diagnóstico.
2. **P2 GIS:** consumidores restantes del MVC50 original, disco/latencia por capa
   y paquetes preparados para expansión. No hay limpieza autorizada.
3. Setales fuera de sus áreas, topónimos GBIF y mapa del plan de importación;
   pendientes funcionales y de ciencia restantes en `todo.md`.

## Archivos para una tarea concreta y límites de cierre

- GIS: `rainmapper_core/mushroom_territorial_context.py`,
  `mushroom_territorial_reader.py`, `mushroom_geography_portable.py`;
  scripts `prepare-mvc50-point-index.py`, `register-mvc50-map-index.py`,
  `prepare-territorial-dataset.py`.
- Mapa/trazabilidad: `rainmapper_core/mushroom_map_model_runtime.py`,
  `mushroom_training_observations.py`, `viewers/prediction-map/`.
- Evidencia local: `docker-data/territorial-validation/`; informes opcionales
  enlazados. El [contexto archivado](reports/session-context-before-close-2026-09-28.md)
  conserva detalles de releases/ciclos anteriores; no es requisito de arranque.
- Git al comenzar este cierre: sólo privados ajenos modificados
  `mushroom-data/mushroom_observations.json` y raíz `mushroom_observations.json`
  sin seguimiento. **No incluirlos, revertirlos ni copiarlos a HA.**
- Cierre actual: release 0.2.331 autorizada y publicada; sin cambios en HA real
  ni trabajos operativos. Instalación/parada/arranque HA y trabajos operativos
  los hace el usuario. No SSH sin autorización expresa; no montar SMB por Tailscale.
- Usar `docker-data` para experimentos. El usuario tiene copia local y rechaza
  backups adicionales en HA. Últimos montajes usados `/Volumes/share` y
  `/Volumes/media-1`: verificar origen antes de volver a usarlos. Conservar la URL
  persistida del worker aunque use Tailscale.
- Comprobación proporcional: no releer/hashing de GIS ya verificados ni repetir
  smoke por documentación. La release 0.2.331 ya tiene su smoke final. La siguiente sesión revalida
  sólo lo pertinente a su tarea.
