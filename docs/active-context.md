# Active Context

Ventana operativa para continuar RainmapperHA sin depender de conversaciones
anteriores. Este documento describe el estado actual, no el historial completo.

## Importación masiva de observaciones + fixes de datos (2026-08-01/02, en curso)

### Estado actual (2026-08-02)

Importación completada y saneada en Docker local. Pendiente revisión manual en la UI antes de subir a HA.

- `review_table.json` en `/Users/carlosginebrosa/Desktop/Fotos Bolets/candidates/`
- 818 archivos de entrada → **772 observaciones totales** en `docker-data/mushroom-data/mushroom_observations.json`
  (126 existentes `include` + 646 nuevas `review`)
  Nota: se eliminaron 33 duplicados y 167 MOV observations respecto al merged inicial.
- Media procesada: 757 ficheros referenciados (fotos + vídeos) en `docker-data/mushroom-data/media/`
- Docker local activo: `http://127.0.0.1:8101`

### Desglose de las 818 entradas originales
- 646 observaciones importadas con `calibration_use: "review"`
- 154 MOVs Live Photo companion detectados y omitidos automáticamente (mismo stem que un HEIC)
- 44 omitidas sin perfil en Rainmapper (18 especies sin definir)
- 3 omitidas no identificadas
- 33 eliminadas por ser duplicados de observaciones `include` existentes

### Fixes aplicados en esta sesión (2026-08-01/02)

**flush_abundance "pending" (nuevo valor de catálogo)**
- Las 646 obs importadas tenían `flush_abundance: null`, bloqueando TODOS los saves con 646 errores de validación.
- Solución: añadido `"pending"` al catálogo `observation_flush_abundance` (`calibration_score: 0.0`, `prediction_favorable: 0`, `sort_order: 0`).
- Las 646 obs parcheadas con `flush_abundance: "pending"`.
- Añadido campo `calibration_score` al formulario de edición del catálogo (era editable solo via JSON raw).
- Validación cruzada nueva: `flush_abundance: "pending"` + `calibration_use: "include"` → ERROR bloqueante.
- Ficheros modificados: `mushroom_reference_catalogs.json`, `mushroom_catalogs_ui.py`, `web_server.py` (handler + template), `validate-mushroom-data.py`.

**Conversión de JPEGs falsos**
- 421 de 645 ficheros `.jpg` contenían bytes HEIC raw (PIL falló durante el import, se guardó raw y se renombró).
- Convertidos a JPEG real con `sips` (macOS nativo). 0 fallos.
- Ningún fichero HEIC queda ni por extensión ni por contenido.

**Borrado de media al eliminar observación**
- `delete_archived_observation` no eliminaba los ficheros de media huérfanos.
- Corregido: al borrar definitivamente una obs archivada, se hace reference counting entre activas + resto de archivadas, y se borran los ficheros con reference_count == 0.
- Patrón idéntico al ya existente en `delete_observation_media`.

**Bug de cambio de especie (causa raíz identificada)**
- El usuario no podía cambiar la especie de una observación importada: el `store.replace` fallaba por los 646 errores de `flush_abundance`. Resuelto al parchear el catálogo.
- UX pendiente de verificar: `observations_return_url` usa `return_selected_species_id` (especie antigua) con prioridad sobre la nueva, lo que puede hacer parecer que el cambio no se guardó aunque sí lo hiciera.

### Scripts en `scripts/observations-mass-import/`
- `README.md` — proceso completo documentado (pasos 1-11)
- `01_assign_areas.py` — point-in-polygon área/micro-área ✓
- `02_assign_evidence.py` — evidencia desde obs más cercana ✓
- `03_map_species.py` — mapeo species→species_id con aliases y reglas contextuales ✓
- `04_generate_observations.py` — genera + media + fusiona con obs existentes ✓
  (detecta y omite MOVs Live Photo companion automáticamente)
