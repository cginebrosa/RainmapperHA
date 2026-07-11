# Active Context

Contexto operativo actual para continuar RainmapperHA sin cargar toda la
historia antigua. Si una tarea necesita mas detalle, seguir las referencias
indicadas.

## Regla de mantenimiento

Este documento debe ser una ventana operativa, no un historico acumulativo.
Cuando entre informacion nueva, debe salir, resumirse o archivarse informacion
que ya no guie el trabajo inmediato. Las tareas cerradas, descartadas o antiguas
no deben quedarse indefinidamente aqui ni en `docs/todo.md`; mover su memoria
util a `docs/project-archive.md`, `docs/decisions.md` o al documento largo que
corresponda.

## Estado real del repo

- Ruta activa: `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Ultimo release HA publicado: `0.2.199`.
- Commit release: `abe0d49 Release Home Assistant 0.2.199`.
- Imagen HA publicada/verificada: `ghcr.io/cginebrosa/rainmapperha:0.2.199`
  y `latest`, digest multi-arch
  `sha256:527673151e74d5c7a5ae2986eea6502b0f8014699ad4fdb3812cdc5ec2d64afb`.
- Plataformas verificadas: `linux/amd64`, `linux/arm64`.
- Estado HA: `0.2.199` validada por el usuario el 2026-07-11. El MapLibre
  protegido funciona y el popup largo muestra `Pluja` en `Valores IDW`.
- Estado GitHub/GHCR: repo GitHub abierto/publico por decision explicita del
  usuario; no cerrarlo. GHCR ya fue limpiado tras validar `0.2.195`, pero no
  repetir limpiezas sin confirmar version activa/rollback y sin conservar
  manifests/attestations auxiliares multi-arch.
- `rainmapper-local/options.local-ha-ui.json` mantiene un perfil local de
  desarrollo con backfill desactivado, filtro vacio y Wunderground activo.

## Foco activo

1. Decidir si limpiar GHCR de forma conservadora tras validar `0.2.199`.
2. Continuar pruebas de backfill mensual Wunderground/AEMET con ventanas
   pequenas y pausas.
3. Retomar UI setas: `Fenologia` en `Parametros`, redisenar `Evidencia` y
   preparar promocion manual de evidencia a perfil.

## Cambios recientes que importan

### Wunderground

- Wunderground usa la API diaria JSON como fuente primaria y el scraper HTML
  solo como fallback cuando la API falla.
- Los metadatos se leen primero desde `estacions_wunderground.csv`; solo se
  consulta HTML si falta cache o hay fallback.
- El resumen de fuente muestra `API fallback errors`.
- La API puede devolver filas provisionales del dia actual que luego corrige al
  cerrar el dia. Decision del usuario: no anadir logica complicada; aceptar ese
  comportamiento de Wunderground.

### Backfill mensual

- Opciones HA/local:
  - `backfill_months_enabled`
  - `months_init`
  - `months_end`
  - `months_interval`
  - `backfill_pause_seconds`
  - `backfill_station_filter`
- Cuando `backfill_months_enabled=true`, antes del primer lanzamiento se hace
  backup de incrementales.
- El `Current step` del summary debe mostrar tambien la pausa entre ventanas.
- `backfill_station_filter` acepta entradas por fuente con separador seguro
  `source::id1,id2`, por ejemplo `wunderground::ICANIL20`.
- Wunderground en backfill mensual usa fechas locales exactas por ventana para
  no reintroducir el desfase UTC que hacia repetir el mes anterior. El modo
  normal por dias conserva deliberadamente la relectura historica al cruzar mes,
  porque ayuda a refrescar ultimos dias cuando Wunderground aun no ha cerrado
  datos.
- Coste esperado Wunderground: una llamada API por estacion y mes consultado.
  Usar ventanas pequenas y pausas para reconstrucciones largas.

### MapLibre

- La correccion por altitud del IDW usa DEM Terrarium/Mapzen por celda solo en
  metricas de temperatura.
- El calculo ocurre en el navegador, acotado por viewport; no carga CPU de la
  Raspberry Pi salvo servir la pagina/datos.
- Badge visible solo cuando IDW esta activo, la metrica es temperatura y la
  correccion por altitud esta activada:
  - `IDW DEM` verde si usa DEM.
  - `IDW sin DEM` rojo si cae a fallback.
  - Sin badge si la correccion esta desactivada o la metrica no es temperatura.
- `maplibre_estimated_field_dem_zoom` existe en config/defaults y settings de
  dispositivo (`8|9|10`, default `9`).
- El popup de click largo muestra `Valores IDW` antes de la estacion con lluvia
  mas cercana. Debe listar primero `Pluja`, luego temperatura normal,
  temperatura corregida, humedad y viento/racha, independientemente de la
  metrica seleccionada en el mapa. Si un punto no tiene soporte IDW, mostrar
  `-` para ese valor.
- `0.2.199` corrige el problema de cache observado en `0.2.198`: el HTML
  protegido se sirve con `Cache-Control: no-store` y reescribe los query strings
  de assets a la version runtime. Si vuelve a faltar `Pluja`, mirar primero el
  HTML servido/cache-buster antes de tocar el calculo.

### Local HA UI

- `rainmapper-local/docker-compose.yml` pasa variables desde el entorno local.
- Si las opciones HA locales no traen clave, `run.sh` puede tomar `GMAP_API_KEY`
  y `AEMET_API_KEY` del entorno. No hay claves reales en el repo.
- El token de Meteocat queda descartado por ahora: la clave encontrada era de
  Meteocat, no de Dades Obertes/GENCAT que usa el flujo actual.

## Validacion reciente

Para `0.2.199` se verifico:

- `tests.test_web_server_auth`
- `tests.test_wunderground_daily_api`
- `node --check` del MapLibre `app.js`
- `sh -n` de scripts shell tocados
- `git diff --check`
- Imagen multi-arch `0.2.199/latest` en GHCR
- Dentro de la imagen: `index.html` referencia `app.js?v=0.2.199` y
  `app.js` contiene `pointValues.rain`.

## Riesgos y dudas activas

- `0.2.198` queda reemplazada para MapLibre porque el codigo tenia `Pluja` en
  `app.js`, pero `index.html` seguia cargando `app.js?v=0.2.196`.
- La URL manual
  `https://ha.nomentero.com/protected/maplibre/index.html?v=0.2.198` dio
  `404`. Para validar usar el boton/ruta normal del visor protegido y evitar
  query manuales hasta confirmar como enruta HA/Cloudflared.
