# Project Archive

Memoria historica seleccionada. Este documento no es el punto de arranque de una
nueva sesion. Sirve para entender por que se tomaron decisiones o que caminos
fueron reemplazados.

## Como usar este archivo

- Consultar solo si una decision actual no se entiende desde
  `docs/active-context.md`.
- Para el detalle completo, acudir a `docs/codex-handoff.md`, `docs/todo.md` y
  `docs/decisions.md`.
- Las entradas historicas no son instrucciones activas si contradicen
  `docs/active-context.md`.
- Cuando algo salga de `docs/active-context.md` pero siga siendo util para
  entender el proyecto, archivarlo aqui de forma resumida y enlazar el documento
  largo si existe.

## 2026-06 - Core Rainmapper y visores

Se consolido la separacion entre:

- `rainmapper_core/`: descarga, historicos, Tomap, GeoJSON, Bokeh, viewers y
  helpers compartidos.
- `rainmapper-app/app/`: codigo especifico de Home Assistant y WebUI.
- `rainmapper-local/`: entorno Docker local.

Se retiraron wrappers/copias legacy de core en `rainmapper-app/app` y se dejo el
build HA copiando desde la raiz del repo. Esto redujo duplicidad y mantiene como
entrypoints canonicos:

- `python -m rainmapper_core.rainmapper`
- `python -m rainmapper_core.tomap`
- `python -m rainmapper_core.geojson`
- `python -m rainmapper_core.bokeh_maps`

Leaflet y MapLibre quedaron como visores estaticos modernos. MapLibre es el
visor principal recomendado, con datos protegidos por `/protected/maplibre/*` en
HA. Bokeh queda como compatibilidad.

## 2026-06 - Releases HA 0.2.150 a 0.2.180

El ciclo 0.2.150-0.2.180 construyo la WebUI de setas de forma incremental:

- Catalogos de referencia.
- Perfiles de especies.
- Observaciones.
- Labels multiidioma.
- Tabs de Parametros, Calibracion, Observaciones.
- Mejoras visuales de especies, fenologia/topografia y listas.
- Version `0.2.180` fue publicada, instalada y validada por el usuario.

Estas notas viven completas en `docs/todo.md` y `docs/codex-handoff.md`.

Estado activo actual: no hacer release HA ni cambiar version sin peticion
explicita. El trabajo local posterior a `0.2.180` aun no se ha publicado como
nueva imagen HA.

## 2026-06 - Store de setas y defaults versionados

Decision inicial:

- `mushroom-data/*.json` en repo como defaults versionados.
- `/share/rainmapper/mushroom-data/` como copia persistente editable en HA.
- Sembrar defaults al primer arranque si faltan.
- Validar antes de guardar, hacer backup y escritura atomica.

Esta decision sigue vigente, pero fue refinada el 2026-07-05: en la fase local,
`docker-data/mushroom-data/` es la fuente operativa de verdad para setas.

## 2026-06 - Borrado defensivo

Se decidio que especies y observaciones activas no se borran directamente:

- activo -> archivado;
- archivado -> restaurado o borrado permanente;
- borrado permanente con confirmacion defensiva.

Motivo: `species_id` y observaciones pueden afectar calibracion futura.

Esta decision sigue vigente.

## 2026-06 - Idioma de setas

`mushroom_parameter_labels.json` fue reemplazado por:

```text
mushroom-data/mushroom_labels.json
```

Se adopto:

- `en`, `es`, `ca`;
- claves `ui.*`, `catalog_group.*`, `value.*` y campos directos;
- mostrar `missing label: <clave>` si falta una traduccion;
- no fallback silencioso a claves raw.

Sigue vigente. Ver `docs/mushrooms/mushroom-labels-reference-es.md`.

## 2026-07-01 - Predictor v0 mas simple

Se descarto arrancar con un predictor hiperparametrizado basado en muchos
campos finos, litologia detallada y pesos no calibrados.

Direccion elegida:

- señales amplias;
- vegetacion/host;
- suelo amplio;
- habitat;
- altitud aproximada;
- temporada;
- meteorologia reconstruida;
- observaciones locales para calibrar y detectar candidatos.

La UI rica no se elimina: queda como vista avanzada/enriquecida. La v0 usa una
proyeccion minima de `mushroom_profiles.json`.