- `media_utils.py` — procesado PIL/ffmpeg de imágenes y vídeos, extraído de web_server.py ✓

### Reglas de mapeo de especies (en 03_map_species.py)
- USER_NAME_ALIASES: Tricholoma sp.→terreum, Morchella sp.→elata_complex, Russula sp.→virescens
- CONTEXT_RULES: Boletus sp. + Amanita caesarea→aereus, + Lactarius→edulis, + Tricholoma terreum→edulis
- Boletus sp. standalone: <1000m→aereus, ≥1000m otoño→edulis, ≥1000m otra época→pinophilus

### Decisiones tomadas
- calibration_use: "review" para todas las importadas
- validation_status: del campo confidence (valid/draft/doubtful)
- Especies sin perfil (18 especies): ignorar, no importar
- Fotos con micro_area_id "pending" (5): importar con micro_area_id null
- Fotos sin área conocida (188): importar con micro_area_id null y site_context vacío
- MOVs Live Photo companion: omitir siempre, conservar solo el HEIC
- source.label conserva el nombre original (.HEIC) como dato de trazabilidad, no es una ruta

### Próximo paso inmediato
Revisar las 646 observaciones `review` en Docker local (`http://127.0.0.1:8101`):
- Confirmar especie correcta, pasar a `calibration_use: "include"` las válidas
- Completar evidencias de campo para las que no tenían obs cercanas
- Cuando esté limpio, subir a HA:
  - `docker-data/mushroom-data/mushroom_observations.json` → `/share/rainmapper/mushroom-data/`
  - `docker-data/mushroom-data/media/` → `/share/rainmapper/mushroom-data/media/`

## Análisis de viabilidad ML (2026-08-02, actualizado con análisis profundo)

### Cobertura meteorológica por fuente
| Fuente | Rango disponible |
|---|---|
| Meteocat | dic 2016 → hoy (fuente principal histórica) |
| Wunderground | ago 2023 → hoy |
| Meteoclimatic | sep 2023 → hoy |
| AEMET | jun 2026 → hoy (solo reciente) |

Observaciones sin cobertura meteo: 19 (años 2012–2013). Decisión: mantenerlas como referencia de campo, no invertir en backfill histórico para 19 obs.

### Documentación actualizada (2026-08-02)
Los cuatro documentos ML se actualizaron en la misma sesión:
- `docs/mushrooms/mushroom-ml-training-plan-es.md` — tabla de 8 especies, corte 2018+, Meteocat, scope multi-especie, umbral empírico ≥20
- `docs/decisions.md` — entrada nueva `2026-08-02` con la decisión de viabilidad ML
- `docs/mushrooms/mushroom-predictor-design-es.md` — sección 12 actualizada con base empírica
- `docs/todo.md` — framing "primera especie B. aereus" corregido

### Unidad de análisis correcta: episodio (area_id + fecha)
El conteo de observaciones es engañoso. La unidad real de entrenamiento ML es el
episodio = (area_id + fecha). Varias fotos del mismo setal el mismo día = 1 episodio.
Además, `scarce` y `very_scarce` son `prediction_favorable=0` según el catálogo
`observation_flush_abundance`, es decir, son negativos (visitas sin florada útil).

### Episodios confirmados (área + fecha, clasificación del catálogo)

| Especie | Eps totales | +confirm | -confirm | Ratio | Pend ep | Sin_area obs |
|---|---|---|---|---|---|---|
| B. aereus | 43 | **15** | **10** | 1.5:1 | 18 | 43 |
| A. caesarea | 31 | **7** | **11** | 0.6:1 | 13 | 7 |
| B. pinophilus | 31 | **6** | **10** | 0.6:1 | 15 | 18 |
| L. deliciosus | 31 | **10** | **4** | 2.5:1 | 17 | 27 |
| H. marzuolus | 27 | **10** | **0** | sin neg | 17 | 7 |
| B. edulis | 35 | 1 | 1 | — | 33 | 58 |
| Cantharellus | 8 | 0 | 3 | sin pos | 5 | 13 |
| Morchella | 6 | 2 | 3 | 0.7:1 | 1 | 3 |

