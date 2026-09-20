# Contexto activo — cierre 21/09/2026

Leer primero [codex-start-here.md](codex-start-here.md). Este documento contiene
lo necesario para retomar; [todo.md](todo.md) amplía prioridades. El
[contexto anterior](reports/session-context-before-close-2026-09-20.md) es archivo,
no una segunda fuente de estado actual.

## Estado y siguiente paso

### HA 0.2.316 publicada

Publicación autorizada tras la aceptación local. GHCR `0.2.316` y `latest`
verificados con el mismo digest
`sha256:df35341875f9c227276c2a1f3c2094f54ce54ca4cf846050b03cd6c4f590302c`,
AMD64 y ARM64. [Informe de release](reports/ha-release-0.2.316.json).
**Siguiente paso: el usuario instala en HA real cuando termine su entrenamiento
en curso.** No se ha instalado ni reiniciado HA real desde esta publicación;
no tocar el worker activo ni lanzar precálculos. Después, verificar resultados
persistidos y la interfaz real, sin atribuirle automáticamente la evidencia local.

El usuario ha autorizado publicar 0.2.316. La candidata incorpora recuperación
GIS/DEM en observaciones, inspector de puntos y agregación MFE25 en microáreas;
[informe de interfaz](reports/gis-recovery-review-2026-09-20.md).
**Incidencia inicial resuelta:** la primera aceptación local completó reconstrucción
y entrenamiento base, pero el multiversión terminó con cinco ajustes fallidos,
ocultos por `Tuning catalog does not cover the plan: 5 missing, 0 unexpected`.
No hubo promoción de esa cadena. Las siete suspensiones se conservaron.

Se corrigió el diagnóstico para comunicar las causas y ámbitos afectados antes
de validar el catálogo incompleto; no se modificaron criterios de entrenamiento
ni admisión. 24 pruebas dirigidas correctas; smoke posterior: 1704 pruebas,
52 omitidas, correcto. HA local y worker reconstruidos/recreados: 216/116 archivos
efectivos coincidentes y huellas de sus coordinadores sin cambios.

El usuario autorizó **una repetición local del multiversión para identificar los
cinco fallos**, ya terminada: todos corresponden a `rbf_svm_calibrated_v1` de
`lactarius_sanguifluus` en los contratos de ventana fija de V2, ambos perfiles
V3 y ambos perfiles V4. Motivo confirmado: `calibration requires at least two
training examples of each class`. Las entradas V3 fijas contenían diez casos
favorables elegibles y uno desfavorable. La repetición usó el mismo snapshot,
58 archivos y el mismo catálogo de ajustes; terminó fallida y limpia, sin
promoción. Evidencia privada ignorada por Git: `tmp/release-0.2.316/`, incluidos
`diagnostic-results.json`, `diagnostic-progress.json` y
`diagnostic-input-parity.json`.

**Reanudado tras confirmar el usuario que las nuevas observaciones están en HA
local.** Comprobado el archivo actual: 505 observaciones, 19 de sanguifluus;
10 episodios favorables y 5 desfavorables válidos/incluidos. La reconstrucción
nueva conserva esos recuentos en las features y está verificada (nueve
artefactos); el entrenamiento base de diez especies está completo/verificado.
El multiversión ha terminado: **792 ajustes correctos, ninguno fallido**;
lote `operational_20260920T204548Z`. Reconstrucción y base promovidos; las cinco
versiones V2–V6 instaladas desde ese lote, con puerta de promoción superada y
revisiones de entrada coincidentes. Recalculadas las huellas de los 792 modelos
y del catálogo de ajustes: ninguna discrepancia. Observaciones privadas,
observaciones/sites locales y las siete suspensiones conservan sus huellas
anteriores. Evidencia actual en `tmp/release-0.2.316/new-data/`, incluidos
`chain-jobs.json` y `promotion-audit.json`; no confundirla con la cadena fallida
anterior. HA local y worker se han reconstruido y recreado después del ajuste de
microáreas; paridad 216/116 archivos, coordinadores sin cambios, smoke final
1704 pruebas/52 omisiones correcto (`smoke-final-ui.log`).

No se ha cambiado el contrato de disponibilidad por modelo. No lanzar
precálculos: siguen a cargo del usuario, después de verificar la promoción.
El precálculo lanzado por el usuario ha terminado: `worker_job_tvVmB0Np_qaP`,
recibido y activo, revisión 71/esquema 1.7, generación nueva y diez especies.
SHA/tamaño, integridad SQLite, identidad deseada y recuentos comprobados:
903 respuestas, 756 coberturas, 574 miembros operativos, 37.773.312 bytes.
Ningún miembro operativo coincide con las siete reglas de suspensión.
Evidencia: `tmp/release-0.2.316/new-data/precompute-audit.json`.
El usuario aceptó el último ajuste visual y autorizó publicar.
Las observaciones privadas se conservan fuera del commit; la documentación
anterior pendiente se incluye en el cierre de la release.

El ajuste posterior de microáreas (Reemplazar si difiere, Mantener si coincide y
selector completo con disposición móvil) ya está en HA local y comprobado con
fixture en navegador a 1600/375 px. Véase el informe GIS enlazado arriba. El smoke final y la reconstrucción de ambos contenedores indicados arriba ya
incluyen este ajuste.