- Backfill mensual largo puede generar muchas llamadas. Para Wunderground:
  estaciones x meses. Usar `backfill_station_filter`, intervalos pequenos y
  pausas.
- Meteoclimatic RSS no sirve para historico real. Meteocat historico queda
  limitado por la API publica sin token adecuado. AEMET deberia funcionar con
  backfill por ventanas, pero probar primero rangos cortos.
- No cerrar el repo GitHub. Si se limpia GHCR, conservar la version activa,
  `latest`, el rollback inmediato y los auxiliares multi-arch asociados.

## Archivos relevantes

- `rainmapper_core/rainmapper.py`: orquestacion de fuentes, backfill mensual,
  backup y pasos de estado.
- `rainmapper_core/sources/wunderground/`: API diaria/fallback scraper y fechas
  exactas de backfill.
- `rainmapper_core/incremental_upsert.py`: contrato de upsert incremental por
  estacion/dia.
- `rainmapper-app/app/web_server.py`: webUI, rutas protegidas MapLibre,
  cache-busting runtime.
- `rainmapper-app/run.sh`: lectura de opciones HA y variables de entorno.
- `rainmapper-app/config.yaml`: defaults empaquetados HA.
- `rainmapper-local/options.local-ha-ui.json`: perfil versionado para la HA UI
  local; no guardar claves reales.
- `rainmapper-local/docker-compose.yml`: entorno local HA UI.
- `rainmapper_core/viewers/maplibre-viewer/index.html`
- `rainmapper_core/viewers/maplibre-viewer/app.js`
- `tests/test_web_server_auth.py`
- `tests/test_wunderground_daily_api.py`

## Fuente de verdad de setas

En local:

```text
docker-data/mushroom-data/
```

En HA:

```text
/share/rainmapper/mushroom-data/
```

Las capas GIS/DEM pesadas para reconstruccion de contexto de setas en HA deben
vivir fuera de `/share`:

```text
/media/rainmapper/mushroom-GIS/
```

`rainmapper_core/mushroom_paths.py` centraliza rutas. Los artefactos v0
operativos viven en `mushroom-data`, no en `mushroom-lab/working`.