### Diagnóstico por especie (modelo de setales conocidos, predicción por area_id)

**B. aereus** — la más madura: 25 eps confirmados (15+/10-). En olvan: 7+/7- en
5 años y 18 episodios — perfectamente equilibrado. 11 áreas distintas.

**A. caesarea** — segunda: 18 eps confirmados (7+/11-, más neg que pos). olvan
tiene 5+/9- en 7 años y 25 episodios. Muy útil para aprender cuándo NO sale.

**B. pinophilus** — buena ratio (6+/10-). guils: 1+/4-, rubio: 2+/1-, la_masella:
1+/2-. Destaca que hay más negativos que positivos, información valiosa.

**L. deliciosus** — 14 confirmados (10+/4-). Caveat: ermita_ascensio tiene 7 eps
pero todos de 2018 (un solo año); diversidad temporal baja.

**H. marzuolus** — 10+/0- confirmados. Sin ningún episodio negativo, el modelo no
puede aprender el umbral de activación. Requiere salidas intencionadas en
condiciones malas.

**B. edulis** — prácticamente vacío (1+/1-): 151 de 153 obs son del import masivo
pendiente de review. Potencialmente la especie más rica tras la revisión.

**Cantharellus** — 0+/3-: todos los confirmados son negativos (scarce/very_scarce).
Inverso al problema habitual.

**Morchella** — 5 eps en bacanella (2+/3-), balance razonable pero solo 1 área útil.

### Problemas transversales que bloquean el avance

1. **646 obs en estado `review`** — bloquean el conteo real de episodios confirmados.
   Hasta que el usuario las revise, B. edulis, H. marzuolus y la mayoría de pendientes
   son incógnitas. Este review es la tarea más prioritaria para el ML.

2. **Sin_area**: entre el 8% y el 45% de obs por especie no tienen `micro_area_id`
   asignada → no son episodizables. Se pueden mapear retroactivamente a un área por
   cercanía geográfica de coordenadas GPS.

3. **Falta de negativos reales** en H. marzuolus y Cantharellus: requiere salidas
   intencionadas en condiciones climáticas desfavorables, con registro explícito de
   no-detección con esfuerzo conocido.

### Ranking operativo

- **Hoy, con datos confirmados**: B. aereus (olvan) y A. caesarea (olvan) son las
  únicas parejas especie/área con señal bidireccional suficiente para un primer experimento.
- **Tras el review de las 646**: B. edulis y H. marzuolus mejorarán sustancialmente.
- **Tras salidas negativas intencionadas**: H. marzuolus pasaría a ser modelable.

## CLAUDE.md creado (2026-08-01)

Se creo `CLAUDE.md` en la raiz del repositorio. Claude Code lo carga automaticamente
en cada sesion. Contiene estructura del proyecto, entrypoints, comandos de validacion,
flujo de release, reglas operativas y referencia del modulo de setas. Mantenerlo
actualizado al introducir cambios estructurales relevantes.

## Repositorio y release estable

- Workspace unico:
  `/Users/carlosginebrosa/Developer/RainmapperHA`.
- Rama: `inicial`.
- Release HA publicada para instalar/probar: `0.2.214`. La ultima instalada es
  `0.2.213` (`145cc03 Release Home Assistant 0.2.213`).
- Imagen: `ghcr.io/cginebrosa/rainmapperha:0.2.214` y `latest`, digest
  `sha256:a13a4bb1a1de0bc901fe198ee01ea25a6fe7fb594b1721321de7df0173cb698a`.
- Manifests verificados: `linux/amd64`
  `sha256:cb03ce65b1d926f96063f2ab2754e4cd299e8c76c5bb365a2d463bcf55b469bc`
  y `linux/arm64`
  `sha256:bf465baef107f537d110463664871ce8e57e6a2bea22f5dbe5601413844180dc`.