## 2026-07-01/02 - Laboratorio `mushroom-lab`

Se creo una fase de laboratorio con rutas bajo:

```text
tmp/mushroom-lab/
docker-data/mushroom-lab/working/
```

Sirvio para:

- organizar fotos, QGIS y pruebas;
- crear outputs experimentales;
- construir los primeros contextos meteorologicos/GIS;
- unir features;
- generar un primer `mushroom_model_v0.json`.

Estado actual: historico para el modelo operativo. Desde 2026-07-05, los
artefactos v0 estables viven en `mushroom-data`. `tmp/mushroom-lab/` sigue
permitido para QGIS/pruebas/fotos/intermedios, no como fuente estable del modelo.

## 2026-07-02 - Marc Estevez y perfiles v0

Se reviso visualmente el PDF local de Marc Estevez porque no tenia texto
extraible util. El resumen versionado es:

```text
docs/mushrooms/literature/marc-estevez-species-conclusions-es.md
```

Se normalizo una fuente v0 para 21 especies y se promovieron perfiles/categorias
necesarias dentro del schema rico. El builder historico:

```text
scripts/build-mushroom-profile-v0-candidate.py
```

queda como regenerador/auditor de candidatos, no como fuente paralela de verdad.

## 2026-07-04 - `v0_catalog_gap_promoted`

Se detecto que `v0_catalog_gap_promoted` era ruido tecnico de migracion y se
prestaba a confusion como "origen" ecologico.

Decision:

- no mostrarlo como origen visible;
- no reintroducirlo en perfiles productivos;
- si un ID esta respaldado por Marc, mostrar origen `Marc`.

## 2026-07-04/05 - Origenes de evidencia

El usuario aclaro que necesita ver tres puntos de vista:

- parametros de especie/perfil;
- lo que declara el observador en campo;
- lo que dice GIS/DEM.

Se acordo que "evidencia observacional" no debe mezclar Campo y GIS sin
distinguir procedencia. La UI de Parametros debe mostrar fuente por chip.

Estado: implementado parcialmente en Parametros. Evidencia aun requiere rediseño
semantico.

## 2026-07-05 - Centralizacion en `mushroom-data`

Se eliminaron rutas operativas estables bajo `mushroom-lab/working`.

Decision vigente:

- datos vivos y artefactos v0 en `mushroom-data`;
- `mushroom_paths.py` como resolver canonico;
- sin fallbacks legacy al modelo en `mushroom-lab`;
- `mushroom_model_v0_state.json` para especies pendientes;
- boton rojo global de modelo desactualizado.

Motivo historico: pantallas distintas estaban leyendo rutas distintas, lo que
provoco que el modelo apareciera vacio o desactualizado aunque existieran datos
en otra ruta.

## 2026-07-05 - Reconstruccion no incremental

Se discutio reconstruir el modelo tras cada observacion. Se decidio no hacerlo
automaticamente en cada guardado porque:

- la reconstruccion no era incremental fina;
- en HA puede costar CPU/tiempo;
- el usuario puede introducir o editar varias observaciones seguidas.

Solucion activa:

- marcar especies pendientes al guardar/importar/archivar/restaurar;
- mostrar aviso visible `Modelo v0 desactualizado`;
- reconstruir manualmente desde UI, preferiblemente solo especies pendientes.

## Historico de bugs resueltos relevantes

- `Parametros` saltaba a `Ecologia` al cambiar especie desde otra pestaña:
  corregido conservando tab activo.
- La pantalla de Observaciones/Parametros tendia a volver a `Enriched` como
  default: corregido para preservar `V0` cuando procede.
- El rebuild web podia leer defaults versionados en vez de datos persistentes:
  corregido centralizando rutas en `mushroom_paths.py`.
- Chips de Parametros tenian estados desalineados y alturas excesivas:
  corregido con layout compacto.
- Formulario de observaciones era demasiado estrecho y disperso:
  ampliado y agrupado logicamente.
- Catalogos no resaltaban claramente la fila seleccionada:
  mejorado visualmente.

## Informacion obsoleta o reemplazada

- `docker-data/mushroom-lab/working/models/mushroom_model_v0.json` como salida
  estable: reemplazado por `docker-data/mushroom-data/mushroom_model_v0.json`.
- `/share/rainmapper/mushroom-lab/` como ruta operativa HA: reemplazado por
  `/share/rainmapper/mushroom-data/`.