**Último ajuste visual incluido en la release:** «Reconstruir y reentrenar operativo» y
«Ejecutar benchmark científico» son desplegables cerrados por defecto en
Workers y trabajos. Actualizada únicamente la imagen/contenedor HA local;
el usuario prohíbe reconstruir/reiniciar el worker porque entrena para HA real.
Se conserva su contenedor y arranque, comprobados antes/después. El cambio
afecta solo a HTML/CSS de `mushroom_workers_ui.py`, que no se incluye en el
worker; paridad efectiva actual 216/116 archivos sin diferencias.
Validación proporcional: 16 pruebas existentes de la pantalla y navegador real
en HA local a 1600/375 px, apertura con teclado, selecciones conservadas y sin
POST. Evidencia: `tmp/workers-folds-20260920/`. No se han repetido entrenamientos
ni precálculos por este ajuste. Smoke completo final con estos desplegables:
1704 pruebas, 52 omitidas, correcto en 80,720 s (`smoke-release-final.log`).

### Cierre histórico de HA 0.2.315

**HA 0.2.315 publicada; instalación en HA real confirmada por el usuario con
«Hecho» antes de pedir este cierre.** No se inspeccionó HA real para comprobar
su versión efectiva ni se confirmaron sus nuevos entrenamientos/precálculo.
La siguiente tarea útil es verificar esa cadena cuando el usuario la haya
lanzado, mediante registros y artefactos persistidos; no iniciarla por el cierre.

- Release `6bbd0e8`, enviada a `origin/inicial`; GHCR `0.2.315` y `latest`, mismo
  digest `sha256:8d064cef61c9e24fe283796b71aa37ad4d3eea2924141f4be554de1cc1a1f885`,
  AMD64 y ARM64 verificados. [Informe](reports/ha-release-0.2.315.json).
- HA local: `rainmapper-local-rainmapper-ha-ui-1`, imagen `rainmapperha:local-ha-ui`,
  puerto 8101. Worker existente: `rainmapper-worker`, etiqueta 1.1.3 independiente
  de HA, puerto 8110. Ambos arrancados al cierre; worker healthy y sus dos
  carriles idle según `/health`. Revalidar al comenzar otra operación.
- El worker conserva el coordinador principal `http://100.111.77.48:8100` y
  la asociación local `http://rainmapper-ha-ui:8100`. Huellas de ambos archivos
  de configuración comprobadas sin cambios; no redirigirlo ni crear otro worker.
- HA local/worker reconstruidos desde el código publicado; 211/114 archivos
  efectivos coincidentes. Smoke: 1690 pruebas, 48 omitidas, OK. UI ES/CA/EN
  probada a 1280/375/320 px. Evidencia detallada en
  [validación SMI-07](mushrooms/SMI/adoption-2026-09-20/validation.md).
- Cadena local: reconstrucción y base promovidos; multiversión del lote
  `operational_20260920T020702Z`, 714 ajustes correctos, ninguno fallido.
- Precálculo lanzado por el usuario `worker_job_7YWJHNU9LAaR`: completo,
  recibido y activado. Al cierre siguen activos revisión 69/esquema 1.7,
  cobertura 20–26/09, 749 respuestas, archivo de 28.004.352 bytes.
  `active-receipt.json` y metadatos de `active.sqlite3` reconsultados; SHA e
  integridad se comprobaron al publicar. No trasladar este resultado local a HA real.

## Qué incorpora la versión y decisiones que conservar

**SMI común:** extracción regulada + Penman–Monteith + una capa 0–30 cm,
contrato `regulated_pm_single_layer_v1`, para entrenamiento, precálculo y mapa.
El simple original sigue sólo como comparación visual; no es una segunda
variable operativa. La decisión fue aceptada por el usuario tras contrastes
con 22 estaciones, incluyendo ocho combinaciones; no reabrir la investigación
para evitar tomar una decisión práctica. [Justificación y consumidores](mushrooms/SMI/adoption-2026-09-20/README.md).

- La entrada operativa es IDW; Copernicus/ICGC son referencias de auditoría,
  no dependencias del cálculo. Referencia orientativa, sin validación absoluta
  de litros restantes ni de evapotranspiración real del bosque.
- PM usa temperatura/humedad, altitud y viento admisible; radiación estimada,
  viento de 2 m/s estimado cuando falta y Hargreaves como alternativa explícita
  si PM no se puede calcular. No se ha implementado sombra/orientación/dosel.
- Reserva calentada con hasta 365 días, ≥90 días completos y convergencia entre
  arranque seco/lleno; cambiar la ventana del gráfico no reinicia el suelo.
  Los huecos no son ceros. Capacidad SoilGrids 250 m, diferencia entre capacidad
  de campo y marchitez integrada en 0–30 cm. SMI = disponible/capacidad.
- Balance climático sigue siendo lluvia−ET₀; no equivale a cambio de reserva
  (lluvia−extracción regulada−drenaje).