- El repositorio GitHub sigue publico por decision explicita del usuario.
- El usuario autorizo expresamente el 2026-07-20 el bump, publicacion y
  commit/push de `0.2.214` tras validar localmente la busqueda corregida.

El codigo de release esta versionado. Antes de continuar, ejecutar
`git status --short`; no limpiar, revertir ni sobrescribir cualquier cambio
local nuevo que aparezca.

## Correccion clave: no existe una imagen HA de desarrollo

No hay, ni se quiere crear, una imagen de desarrollo/sideload de Home Assistant.
Introducirla complicaria innecesariamente el despliegue y la continuidad.

No se creo ni se debe crear una imagen HA de desarrollo. `0.2.208` introdujo el
coordinador normal, `0.2.209` corrigio su refresco bajo Ingress y `0.2.210`
controla la interaccion de Workers y la preparacion costosa de entradas sin
cambiar los flags seguros ni el fallback HA. `0.2.211` integra los avisos de
actividad en el polling: los mensajes de preparacion, cola y conflicto se
retiran al finalizar el trabajo, mientras los errores reales permanecen.

La `0.2.208` arranco con ambos interruptores apagados. Despues se publico
`8100` solo en la LAN, se activo `Enable external worker connections`, se
emparejo M1 y la prueba inocua de asignacion termino correctamente en 13 s.
En `0.2.209` se comprobo que Rainmapper, el worker y la pagina en reposo son
estables, al igual que una asignacion. Una sola prueba de envio de entradas
consume aproximadamente un nucleo mientras calcula los hashes de 5,87 GiB,
termina correctamente y devuelve la CPU a la normalidad. Los clics repetidos
antes de ver respuesta iniciaban varias preparaciones sincronas concurrentes,
agotaban la CPU de HA y provocaban timeouts de watchdog y salidas 137 de otros
add-ons. `0.2.210` prepara el bundle en segundo plano, impide duplicados con un
lock no bloqueante, desactiva inmediatamente el boton y reutiliza una cache
privada de hashes GIS validada por metadatos del fichero.

`0.2.211` ya se instalo y se valido con el worker M1 por LAN. El reposo, la
asignacion, el envio de entradas y la retirada automatica de avisos quedaron
estables. Una reconstruccion candidata privada de todas las especies elegibles
termino verificada al 100 % en 55 s (`Candidate result verified`) sin tocar el
modelo vivo. Despues se activo `Allow external rebuilds and promotion`: un job
operacional completo termino en 49 s y su promocion manual instalo correctamente
el candidato como modelo vivo, retiro la accion y conservo la copia anterior.

Siguiente orden:

1. Publicar solo con autorizacion expresa las mejoras locales: descarte con
   modal de candidatos terminales no promocionados, limpieza segura en HA y
   worker, y pantalla compacta HA + dos workers con trabajos ordenables.
2. Validar el descarte con un candidato terminal no promocionado; despues
   probar corte/reconexion sin revocar la credencial. La reconstruccion parcial
   y la cancelacion de `Amanita caesarea` ya se probaron en HA real.
3. Completar pruebas de freshness/cache y seguridad del endpoint.
4. Verificar otra vez el fallback HA y medir las fases en HA y M1 sobre el mismo
   snapshot/dataset.

La conexion actual usa HTTP en la LAN privada. No publicar `8100` en el router;
Tailscale/TLS/ACL queda como endurecimiento posterior.

## Estado del worker externo local

El prototipo funciona enteramente en el laboratorio Docker local y no depende
de HA real:

- UI Rainmapper local: `http://127.0.0.1:8101`.
- Coordinador local, solo en la red Docker: `http://rainmapper-ha-ui:8100`.
- Health local del worker: `http://127.0.0.1:8110/health`.
- Inicio/parada: `./mushroom_worker_start.sh` y
  `./mushroom_worker_stop.sh`.