- Boton "reconstruir GIS" como concepto principal: reemplazado por reconstruir
  modelo v0, que incluye GIS/DEM, meteorologia, features y modelo.
- `v0_catalog_gap_promoted` como origen visible: retirado.
- Literatura incompleta como fuente de umbrales numericos: no permitida.

## Dudas conservadas para futuro

- Como sera exactamente el flujo de promocion manual de candidatos al perfil.
- Si la reconstruccion por especies pendientes necesita optimizacion adicional
  para HA cuando crezcan observaciones.
- Si la importacion EXIF multiple desde edicion debe pedir confirmacion
  explicita.
- Si hara falta importacion CSV/JSON de observaciones una vez el flujo EXIF sea
  suficiente.
- Si la app movil futura usara Cloudflare R2/Workers o una API distinta; ese
  diseño sigue bajo demanda en `docs/mobile-app-architecture.md`.

## 2026-08-18/19 - Fases 1-4: separar operativo/benchmark, candidatas y promoción genérica, Biology V3+ físico

Publicado en HA `0.2.262` (release fases 1-4, ver `docs/decisions.md`). Resumen
del recorrido, útil solo si una decisión actual no se entiende desde
`docs/active-context.md`:

- Fase 1-2: la cadena habitual de reconstrucción resuelve únicamente la
  generación operativa activa (V2 fixed/lag); V2-V6 pasó a ser un benchmark
  científico manual, seleccionable por perfiles, con informe persistente
  (`ml_models/benchmarks/<batch_id>/`), cancelación cooperativa en HA local y
  sin promoción automática. Ambos jobs (`operational`/`benchmark`) requieren
  que el worker anuncie `ml_job_purpose_v1`.
- Fase 3: `biology_v3/common_idw_plus_physical_state` ("Biology V3+ físico")
  se registró como perfil nuevo sin modificar los bundles V3 core, añadiendo
  solo balance hídrico y SMI derivados del mismo IDW (365 días como
  calentamiento, 90 días de ventana predictiva). Comparación real: 216/216
  fits, 0 fallos.
- Fase 4: la unidad de promoción pasó a ser la versión completa (no un
  perfil aislado). Cualquier perfil `operational_eligible` de una versión se
  prepara como candidata desde su informe (`Preparar candidata completa`),
  reutilizando los bundles ya ajustados del benchmark sin repetir
  entrenamiento, y se activa con una segunda confirmación humana separada;
  ambos pasos son transaccionales con rollback. `biology_v3` fue el primer
  objetivo (V3 core + V3+ conjuntos). El score por especie/perfil/contrato
  pasó a elegir el menor Brier validado entre **todos** los estimadores
  declarados (no solo LR/RF); V4-V6 quedaron migrados a `candidate` en el
  registro persistente sin tocar la versión V3 activa.
- **Bug encontrado y corregido durante la primera promoción real V3**: la
  candidata operativa no transportaba el `quality-catalog.json` del
  benchmark fuente (ausencia de Brier en Predictor) y la comparación no
  reenviaba a interpretación la evidencia `significant_rain_found_90d`
  calculada por el adaptador (falso veto de lluvia pese a existir
  acumulados). Corregido conservando el catálogo científico por hash (con
  fallback verificado para generaciones ya instaladas) y separando metadatos
  ecológicos de inputs del modelo. Quedó documentado como contrato
  obligatorio para toda versión futura.
- **Segundo bug relacionado, encontrado al activar V4**: un adaptador podía
  anidar la evidencia ecológica en otro nivel de `quality`; la interpretación
  la recibía como ausente y anulaba el rango aun con datos disponibles.
  Corregido haciendo que la extracción recorra genéricamente todos los
  niveles anidados de `quality`, con una prueba transversal que exige
  Brier/lluvia/compatibilidad/rango coherentes en V2-V6. La causa raíz real
  era que el adaptador diario V4 eliminaba esos campos al reconstruir
  `quality` en vez de propagarlos; se corrigió en el adaptador, no solo en la
  extracción.
- Cifras de validación de cada paso (números de tests, digests de imagen
  local, snapshots de benchmark) quedaron en el historial de commits y en
  `docs/decisions.md`; no se repiten aquí porque ya no condicionan ninguna
  decisión activa.