- V2/V3 core/V4 extended no usan SMI; V3+ físico usa SMI y balance; V4 climatic
  usa balance sin SMI; V5/V6 físicos completos usan ambos; V5w/V6w usan escalares
  SMI sin los canales físicos diarios completos. El perfil y las columnas
  reales determinan las entradas, no el nombre del estimador.
- **Migración:** reconstruir entradas y reentrenar modelos físicos antiguos;
  sólo precalcular no basta. Se preservan hiperparámetros verificados del
  catálogo previo, nunca pesos ni métricas. Solicitudes precálculo 1.6 pueden
  avanzar a 1.7 conservando revisión; artefactos 1.6 no se aceptan como actuales.

**Mapa:** nombre del modelo elegido antes del IFF, por fecha; tooltip propio
ES/CA/EN con algoritmo, SMI, balance directo, otras entradas y ventana. Metadatos
obtenidos del artefacto ya cargado y deduplicados por especie. Mantiene distintos
«Sin IFF calculado», «Sin modelo disponible» y abstención. Cabecera con capacidad
y disponible; SMI antes del balance y Terreno al final de los desplegables.

**Suspensiones:** panel cerrado por defecto, JSON independiente
`mushroom_ml_prediction_policy.json` y exportación/importación en Workers.
La migración conserva reglas y generaciones; la imagen no contiene reglas
privadas. Siete reglas de rovelló se aplicaron a HA real en 0.2.314 según la
verificación anterior; confirmar que siguen efectivas tras instalar/entrenar.
No reactivar por rutina. [Contrato](mushrooms/model-suspensions-es.md).

## Pendientes prioritarios y dudas

1. **HA real:** verificar versión, reconstrucción/base/multiversión, recepción y
   promoción; después precálculo y activación, contratos nuevos y siete reglas.
   No sabemos si el usuario ya inició esa cadena. Revisar primero, no repetir
   cálculos caros ni copiar resultados locales.
2. **Falsos positivos:** tres visitas sin setas frente a IFF 86/84/100 del 18/09.
   Puntos: Vallcebre 42.20292/1.84242, Vallcebre 42.18669/1.82177,
   Bellver/Riu 42.31110/1.79167. Fecha de visita y esfuerzo no confirmados;
   las capturas no identificaban el modelo. No se demuestra que el nuevo SMI
   los haya corregido. No convertir visitas incompletas en negativos de entrenamiento.
3. **Indicador del worker:** usuario observó «ocupado» después de cancelar y
   luego confirmó ambos coordinadores en espera. Hay carriles foreground/background
   y asociaciones por coordinador. Semántica del indicador pendiente: el usuario
   cree que debe contar background por coordinador. No imponer «cualquier carril
   ocupado» ni cambiar planificación como arreglo visual. Revisar sólo si se retoma.
4. GIS aplazado, revisión manual GBIF, candidatas WU y nueva limpieza de disco
   no se reabren automáticamente; prioridades y fuentes en `todo.md`.

## Archivos y accesos para continuar

- Física: `rainmapper_core/mushroom_water_physics.py`, `mushroom_soil_water_state.py`.
- Adaptadores: `mushroom_map_hydrology.py`, `mushroom_ml_weather_workspace.py`,
  `mushroom_ml_area_weather_runtime.py`; `mushroom_map_water_physics.py` sólo reexporta.
- Modelos/tooltip: `mushroom_model_labels.py`, `mushroom_map_model_runtime.py`,
  `viewers/prediction-map/prediction-mode.{js,css}`, `prediction-weather.js`, labels.
- Migraciones: `mushroom_ml_tuning_catalog.py`, `mushroom_ml_policy_store.py`,
  `mushroom_predictor_precompute_control.py` (todos bajo `rainmapper_core/`).
- Local: `http://127.0.0.1:8101/protected/maplibre/index.html` (modo predicción)
  o `/protected/prediction-map/index.html`; Workers `/mushrooms/workers`.
- Estado local: `docker-data/mushroom-data/`; GIS canónico
  `docker-media/rainmapper/geography/`; resultados/precálculo
  `docker-media/rainmapper/results/`. HA real usa sus propios `/share` y `/media`.
- Visores independientes: `local-apps/{wunderground,gbif}/{code,data}`;
  los datos/fotos/revisiones quedan excluidos de Git e imágenes. No duplicarlos
  en `docs/mushrooms/GBIF` ni reimportar observaciones automáticamente.

## Permisos y preservación

El usuario lanza el precálculo; instalar/parar/arrancar HA real le corresponde.
Preferir archivos compartidos/API autorizada; no usar SSH sin petición expresa
ni alterar destinos del worker. No crear imágenes/volúmenes/workers auxiliares.
Respetar recursos RPi4 y el circuito local obligatorio antes de otra release.

Antes del cierre documental, único cambio sin commit:
`mushroom-data/mushroom_observations.json`, privado/preexistente; no editar ni
incluir. Este cierre cambia sólo documentación, sin nueva versión/build,
entrenamiento ni precálculo. No asumir commit/push de este cierre: comprobar Git.
Conservar auditorías SMI, datos de los visores y `tmp/soil-review-after-0.2.307/`.