- Imagen generica privada: `rainmapper-worker`; servicio/contenedor
  `rainmapper-worker`; volumen persistente `rainmapper-worker-data`.
- El launcher admite `--help`, nombre, URL del coordinador, pairing y modo no
  interactivo; recupera la configuracion no secreta y la identidad desde el
  volumen. El token permanente se guarda separado bajo `secrets/`.
- El worker es headless: la interfaz humana y la autoridad permanecen en
  Rainmapper.
- La comunicacion es outbound desde el worker. Rainmapper conserva la fuente de
  verdad de datos vivos, jobs y artefactos aceptados.
- Pairing temporal de un solo uso, Bearer permanente por worker, registro
  multi-worker, heartbeat, deteccion desconectado, revocacion y ejecutor
  predeterminado estan implementados localmente.
- La cola persistente implementa lease/claim, inicio, progreso, finalizacion,
  cancelacion cooperativa y forzada, y reasignacion solo antes del inicio.
- Un `work_key` impide ejecuciones activas solapadas. Especies disjuntas pueden
  ejecutarse en paralelo; los alcances completos o con especies comunes se
  bloquean.
- La pagina `Workers y trabajos` centraliza los lanzamientos y conserva HA como
  fallback. No existe fallback silencioso si el ejecutor predeterminado esta
  desconectado o no es compatible.
- Alcances externos locales operativos: todas las especies elegibles,
  pendientes y una especie.
- El aviso `Modelo V0 desactualizado` y las antiguas acciones de Observaciones
  navegan a `Workers y trabajos` con el alcance preseleccionado; ya no lanzan un
  rebuild directamente.

### Pipeline, datasets y promocion

- HA y worker usan el pipeline unico
  `rainmapper_core/mushroom_rebuild_pipeline.py`; la ruta HA estable continua
  en `legacy` salvo flag opt-in.
- Contratos versionados locales: `InputManifest 0.1`, `JobSpec 0.1` y
  `ResultManifest 0.1`.
- El snapshot vivo se congela en Rainmapper. El worker descarga solo paths
  declarados, valida tamaños/SHA-256 y nunca monta directamente `docker-data`.
- La imagen no contiene GIS/DEM. El dataset semiestatico se sincroniza desde
  Rainmapper a staging solo si falta o cambia el fingerprint, se valida y se
  activa atomicamente en el volumen persistente.
- Cache actual probada: `mushroom_gis_v0`, 10 ficheros,
  6.306.367.027 bytes. Primera carga a volumen vacio y reutilizacion posterior
  con cero bytes transferidos verificadas.
- El worker genera nueve artefactos candidatos privados, sube manifest y bytes,
  y Rainmapper vuelve a validar contrato, hashes, tamaños y contadores.
- La promocion siempre es explicita. Una promocion completa o parcial instala
  atomica y conjuntamente los nueve artefactos; la parcial mezcla solo las
  observaciones/especies declaradas con el ultimo modelo vivo.
- Antes de instalar los artefactos, HA elimina referencias auxiliares del
  worker y rebasa las rutas de metadatos a las rutas autoritativas del
  coordinador. Los datos privados existentes no se reescribieron durante la
  auditoria.
- Las promociones se serializan para que trabajos disjuntos no pierdan cambios.
- Se conservan como maximo dos copias recuperables de los nueve artefactos
  derivados anteriores (aproximadamente 2 MB por copia, sin GIS/DEM). La poda
  ocurre solo tras una promocion correcta.
- Estas copias son rollback operativo, no un catalogo historico de modelos.
  Para la futura fase ML queda documentado un registro versionado independiente
  con algoritmo, parametros, snapshot/dataset, metricas comparables y seleccion
  explicita del modelo activo.
- La opcion de conexiones externas esta activa en la instalacion real para M1;
  la opcion operacional de reconstruccion y promocion sigue desactivada hasta
  el siguiente ensayo controlado.

## Validacion local de cierre

Resultados comprobados el 2026-07-20 tras consolidar el diff y sus correcciones
posteriores:

- `.venv/bin/python -m unittest discover -s tests`: **386 tests OK**.
- `.venv/bin/python scripts/validate-mushroom-data.py`: **0 errores y 11
  warnings conocidos**.
- `PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh`: **OK**, incluidos los
  386 tests, sintaxis Python/JavaScript/shell, versiones y fixtures.
- Las imagenes locales HA/worker se inspeccionaron sin montar volumenes: no
  contienen `docker-data`, GIS/DEM, credenciales ni configuracion persistente
  del worker. HA contiene solo los assets `mushroom-data` ya versionados.
- Reconstruccion externa completa local, transferencia GIS a volumen vacio,
  reutilizacion de cache, corte/reconexion, cancelacion, corrupcion/freshness,
  retorno de 9/9 artefactos y promocion manual atomica: verificadas.
- Alcance `una especie` para `cantharellus_lutescens`: completado y
  promocionado.
- Alcance `pendientes` para la misma unica observacion: completado y
  promocionado.
- Los hashes de las otras 13 especies permanecieron exactamente iguales.
- Segundo job `pendientes`: cancelado cooperativamente en Meteorologia al 55 %,
  sin promocion.
- La retencion elimino la tercera copia y mantuvo las dos mas recientes.
- La web y el protocolo quedaron separados: `8099` rechaza las rutas del
  worker, `8100` solo acepta el protocolo cerrado y exige Bearer. Una sonda
  manual desde el contenedor worker existente alcanzo `8100` dentro de la red
  Docker; ese puerto no se publico en el Mac.
- El proceso worker que llevaba horas activo no se reinicio para no reclamar ni
  alterar jobs conservados. Sigue usando en memoria la URL antigua `:8099` y
  registra 404; el proximo arranque mediante `mushroom_worker_start.sh` migrara
  la URL local persistida a `:8100` antes de conectarse.
- No quedan rebuilds candidatos activos. La cola local conserva tres probes de
  transporte antiguos en `claimed`; no son reconstrucciones ni modifican el
  modelo. No borrarlos sin revisar/autorizar.

Los contenedores locales se reconstruyeron con el codigo actual y quedaron
encendidos al cerrar, pero la proxima sesion debe comprobar su estado real en
vez de asumirlo.

### Objetivo `prediction_favorable`

La derivacion se verifico explicitamente en los datos locales actuales:

- features: 126 filas = 66 favorables + 60 desfavorables;
- 0 discrepancias respecto a `prediction_favorable` del catalogo;
- 0 valores sin politica conocida;
- modelo entrenable: 125 filas = 65 favorables + 60 desfavorables.

La diferencia es `obs_20241109_0005` (`cantharellus_lutescens`): es favorable
pero sigue en borrador y se excluye del entrenamiento. Sigue pendiente, si se
considera necesario, comprobar visual/operativamente estos recuentos en HA; no
confundirlo con la validacion local ya cerrada.

## Prioridades siguientes

### P0 — Consolidar el prototipo antes de publicar nada

Estado: consolidacion completada, publicada en `0.2.208`, instalada y probada
contra M1 real; el refresco se publico en `0.2.209` y el control de interaccion
y preparacion pesada en `0.2.210`. La sincronizacion de avisos con el estado
terminal de los trabajos se publica en `0.2.211`.

1. La API permanece apagada por defecto, la autenticacion es fail-closed y el
   modo operacional exige simultaneamente API y autenticacion. HA expone dos
   opciones separadas: `Enable external worker connections` y
   `Allow external rebuilds and promotion`, ambas desactivadas por defecto.
2. Se confinan los paths de snapshots/GIS, se verifica la huella del manifest,
   se acota el JSON del protocolo y se evita conservar paths privados del
   worker tras una promocion.
3. El empaquetado fuente excluye `docker-data` y `mushroom-GIS`; la imagen HA
   incluye el coordinador pero no lo habilita. La comprobacion final de la
   imagen construida corresponde a P1, antes de publicar.
4. Preparar un checkpoint/commit solo cuando el usuario lo pida. No mezclar un
   release apresurado con el cierre documental.

### P1 — Preparar una version HA normal para la prueba real

1. Topologia interna definida: web/Ingress permanece en `8099`; el protocolo
   del worker usa un listener dedicado `8100`, no publicado por defecto en HA,
   con rutas cerradas y autenticacion obligatoria. Los controles humanos del
   worker en `8099` solo aceptan Ingress autenticado de HA.
2. Elegir y validar como primera exposicion privada el puerto host de `8100`
   mediante LAN/Tailscale y su ACL/TLS. Comparar Tailscale del host frente a
   sidecar Docker. El sidecar favorece
   portabilidad, pero no elude politicas del Mac ni debe ser requisito para la
   primera prueba si LAN/Tailscale del host basta.
3. Imagen HA local construida con el Dockerfile normal e inspeccionada sin
   volumenes: incluye coordinador/UI/core, no contiene datos privados ni
   GIS/DEM y la reconstruccion local HA sigue disponible en `legacy` por
   defecto.
4. Bump y GHCR de `0.2.214` completados con autorizacion expresa. `0.2.214` y
   `latest` comparten el digest multi-arch verificado
   `sha256:a13a4bb1a1de0bc901fe198ee01ea25a6fe7fb594b1721321de7df0173cb698a`;
   import check arm64: `image_import_ok 0.2.214 False False True True`. Queda
   instalar y validar la busqueda global y el descarte contra HA real.

### P2 — Prueba M1 ↔ HA real

- M1 ya esta emparejado por LAN con HA real y la prueba de asignacion termino
  correctamente en 13 s.
- `0.2.211` esta instalada; reposo, asignacion, preparacion de entradas y
  retirada automatica de avisos quedaron comprobados.
- La reconstruccion completa operacional en M1 termino en 49 s, fue verificada
  y se promociono manualmente al modelo vivo con exito. Falta probar pendientes
  y una especie contra HA real.
- Probar cancelacion cooperativa/forzada, worker apagado, corte/reconexion,
  duplicados/solapes, stale result y cache presente/ausente.
- `0.2.212` ejecuta la promocion en segundo plano con fases, porcentaje y barra
  mediante el polling existente; ya se valido en HA real.
- `0.2.213`: `Descartar` aparece solo en candidatos terminales no
  promocionados y abre un modal. HA elimina resultado y snapshot privados; una
  orden/acuse idempotente por heartbeat elimina el directorio del job en el
  worker. Una promocion activa bloquea el descarte; una interrumpida solo se
  puede borrar si no hay recibo, backup ni staging de recuperacion. El modelo
  vivo, sus dos rollback y la cache GIS/DEM quedan fuera del borrado. Para la
  prueba integral hay que instalar HA y reiniciar el launcher del worker, que
  reconstruye su imagen.
- La misma version compacta `Workers y trabajos`: HA y dos workers caben
  en tres columnas, las pruebas/gestion quedan plegadas, el encabezado pierde
  textos redundantes y el acceso azul que solo hacia scroll. La tabla permite
  ordenar por cualquier columna, muestra los jobs HA como `HA local` y compara
  fechas de HA/worker por instante UTC para evitar ordenes falsos por offset.
- Observaciones deja de mostrar el desplegable heredado de ultima reconstruccion
  GIS: no estaba ligado a un job concreto y podia prometer una revision vacia o
  distinta del trabajo reciente. La ejecucion y el historial quedan en Workers.
- `0.2.214` corrige la busqueda de Observaciones bajo paginacion: Enter envia
  inmediatamente, la escritura se envia con debounce, se vuelve a pagina 1 y
  se buscan todos los campos persistidos y los nombres visibles resueltos de
  especie, area, microarea y catalogos antes de paginar. El usuario la valido
  localmente; falta instalarla en HA.
- Verificar que HA reconstruye localmente aunque no haya worker.
- Medir tiempos por fase HA/M1 con el mismo snapshot y dataset.

### P3 — Portabilidad y ML posteriores

- Repetir `docker load` y bootstrap en otro daemon/host sin reutilizar capas ni
  volumen; probar tambien una actualizacion real del dataset semiestatico.
- Solo despues incorporar jobs separados `build_ml_dataset`, `train_ml_model`
  y `evaluate_ml_model`, sin promocion automatica.
- M5 y AWS quedan diferidos.

## Riesgos y dudas abiertas

- El prototipo grande ya esta versionado en `e2f117d`; los datos persistentes y
  GIS/DEM siguen fuera de Git y no deben limpiarse.
- La equivalencia local no sustituye una prueba en HA/Raspberry ni una prueba
  de red real.
- Falta elegir y validar en HA real la publicacion privada de `8100`, su
  ACL/TLS y la topologia Tailscale inicial; el protocolo ya no comparte el
  listener web `8099`.
- No se ha demostrado aun portabilidad en un daemon/host realmente limpio.
- La auditoria local no encontro secretos ni datos GIS/vivos incorporados al
  contexto de imagen. Antes de publicar sigue siendo obligatorio inspeccionar
  la imagen HA construida y su configuracion efectiva.
- `docker save/load` mueve la imagen, no el volumen persistente; un host nuevo
  debe reconstruir cache/configuracion mediante bootstrap y sincronizacion.
- Los datasets GIS/DEM requieren revisar licencias/atribucion antes de cualquier
  redistribucion fuera del entorno privado.
- El modelo V0 sigue siendo descriptivo/auditable, no un modelo ML predictivo.

## Archivos relevantes

Diseno y continuidad:

- `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- `docs/mushrooms/mushroom-ml-training-plan-es.md`
- `docs/decisions.md`
- `docs/todo.md`

UI/coordinador:

- `rainmapper-app/app/web_server.py`
- `rainmapper-app/app/mushroom_workers_ui.py`
- `rainmapper-app/app/mushroom_profiles_ui.py`
- `rainmapper-app/app/mushroom_known_sites_ui.py`

Worker y despliegue local:

- `rainmapper-worker/`
- `mushroom_worker_start.sh`
- `mushroom_worker_stop.sh`
- `mushroom_lab_start.sh`
- `rainmapper-local/docker-compose.yml`
- `rainmapper-local/docker-compose.worker-local.yml`

Core compartido:

- `rainmapper_core/mushroom_rebuild_pipeline.py`
- `rainmapper_core/mushroom_rebuild_contracts.py`
- `rainmapper_core/mushroom_rebuild_snapshot.py`
- `rainmapper_core/mushroom_rebuild_comparison.py`
- `rainmapper_core/mushroom_worker_*.py`

Pruebas:

- `tests/test_mushroom_rebuild_*.py`
- `tests/test_mushroom_worker_*.py`
- `tests/test_web_server_auth.py`

## Reglas innegociables de continuidad

- Trabajar exclusivamente en el workspace indicado.
- Usar siempre `.venv/bin/python` (Python 3.11), nunca el Python del sistema.
- No revertir ni sobrescribir cambios locales existentes.
- No borrar, sustituir ni versionar datos privados de
  `docker-data/mushroom-data` ni GIS/DEM.
- No hacer bump, release, limpieza GHCR ni cambios destructivos sin peticion
  expresa.
- No crear una imagen HA de desarrollo como atajo.
- Mantener siempre la reconstruccion local de HA como fallback.
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` para `en`, `es` y `ca`.
