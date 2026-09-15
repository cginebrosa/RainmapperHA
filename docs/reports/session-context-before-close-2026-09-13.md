# Archivo previo al cierre del 13/09/2026

Snapshot íntegro de documentación antes de consolidarla. No es contexto activo;
sus prioridades y estados antiguos pueden estar reemplazados. Para continuar
leer `docs/codex-start-here.md` y `docs/active-context.md`. El relevo técnico
complementario se conserva en `prediction-map-handoff-before-compaction-2026-09-13.md`.

## active-context.md antes del cierre

````markdown
# Active Context

Ventana operativa actualizada el **13/09/2026**, tras conectar el filtro ecológico.
Revalidar antes de actuar; las pruebas históricas no acreditan por sí solas el estado actual.

**Relevo completo antes de compactar:**
[prediction-map-handoff-before-compaction-2026-09-13.md](reports/prediction-map-handoff-before-compaction-2026-09-13.md).
Contiene decisiones, archivos modificados, fuentes locales, comando de preview,
pruebas y pendientes ordenados. Leerlo para continuar desde este punto; prevalece
sobre los «siguientes pasos» históricos del 11–12/09 y primeros bloques del 13/09.
Preview revalidada en este relevo: HTTP 200, puerto 65517, PID 84535 (temporal).
Los tres JSON del filtro coinciden con las huellas del informe de compatibilidad.
No se han reiniciado procesos ni repetido pruebas para esta actualización documental.
Actualización del **12/09/2026**: el usuario confirma HA `0.2.303` instalado y
funcionando. Confirmación del usuario, sin inspección remota nueva.

## Objetivo y punto exacto de continuación

**Decisiones posteriores a la revisión, 13/09 — vigentes:** el usuario acepta
ventanas amplias para meses, hospedadores/hábitats, pH y altitud min/max de cada
ficha, revisables más adelante. Orientaciones fuera de requisitos para todas.
Salmonicolor/quieticolor permanece unido, con ventanas amplias; no separar
ficha, observaciones ni modelos. Crear pH mínimo/máximo en JSON y mantenimiento
Especies → Ecología → Suelos. Usar cifras de suelo; vacío si no hay datos,
sin trasladar óptimos de cultivo. No cambiar pesos meteorológicos por esta decisión.

Rovelló: mantener ventanas por ficha, pensar aparte el objetivo del Predictor.
Comprobado en código/datos locales: deliciosus se llama «Rovelló»; observaciones
separadas deliciosus 56, sanguifluus 7, vinosus 2, salmonicolor/quieticolor 1;
el informe base incluye solo deliciosus entre esos IDs. No se ha acreditado
entrenamiento conjunto por el nombre visible. **Decisión posterior cerrada:**
conservar observaciones independientes y agruparlas en datos derivados para
entrenar/predecir «Rovelló», con correspondencia versionada y referencias a
los IDs originales. Una curva, compatible si una ficha completa encaja, con
detalle de fichas compatibles. No renombrar el modelo deliciosus ni sumar
curvas. Implementación/entrenamiento pendientes; no lanzar trabajos por esta
actualización documental. Permite futuros modelos por variedad sin perder datos.

Documento actualizado: [revisión y decisiones](mushrooms/prediction-map-species-literature-review-es.md),
§1 vigente y §8 pendientes/grupo. La revisión de 21 fichas y segunda pasada
se conserva como evidencia, no como veto a las ventanas amplias acordadas.
[Anexo](reports/prediction-map-species-literature-review-2026-09-13.json) conserva
el snapshot bibliográfico anterior. **Aplicación local posterior completada:**
21 fichas actualizadas con ventanas amplias, 25 relaciones de plantas y 12 de
bosque añadidas; pH opcional `ecology.ph_min/ph_max` en Ecología → Suelos,
V0/Enriched, guardado/importación y validación. Ambos límites pH quedan `null`
en las 21 fichas por falta de cifras utilizables; nueve óptimos 0–0 y extremos
provisionales de altitud pasan a desconocidos. No se alteraron observaciones,
IDs, nombres, orientaciones, pesos ni modelos entrenados. Catálogo local:
se conservan las 114 entradas y se añade `host_eucalyptus_spp` (115).
[Registro de cambios y backups](reports/prediction-map-species-windows-2026-09-13.json),
[tabla de ventanas](mushrooms/prediction-map-species-literature-review-es.md#11-aplicación-local-completada--13092026).
HA local reconstruido/recreado, modo serve y schedule desactivado; 4 huellas
verificadas. 26 pruebas dirigidas de mantenimiento + 22 de datos/proyección/
perfiles pasan; 42 editores renderizados en contenedor y pH visible vía HTTP.
Datos locales validan con 0 errores/89 avisos. Backups `.keep.json` preservados;
sin publicación, trabajos ni reinicio del worker. No promover semillas automáticamente.
**Incremento posterior — filtro conectado a preview:** lector forestal devuelve
IDs; evaluador residente de las 21 fichas con catálogo local y mappings exactos
aceptados. Sin hospedadores identificados: ninguna candidata. Si una especie
requiere pino negro/abeto y solo hay encinas, tampoco se incluye. Padre de género
↔ especie admitido; especies hermanas no equivalentes: ficha pino negro admite
GIS pinos, pero no pino rojo. Mismo criterio para todas las fichas.
Meses/altitud y pH opcional; sin orientación como requisito. Fichas sin límites
pH no se excluyen por ese dato. Nueva rama del popup muestra candidatas del día
como «Predicción pendiente», sin porcentajes ni curvas de ejemplo, también ante
fallos del lector. Payload `ecology`; el contrato de prototipo aún conserva
`species` de demostración, ignoradas por esta rama visual.
42 pruebas Python dirigidas + navegador real pasan. Avià 42.06511,1.81822:
cero candidatas comprobado con lector y HTTP. Preview reiniciada solo en puerto
65517 conservando argumentos y añadiendo rutas explícitas de perfiles/catálogos/
mappings locales; sesión 92305 (revalidar). Sin cambios de datos o contenedores.
[Informe](reports/prediction-map-ecology-2026-09-13.json),
[especificación vigente](mushrooms/prediction-map-specification-es.md#filtro-previo-conectado-a-la-vista-previa--13092026).
**Siguiente:** completar mappings de hábitat/suelo/litología nuevos (los cinco
exactos actuales no corresponden a productos ICGC nuevos; especies que requieren
ese hábitat siguen sin compatibilidad confirmada). Después agrupación derivada
Rovelló y motor compartido primero local/HA. Comparar con worker cuando haya
predicción completa. No lanzar trabajos ni publicar HA.
Sustituye las indicaciones de siguiente paso de los snapshots anteriores.

## Evidencia anterior y evolución — no usar sus siguientes pasos como prioridad actual

**Aceptación del usuario, 13/09:** el arbolado del visor funciona y se da por
bueno de momento, aunque haya zonas sin información. No ampliar cobertura como
requisito para continuar. Los huecos son información desconocida, no ausencia
de árboles ni incompatibilidad de una seta. Siguiente bloque: conectar IDs GIS,
catálogo y relaciones existentes de especies para evaluar compatibilidad;
completar el tratamiento de pH antes de activar la predicción real. Después,
motor compartido primero en servidor local/HA y comparación con worker.

**Ampliación de hosts completada, 13/09:** autoridad de trabajo:
`docker-data/mushroom-data/mushroom_reference_catalogs.json`; promoción al repo
y HA real pendiente, no sustituir desde seed. Tras autorización de los 83 casos
se añadieron 69 nombres específicos, ocho géneros y seis grupos cartográficos:
31 → 114 hosts; los 100 nombres/códigos inventariados en MFE Catalunya resuelven.
También se completaron alias científicos en doce entradas existentes y los
nombres ES/CA/EN vacíos de Juniperus spp.; se conservaron los nombres del usuario,
IDs, otros campos y grupos. Juniperus communis ya se reconocía por su nombre
científico; Quercus humilis/pubescens y Fraxinus excelsior necesitaban altas.
El lector compartido ya utiliza alias explícitos inequívocos, con prioridad del
nombre científico exacto y sin resolver colisiones arbitrariamente. Recarga
catálogo pequeño por metadatos sin perder caché geográfica. Popup: etiqueta ES;
selección de idioma pendiente. No cambia asociaciones micológicas.
Diez tests del lector pasan; 100 correspondencias comprobadas con lector real.
Validador: cero errores y 93 warnings (diez previos + 83 IDs aún sin referencias
por perfiles/mappings). HTTP local confirma Lles: Roble pubescente/Pino Rojo/
Fresno de hoja ancha; Ger: Pino negro/Enebro; Olvan: Encina/quejigo/Roble pubescente.
Preview reiniciada conservando argumentos, sesión 25987, puerto 65517 (revalidar).
Backup local e informe `reports/prediction-map-host-catalog-completion-2026-09-13.json`;
inventario anterior conservado. No se escribieron seed, perfiles, observaciones
ni HA real. Betula alba y Salix fragilis conservan conceptos MFE pendientes de
revisión taxonómica; cobertura del inventario Catalunya, no exhaustividad nacional.
Siguiente: mappings/compatibilidad ecológica, perfiles/pH y motor real; curvas
siguen simuladas. El usuario preguntó por «sinónimos en popup»: se aclaró que
permiten encontrar el nombre común, no mostrar una lista de sinónimos.

**Entrega anterior del 13/09 (snapshot previo a la ampliación anterior):** arbolado en una fila de ancho completo debajo de la
ubicación/altitud/pH, con datos MFE reales de Catalunya. Lector compartido
`mushroom_map_forest.py`, preparador explícito `prepare-prediction-map-forest.py`;
índice activo `mfe25/prepared/catalunya-point-index-v2-2026-09-13.sqlite` (23,8 MB).
Vista previa con `--forest-index` y `--forest-catalogs` apuntando al catálogo
editable `docker-data/mushroom-data/mushroom_reference_catalogs.json`.
Sesión 21168, revalidar antes de reiniciar. Ambos puntos de Olvan dan encina,
quejigo y Quercus humilis; Ripoll da haya/pino/Quercus humilis. Se conservan los
nombres científicos sin correspondencia exacta y no se infieren ausencias.
Cinco pruebas del lector y 18 de contrato/broker completadas; navegador con
fila completa y móvil; cuatro controles contrastados con originales, HTTP real
comprobado. Informe `reports/prediction-map-forest-2026-09-13.json` y detalle en
la especificación central. Tres polígonos grandes subdivididos sin elevar límites;
uno corregido solo en copia auxiliar con control de área. Fuentes y cachés
antiguas conservadas. No jobs ML, descargas ni publicación/recreación HA/worker.
Corrección del catálogo tras el aviso sobre Juniperus: la vista previa leía
la copia del repositorio mientras la nueva entrada Enebro estaba en docker-data.
Ahora usa ese catálogo editable y recarga los nombres solo cuando cambian sus
metadatos; conserva la caché geográfica y vuelve a aplicar etiquetas al resultado.
Siete pruebas dirigidas completadas, incluidas alta/edición/baja de nombres y
recuperación de guardado incompleto. Consulta HTTP de 42.46291, 1.82695 devuelve
Pino negro y Enebro. No se ha escrito en los catálogos del usuario.
Pendiente: ampliar esquemas/regiones MFE, mappings/compatibilidad revisados,
pH de especies e integración del motor real. Probabilidades aún simuladas.

**Última entrega técnica del 12/09:** lector `mushroom_map_land.py` conectado al
adaptador geográfico residente y popup de Terreno: cubierta ICGC 2024 y geología
ICGC 1:50.000 con códigos/descripciones originales, sin mappings ni inferencia.
Vista previa actualizada en `http://127.0.0.1:65517/protected/prediction-map/index.html`
con las rutas opcionales `--land-cover` y `--geology`, conservando el resto de
opciones. Última sesión de proceso 21168 (catálogo editable conectado); revalidar antes de reiniciar.
Primera entrega: 40 pruebas Python y navegador, consulta HTTP real en Pallars.
Detalle y recursos en §8 central y `reports/prediction-map-land-context-2026-09-12.json`.
**Corrección posterior al aviso del usuario:** cuatro polígonos grandes divididos
en 256 piezas en `mushroom-map-GIS/icgc-cobertes-2024/prepared/oversized-parts-2026-09-12.gpkg`
(22 MB), sin modificar el original ni elevar límites. Preparador
`scripts/prepare-prediction-map-land.py`; lector auxiliar `mushroom_map_land_parts.py`.
Vista previa activa con `--land-cover-parts` además de sus argumentos anteriores.
24 pruebas de lectores + 18 de contrato/broker; 12 controles coinciden con las
geometrías originales. Ripoll/Selva ya dan cubierta disponible por HTTP en el
visor local. Cortes artificiales no producen límites: se unen piezas cercanas
del mismo original. Informe `reports/prediction-map-land-parts-2026-09-12.json`.
**Siguiente paso:** ampliar cobertura MFE25/hospedadores y mappings revisados; pH en
fichas y compatibilidad/inferencia siguen pendientes. No se han lanzado jobs,
descargas o builds HA/worker ni modificado perfiles/observaciones/coordinadores.
El archivo auxiliar se preparó explícitamente una vez en el Mac, no mediante
un trabajo del coordinador; la consulta nunca lo reconstruye.

**Última prioridad confirmada:** completar primero vegetación/geología y el
contexto de compatibilidad ecológica con reglas justificadas; después integrar
motor/selección semanal y validar antes de mostrar probabilidades reales.
La lista anterior que posponía ecología hasta después de la predicción queda
reemplazada. Las reglas aún no están definidas: revisar bibliografía por especie,
fuente normalizada de Marc Estevez y perfiles, sin activar afinidades numéricas
provisionales. Primer trabajo: lectores cartográficos descriptivos y matriz de
correspondencias/evidencia. Detalle y procedencia en §8 central. Francia sigue
aplazada; desconocido no significa incompatible. La integración del motor puede
avanzar en paralelo, sin adelantar su aceptación científica.
Bibliografía solo durante preparación/revisión de reglas. Cada predicción usará
una tabla local compacta, revisada y versionada, igual en HA y worker; sin PDF,
web ni LLM por clic. Artefacto de reglas todavía por definir/implementar. Ante
carencias: compatibilidad desconocida, nunca búsqueda o invención en ejecución.

Revisión del 12/09 de perfiles/catálogos solicitada por el usuario: reutilizar
Especies, Reference catalogs y GIS mappings antes de integrar predicción real.
Inventario y cadena de traducción documentados en §8 central: 330 afinidades con
IDs existentes, pero 21 perfiles pendientes de revisión; los ceros no son vetos.
pH min/max existe en 8 tipos de suelo del catálogo, no como rango por especie.
Ampliación opcional de la ficha aceptada por el usuario, todavía sin implementar
ni rellenar valores. Acepta también los estados iniciales de compatibilidad,
incompatibilidad e información insuficiente, revisables con los resultados.
Decisión posterior: aceptar coincidencia entre hospedador genérico y específico
en ambos sentidos según la jerarquía del catálogo (GIS «pinos» sirve para una
relación con pino silvestre). Conservar el ID original y explicar coincidencia
por grupo, sin inventar identificación específica ni equiparar automáticamente
taxones específicos distintos. Detalle en §8 central.
Conservar evidencia y revisión por relación; revisar el guardado del
formulario para no perder campos nuevos. Cinco mappings exactos en cada copia
local inspeccionada no equivalen a las 67 filas de la captura del usuario: la UI
combina mappings y candidatos, y no se ha comprobado el origen de esa instancia.
No sincronizar ni reemplazar esos datos a partir de la diferencia de recuentos.

Nueva tarea acordada del 12/09: revisión cruzada por especie de las fichas de la
UI frente a toda la biblioteca local (incluidos Sporas, Marc Estevez,
`prediction/` y `fruiting-phenology/`), y de esos documentos entre sí. Matriz de
valor actual, fuentes, coincidencias/conflictos y cambio propuesto; alcance y
criterios en §8 central. Pendiente, no confundir con el inventario de IDs ya
hecho. Identificar primero el origen efectivo de las fichas V0/Enriched y no
atribuir a la instancia del usuario la copia del repositorio. Mantener como
siguiente paso los lectores/traducciones del terreno; revisar las relaciones
que se activarán antes de validar compatibilidad y extender la comparación al
resto de campos/especies. No sobrescribir valores por ser una fuente más nueva,
ni resolver discrepancias promediando cifras o repitiendo descargas.

**Traspaso preparado antes de compactación, a petición del usuario:**
[contexto operativo del 12/09](reports/prediction-map-handoff-before-compaction-2026-09-12.md).
Contiene las últimas confirmaciones, implementación, límites y punto de entrada
al motor existente. No sustituye la especificación central.

Desarrollo nuevo **Mapa de predicción**, complementario al **Predictor** actual:
al pulsar un punto, informe de terreno, compatibilidad de especies, meteorología
y, tras validación, predicción. Catalunya primero, con datos para España.
**Primer prototipo local implementado el 12/09/2026, con datos simulados;
con municipio, altitud, pH y meteorología observada reales en la vista previa;
sin inferencia geográfica ni instalación en HA.**

**Referencia principal del diseño:**
[prediction-map-specification-es.md](mushrooms/prediction-map-specification-es.md).
Reúne objetivo, alcance, componentes, visor, permisos, datos, reparto HA–worker,
integración con la aplicación actual, pruebas, fases y decisiones abiertas.
Actualizar allí las decisiones y sincronizar sus anexos; el seguimiento registra
ejecución. El mapa meteorológico actual debe conservar exactamente su
comportamiento; las funciones nuevas se habilitan solo en la ruta nueva.
Interacción acordada el 12/09/2026: mismo visor MapLibre, botón entre las opciones
de la derecha, inmediatamente debajo de IDW, para entrar en modo predicción;
SVG de diana con dardo incluido en el prototipo, pendiente de aceptación visual.
Toque/clic fuera de estaciones para
mostrar predicción por especies de esa zona. Sin selección previa obligatoria
de especie/fecha; contrato inicial y alcance implementado en §5.1 del documento central.
Resultado en popup anclado al punto con flecha/estilo actuales de Rainmapper,
por aclaración del usuario; sustituye propuesta lateral y ficha inferior móvil.
Al hacer clic fuera de estaciones, modal inmediato «Calculando predicción…» durante la espera;
al terminar se cierra y aparece el popup. Cancelación y errores explícitos,
sin espera perpetua ni recarga del visor. Flujo implementado con respuesta demo.
Decisión revisada: en modo predicción, clic y hover sobre una estación conservan
sus popups meteorológicos actuales, sin solicitud ni modal predictivo. El clic
fuera de estaciones consulta predicción. Acceso inicial solo para administradores, dejando
preparado un permiso individual para habilitar después a otros usuarios.
Contenido: referencia Sporas inspeccionada en Safari el 12/09/2026; propuesta y matriz
de información en §4 de la especificación central. Horizonte acordado de hasta
una semana, sin previsión meteorológica por ahora. Viento solo si hay una serie
utilizable; si no, omitirlo. Reutilizar el visor existente; integrar GIS en el
worker no significa rehacer el mapa visual.

Inicio técnico autorizado por el usuario: nueva ruta
`/protected/prediction-map/index.html`, composición de la plantilla existente
y extensión opcional en `rainmapper_core/viewers/prediction-map/`.
Los cuatro archivos del visor meteorológico original siguen sin cambios.
API administrativa `/api/mushrooms/prediction-map`: `capabilities`, `demo` y
reserva `queries` que devuelve 503 sin crear trabajos. Permiso reservado
`can_use_prediction_map`, sin edición de usuarios reales. Veintitrés pruebas Python
dirigidas (13 de contrato/traducciones, tres de IDW y siete de HTTP existente)
y prueba Chrome aislada de escritorio/móvil superadas; alcance y
límites de evidencia en §9.1 central. No equivale a paridad de contenedores.

El usuario informa que ha terminado su runner meteorológico local y que ahora
corre su precálculo. Aviso del usuario, no estado inspeccionado por este trabajo.
Las pruebas del prototipo usan datos sintéticos y no intervienen en ese proceso.

Vista previa manual solicitada posteriormente por el usuario: servidor temporal
en `http://127.0.0.1:65517/protected/prediction-map/index.html`, iniciado con
`tests/prediction_map_browser_check.mjs` y `--preview`. Lee los GeoJSON locales
de `docker-data/PublicData`, usa sesión ficticia y predicciones simuladas; no
es HA local. Comprobar que siga activo antes de reutilizar la URL. No se ha
reconstruido/reiniciado HA ni el worker para mostrarla.

Actualización municipal: capa IGN nacional preparada (8.220 recintos de cuarto
orden, GeoPackage 78.630.912 bytes). Lector residente aislado y nombre opcional
conectados a la vista previa; curva predictiva todavía simulada. Cinco pruebas
geométricas y navegador escritorio/móvil correctos; detalles y medidas en §4.5
central y `docs/reports/prediction-map-municipalities-2026-09-12.json`.
La vista previa conserva el puerto 65517 y usa un proceso Python Homebrew con
GDAL, distinto de HA/worker. No se han añadido esas dependencias a producción.

Prioridad reiterada por el usuario: **el mapa de predicción aunque el rendimiento
inicial sea subóptimo**. Servidores/AWS/migración de HA son ideas futuras y no
deben desviar el desarrollo. Municipio opcional: su ausencia en la Cerdanya
francesa no bloqueará una predicción que disponga de datos y modelo aplicables.
La capa francesa queda aplazada, sin descarga. Siguiente avance funcional:
conectar el informe geográfico real y preparar el cálculo validado, sin presentar
como reales las curvas de demostración ni ampliar cambios al visor actual.

Comprobación francesa solicitada después: DEM francés de 5 m y las 54 capas de
retención + nueve de pH dan valores en los puntos representativos de Font-Romeu,
Quérigut y sus tres microáreas. Los tres contextos persistidos tienen DEM `ok` y
SoilGrids `complete`. Faltan capas francesas de vegetación y geología en las
raíces revisadas; ambas consultas vectoriales operativas dan cero coincidencias,
y los IDs ecológicos están vacíos. Evidencia actual en
`docs/reports/prediction-map-france-local-layers-2026-09-12.json` y §6 central.
No confundir cobertura puntual local con cobertura completa del corredor,
copias efectivas en otros ejecutores o predicción geográfica ya disponible.

Decisión siguiente: vegetación y ecología francesas pendientes, sin abordarlas
ahora; continuar el mapa. Entrega acotada terminada: altitud y pH reales en Terreno
de la vista previa, índice SQLite candidato de 712.704 bytes y lector residente
para puntos (`mushroom_map_terrain.py`). Adaptador común
`scripts/prediction-map-local-geography.py`, en el servidor temporal del puerto
65517; recargar y desplegar Terreno tras clicar con la diana activa.
Siete pruebas de lector, 13 de contrato/traducciones y navegador escritorio/móvil
correctos. Evidencia en `docs/reports/prediction-map-terrain-preview-2026-09-12.json`.
Curvas aún simuladas, sin migración de caché antigua ni integración HA/worker.
Entrega siguiente completada: meteorología observada del punto en el popup,
con 7/15/30/60 días, lluvia, extremos térmicos/humedad y viento de estación
identificada cuando existe. Lee Parquet local sin escrituras ni hashes completos;
adaptador residente `.venv` junto al geográfico GDAL. Vista previa del puerto
65517 actualizada con `--weather-data docker-data/Data --weather-stations
docker-data/stations.txt`. 32 pruebas dirigidas y navegador escritorio/móvil
correctos; mediciones y límites en
`docs/reports/prediction-map-weather-preview-2026-09-12.json` y §8 central.
Decisión posterior: permitir elegir **Servidor local / Worker** en un grupo
**Predicción** de los parámetros del visor nuevo, inicialmente local. Sustituye
la exigencia de ejecución exclusivamente en worker. Selector/persistencia y
tiempos incorporados; `PointExecutor`, broker efímero acotado y canal saliente
`map_report_v1` implementados y probados aisladamente. Integración activable con
`RAINMAPPER_PREDICTION_MAP_CONFIG`; no configurada ni instalada en HA/worker.
Vista previa: local operativo, worker indica indisponibilidad; no se ha cambiado
el coordinador de ningún worker. Ver §5 central para contrato/configuración,
límites y alcance exacto. Empaquetado fuente actualizado, imágenes sin construir.
Persistencia revisada después: `prediction_execution` usa los ajustes del
dispositivo en `/auth/device-settings` y `devices.json`, con guardado al cerrar
el panel como General/IDW/Heatmap. Guardar desde el visor meteorológico conserva
el campo. La vista previa sigue sin autenticación real por decisión expresa:
sesión ficticia, sin crear usuarios/dispositivos HA; ajustes y vista por defecto
se prueban en un JSON temporal aislado, nunca en el `devices.json` real.
Prioridad revisada y confirmada por el usuario: construir las entradas del punto
y reutilizar el motor de predicción existente, con un único código Python para
HA y worker. No ejecutar predicción en el navegador. El navegador conserva su
IDW visual/heatmap/relieve; no confundirlos con entradas científicas del modelo.
Comparar HA–worker solo después de disponer de la predicción completa, incluyendo
el transporte. Revisión e incremento de entradas completados al retomar: lector
puntual de las 54 retenciones SoilGrids y preparación meteorológica/física de
90/365 días con `materialize_area_series` existente, mediante contexto efímero.
El usuario confirma **máximo 60 días en el popup**, aunque el motor use más.
No hay áreas ficticias persistidas ni cambio de fórmulas. Índice candidato
`mushroom-map-GIS/terrain-index/point-inputs-2026-09-12.sqlite`, 2.162.688 bytes;
el índice anterior y la vista previa permanecen en su configuración anterior.
35 pruebas dirigidas correctas; Ripoll/Font-Romeu con entradas de retención y
estado hídrico utilizables. Detalles, tamaños y límites en §8.1 central y
[mediciones](reports/prediction-map-point-inputs-2026-09-12.json).
Siguiente: conectar estos adaptadores al ejecutor y los constructores/inferencia
compartidos, resolver selección y aplicabilidad por coordenada y continuar las
carencias de vegetación/geología/ecología. El ejecutor del visor todavía no llama
a la nueva preparación del modelo y las curvas siguen simuladas. No sustituirlas
antes de validar; no adelantar comparación de ejecutores ni despliegues.

Confirmación posterior: **predicción específica del punto**, también dentro de
un área conocida; no copiar el resultado del área. Reutilizar la continuidad
semanal `weekly_lag_event_v2`: familia común por especie/ubicación, h1–h7 con
corte de emisión menos un día, prioridad por aplicabilidad semanal y evidencia,
veto diario sin cambiar familia y `daily_fallback` cuando no haya familia común.
Mismo motor/reglas no obliga a porcentajes ni familia idénticos si cambian las
entradas del punto. Exigir igualdad con entradas/evidencia/artefactos idénticos.
Documentado con fuentes y pruebas requeridas en §8.2 central; integración al
mapa todavía pendiente. No cambiar opciones ni lanzar precálculo por esta decisión.
Adaptador semanal aislado implementado después:
`mushroom_map_prediction.resolve_species_week` llama a las tres operaciones
existentes de selección. Doce pruebas correctas (seis del adaptador, seis de
continuidad temporal), con miembros sintéticos. Falta conectar la materialización
real de modelos y el origen de evidencia de la coordenada; no está llamado desde
el visor ni sustituye sus curvas demo. El aviso de estación/distancia del popup
se refiere solo al viento; lluvia, extremos térmicos y humedad siguen usando IDW.

Las descargas y la auditoría de cobertura SoilGrids están terminadas. El usuario
acepta los huecos del 2,43 % nacional: no rellenarlos ni repetir esa auditoría
sin una causa nueva. Su última preocupación es el coste de lectura en la
**Raspberry Pi 4 compartida con otros servicios**.

**Trabajo relacionado, sin desplazar la prioridad predictiva anterior:** contrato geográfico y
[diseño del lector compartido](mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md),
ya documentado; implementación y migración pendientes. Propone índice SQLite,
lector residente con ventanas y límites y conservación de contextos.
El [reparto HA–worker](mushrooms/mushroom-map-compute-data-placement-es.md)
queda revisado por indicación del usuario: HA atiende ediciones pequeñas;
workers con copias locales de todos los mapas necesarios realizan preparación
pesada, entrenamiento/precálculo y el futuro mapa a demanda.

Acuerdo posterior del 12/09: imagen con código/lectores y volumen persistente
con GIS/DEM/SoilGrids/municipios e índices preparados. Exportar a otro equipo
debe incluir imagen, paquete de datos, manifiesto e instalador del volumen,
sin reconstrucción desde HA ni dependencia de rutas del Mac. Preservar destinos;
cartografía pública separada de credenciales y artefactos privados. Distribución
y exportación todavía pendientes, con prueba exigida en destino limpio (§6 central).
El usuario prevé trasladar el worker del M1 actual a AWS u otro servidor en casa
según coste; diseño portable a Linux, sin proveedor/instancia/hardware elegidos.
Medir carga antes de comparar costes; no hay recursos contratados ni despliegue.

Trasladar también
la autocura previa al snapshot al worker. No precalcular todos los puntos de
España ni usar HA como fallback pesado automático del nuevo mapa.
Local significa en la máquina ejecutora, no necesariamente en HA; las
descargas de fuentes externas no se harán durante consultas o guardados.
No hace falta volver a descargar el país. La compatibilidad del lector nuevo
aún no está comprobada: solo está implementado el lector candidato de puntos
DEM/pH, no la agregación hídrica ni la migración de consumidores.

La [revisión consolidada del plan](mushrooms/mushroom-prediction-map-progress-es.md)
separa migración compatible, enriquecimiento descriptivo propuesto de la
aplicación actual (incluido pH) y nuevo mapa/predicción geográfica. Los rangos
de pH del catálogo de tipos de suelo ya existen, pero no son pH geográfico
SoilGrids. El uso de los atributos nuevos en modelos no está implementado ni
validado y requiere una fase científica separada.

Visor incorporado explícitamente al plan: la
[propuesta MapLibre](mushrooms/mushroom-map-compute-data-placement-es.md#visor-maplibre-y-entrega-de-resultados-al-navegador)
acuerda un único visor/código compartido con dos rutas iniciales: meteorológica
actual con predicción deshabilitada y nueva con módulo opcional según permisos
e interruptor. Misma plantilla, navegación, estilos y sesión; futura habilitación
en la ruta actual sin reescribir el visor, tras validación. HA sirve la vista;
el navegador dibuja marcador/panel con resultados asíncronos del worker.
Comprobar permisos también en API y regresión en ambas rutas. No calcular el
punto en HA ni recargar el visor para esperar. Prototipo demo local iniciado; una capa
continua de probabilidades es un alcance distinto de la consulta por clic.

## Estado histórico comprobado al cierre del 11/09/2026

Las entradas siguientes son anteriores al prototipo. El trabajo del 12/09 añade
código de rutas/API/extensión y etiquetas, todavía sin commit ni despliegue;
no se ha repetido la inspección remota ni alterado servicios por estas pruebas.

- Rama `inicial`: HEAD, `origin/inicial` y el remoto consultado mediante
  `git ls-remote origin refs/heads/inicial` coinciden en
  `fce06dd24507a17071755763cb24fb7da1a4ce85`,
  `Release Home Assistant 0.2.303`.
- Worktree con documentación/informes nuevos, cambios en `.gitignore` y
  `.dockerignore` para excluir `mushroom-map-GIS/`, y el JSON de observaciones
  modificado por el usuario. Sin commit/push de este trabajo GIS ni de este cierre.
- `docker ps`: `rainmapper-local-rainmapper-ha-ui-1` en marcha con
  `rainmapperha:local-ha-ui`; `rainmapper-worker` en marcha y healthy con
  `rainmapper-worker:1.1.1`. Esto no revalida código efectivo, jobs ni asociaciones.
- No se reconstruyeron/reiniciaron servicios ni se lanzaron trabajos durante
  la preparación GIS y este cierre. No se cambió código de producción.
- HA real `0.2.303` instalado y funcionando, confirmado por el usuario el
  12/09/2026. Pendiente de instalación cerrado; no implica una inspección remota
  nueva ni una revalidación de tags GHCR o de futuros cambios.
- Datos vivos locales: `docker-data/mushroom-data/`. Catálogo auditado:
  `mushroom_known_sites.json`, 34 áreas y 66 microáreas. No confundirlo con
  el catálogo vacío bajo `mushroom-data/`.
- Observaciones protegidas: `mushroom-data/mushroom_observations.json`, SHA-256
  `f2d2df20a7d4397fd905d3e440ef81333feab0c609b43c592ebd18765f4142d0`.
  No editar, restaurar ni incluir ciegamente en un commit.
- Las dos asociaciones del worker se conservan según la última validación
  histórica. Antes de cualquier operación sobre él, leer los destinos persistidos;
  no inferirlos ni cambiar ninguna URL de coordinador.

## Datos preparados, separados del runtime

Todo lo nuevo está en **`mushroom-map-GIS/`**, fuera de `mushroom-GIS` y excluido
por Git y Docker. Hay README junto a cada fuente/descarga. **Los datos, scripts
y manifiestos de esa carpeta solo están en este Mac; un clone de Git no los trae.**
Los informes de `docs/` conservan el inventario y la evidencia resumida.

| Fuente | Preparación y límites documentados |
|---|---|
| IGN MDT25 | 1.524 TIFF, unos 4,59 GB; cabeceras verificadas; dos discrepancias nombre/CRS documentadas. |
| ICGC cubiertas 2024 | 1.524.399 polígonos, 41 clases; pendiente adaptación al informe. |
| MFE25 | 17 comunidades recibidas, 1.994.853 polígonos; campos/diccionarios variables por origen, normalización pendiente. `MFE_42` era Castilla-La Mancha: carpeta renombrada a `mfe_castillalamancha`, nombres internos conservados. |
| GEODE | 612.170 recintos geológicos y 44.464 de Cuaternario descargados; índice local pendiente. Falta Z3000/Catalánides en la capa principal; una geometría vacía documentada. |
| ICGC geología 1:50.000 | 61.437 polígonos locales con índice; 16 controles catalanes positivos y tres exteriores negativos. Prioridad en Catalunya donde cubra, GEODE fuera; no sustituir un hueco por el polígono más cercano. |
| SoilGrids compartido | Descarga nacional y cobertura comprobadas; lector operativo antiguo sigue activo. Detalle abajo. |

Geología debe funcionar **sin consultas online en cada clic**. Los controles
puntuales GIS no prueban ausencia exhaustiva de huecos ni exactitud en el terreno.

## SoilGrids: alcance cerrado y evidencia útil

- **63 combinaciones**: retención `wv0010/wv0033/wv1500`, seis profundidades y
  tres cuantiles (54), más pH `phh2o`, 0–5/5–15/15–30 cm y tres cuantiles (9).
  No descargar textura, carbono ni materia orgánica a escala nacional sin una
  necesidad nueva justificada. No cambiar contratos ni contador de días secos.
- 113 teselas de almacenamiento, 7.119 pares tesela/capa. Los 538 bloques nuevos
  y 1.410 archivos previos copiados/verificados suman **1.948 rásteres,
  795.522.040 bytes**. Reutilizar 1.410 archivos no significa 1.410 lugares:
  eran 55 originales y 1.355 normalizados para 30 teselas antiguas.
- Mayor TIFF individual: **4.140.163 bytes**, no GiB. Todos usan bloques
  256×256 Int16: 128 KiB descomprimidos por bloque. Nueve bloques pH son
  1,125 MiB; 63 bloques, 7,875 MiB. **Son cuentas de píxeles, no medidas de
  RAM total, latencia o tráfico real en la RPi4.**
- Auditoría de 8.105.272 centros de píxel nativos de 250 m dentro de las 19
  regiones españolas GISCO NUTS2 2024 (1:1M): 97,5675 % con las 63 capas
  utilizables; Catalunya 95,4419 %. No es cobertura catastral ni solo de bosques.
- 197.122 celdas con todas las capas a cero y 36 parciales. Mantener ausencias
  y cobertura parcial; pH cero no es un valor de suelo. Los controles pH WCS
  frente al original no autorizan a declarar NoData cualquier cero de retención.
- Las 66 microáreas tienen cobertura completa y conservan contextos, geometrías
  y referencias. Los 1.355 normalizados coinciden por SHA en ambas raíces.
  Selva del Camp tiene una celda sin datos de 326 en el área, fuera de sus
  microáreas. No se han cambiado catálogos ni caché antigua.
- Los bloques nuevos WCS carecen de declaraciones CRS/NoData: normalización
  pendiente. Se conserva retención previa junto a adquisiciones actuales;
  no se ha certificado una edición científica homogénea de toda la descarga.

## Próximo trabajo: lectura y migración controlada

Revisión del código y plan detallado terminados en el
[diseño del lector](mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md).
Verificados `web_server.py:11541`, `:23381`, `:23429`, `:24028`, `:24116` y
`mushroom_soilgrids.py:802`, `:1149`, `:1199`, `:1254`: las áreas no disparan
SoilGrids, las microáreas reutilizan o resuelven su contexto y pueden ampliar
la caché si faltan activos. Ya existen ventanas, pero con hashes completos y
CLI por capa durante la agregación. El Predictor consume contextos persistidos.

1. Implementar índice candidato y lector aislado según el diseño, sin cambiar
   raíces operativas. Normalizar metadatos sin copiar rásteres ni reinterpretar
   ceros de retención como NoData general.
2. Probar identidad de referencias antiguas, procedencia de zonas nuevas y
   compatibilidad numérica; preparar réplica de mapas del worker y fase remota
   de contextos previa al snapshot, con aceptación de deltas en HA. Adaptar
   altas/cambios, consumidores adicionales y CLI según la matriz de reparto.
3. Medir consultas y agregados con límites candidatos: 16 MiB de bloques GDAL,
   una lectura activa y objetivo de RSS adicional de 96 MiB. Son presupuestos
   propuestos, no medidas; no extrapolar tiempos del Mac a la RPi4.
4. Validar integración local y el circuito aplicable antes de aceptar cualquier
   migración a HA. Ningún trabajo, build o prueba sobre HA real está autorizado
   por el mero hecho de documentar este plan.
5. Después de validar, cambiar referencias de forma controlada y conservar
   copia temporal de lo antiguo para rollback. **30 días es una propuesta de
   retención, aún por concretar**, no permiso para borrar automáticamente.
   Retirar lo antiguo solo tras aceptación y comprobación de que no se usa.

La auditoría usa GDAL/NumPy de `/opt/homebrew/bin/python3` como herramienta local;
no añadió bindings Python GDAL a HA. Las utilidades de adquisición usan `.venv`.
No ejecutar la auditoría nacional ni transportar su detalle extenso a la RPi4.

## Decisiones y pendientes posteriores del mapa

- Terreno según punto/celda de cada fuente; meteorología IDW por zona cuya
  escala útil aún hay que auditar. El suelo detallado no convierte la lluvia
  estimada por estaciones distantes en una medida exacta del punto.
- Propuesta: selección con evidencia global de especie, validando por separado
  la transferencia a lugares nuevos. No reutilizar porcentajes de áreas como
  probabilidades geográficas ya demostradas. Primero compatibilidad explicada;
  candidata inicial a siete días. Quince días requiere otro contrato/evaluación.
- Ecología basada en la literatura disponible (21 perfiles analizados), con
  reglas, fuentes e incertidumbre explícitas; distinguir temporada configurada
  de estacionalidad aprendida. No se ha implementado esa capa.
- Sporas sirve como referencia visual. No se confirmó su algoritmo interno ni
  que use teselas grandes. Consulta en Safari autorizada sin cambios en la cuenta;
  no hace falta reabrirla para continuar el lector SoilGrids.
- Predictor existente: continuidad `lag_event` h1–h7 y fallback diario auditado
  se conservan; auditorías de días secos cerradas con decisión de no cambiarlo.
  Otros pendientes, sin desplazar el mapa: aplicabilidad multiespecie,
  Historial, CLI multicoordinador y transporte eficiente (ver TODO).

## Archivos para profundizar cuando corresponda

- [Pasos del mapa](mushrooms/mushroom-prediction-map-progress-es.md).
- [Cobertura SoilGrids y recursos RPi4](mushrooms/mushroom-prediction-map-soilgrids-coverage-es.md).
- [Dimensionado y migración](mushrooms/mushroom-prediction-map-soilgrids-plan-es.md).
- [Diseño del lector, altas/cambios y plan de pruebas y recursos](mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md).
- [Reparto GIS/DEM/SoilGrids, consumidores y réplicas HA–worker](mushrooms/mushroom-map-compute-data-placement-es.md).
- [Inventario de descargas GIS](mushrooms/mushroom-map-gis-downloads-es.md).
- [Viabilidad por coordenadas](mushrooms/mushroom-map-point-prediction-feasibility-es.md).
- Evidencia resumida: `docs/reports/mushroom-prediction-map-soilgrids-*.json`.
- Evidencia local detallada: `mushroom-map-GIS/soilgrids-shared/coverage-audit/`;
  `rpi4-io-review.json`, `coverage.json`, controles de geometría y conservación.
- [Archivo previo al cierre](reports/session-context-before-close-2026-09-11.md):
  releases, pruebas, UI y diagnósticos anteriores. **No hace falta leerlo al arrancar.**

## Límites de esta continuidad

No lanzar entrenamiento/precálculo, reconstruir servicios, publicar HA, cambiar
URLs o borrar datos por cerrar documentación o investigar el mapa. Seguir el
flujo local y `docs/release-flow.md` cuando exista una solicitud de release.
Revalidar evidencia proporcional al siguiente cambio y dar actualizaciones
breves mientras se trabaja, respondiendo al usuario sin abandonar la tarea.

Cierre documental: diff revisado, `git diff --check` correcto, enlaces Markdown
de la documentación viva resueltos y JSON de informes legibles. SHA de las
observaciones protegido sin cambios. No se repitieron tests de producción por
este cambio documental; no se hizo commit, push ni publicación.

````

## todo.md antes del cierre

````markdown
# TODO

Prioridades al cierre del **11/09/2026**. Arranque en `codex-start-here.md` y
`active-context.md`; detalle histórico fuera de esta lista.

Diseño del Mapa de predicción:
[especificación central](mushrooms/prediction-map-specification-es.md).
Esta lista registra prioridades; alcance y fases se mantienen en la especificación.

## P0 — SoilGrids compartido: lectura eficiente y migración segura

- [x] Concretar alcance nacional: retención (54 capas) y pH superficial (9),
  dejando textura/carbono/materia orgánica fuera del alcance inicial.
- [x] Descargar y verificar 7.119 pares tesela/capa, reutilizando archivos
  existentes en la nueva raíz separada, sin modificar la caché operativa.
- [x] Auditar cobertura nacional y las 66 microáreas locales; conservar
  referencias, geometrías y valores antiguos. Usuario acepta huecos: no rellenar.
- [x] Revisar tamaños y bloques: 795,5 MB en total, TIFF máximo 4,14 MB;
  esto no es un benchmark de consumo o latencia en RPi4.
- [x] Proponer diseño y presupuesto medible del lector común: índice,
  ventanas, caché acotada, consultas de propiedades necesarias y ausencia de
  rehashes completos/procesos por capa en cada clic. Diseño documentado,
  sin implementación ni mediciones del nuevo lector.
- [x] Revisar consumidores y reparto: HA para edición pequeña; workers con
  copias locales de los mapas para preparación, entrenamiento/precálculo y
  nuevo mapa a demanda. No significa que las réplicas estén instaladas.
- [ ] Implementar lectores/índices, réplicas y preparación remota previa al
  snapshot; aceptar deltas en HA sin perder ediciones concurrentes.
- [ ] Normalizar CRS/NoData y registrar procedencia/edición, conservando
  explícitamente las celdas parciales. No confundir todo cero con NoData.
- [ ] Implementar y validar localmente la compatibilidad y el circuito de
  creación/cambio de áreas y microáreas; medir RAM/IO/latencia/concurrencia.
- [ ] Cambiar las referencias solo después de validar. Conservar backup
  temporal y rollback; concretar plazo (30 días propuestos, no acordados).
  No retirar archivos aún referenciados ni borrar automáticamente.
- [ ] Resolver cómo conservar/transportar el paquete y sus herramientas:
  `mushroom-map-GIS/` está excluido de Git y Docker; hoy solo existe en este Mac.
- [x] Acordar imagen con código/lectores y volumen persistente de cartografía
  e índices, con generaciones independientes. No reconstruir datos desde HA real.
- [ ] Implementar exportación/importación portable: imagen de arquitectura
  compatible, datos preparados, manifiesto e instalador del volumen. Validar
  destino limpio, reinicio/actualización, rutas portables y conservación del
  coordinador, sin incluir credenciales privadas dentro del paquete cartográfico.
- Referencias: `mushrooms/mushroom-prediction-map-soilgrids-plan-es.md` y
  `mushrooms/mushroom-prediction-map-soilgrids-coverage-es.md`;
  diseño en `mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md`
  y reparto en `mushrooms/mushroom-map-compute-data-placement-es.md`.

## Aplicación actual — enriquecimiento propuesto, separado de la migración

- [ ] Concretar contrato y UI para información adicional de terreno en
  Setales/observaciones: pH estimado, profundidades, incertidumbre, fuentes y
  agregación de polígonos; preservar anotaciones y contextos existentes.
- [ ] Integrarlo sobre los lectores compartidos después de validar su acceso.
  Los rangos `ph_min`/`ph_max` del catálogo actual no son pH geográfico SoilGrids.
- [ ] Si se propone uso en modelos/reglas operativas, evaluarlo como cambio
  científico separado con entradas versionadas; no incorporarlo implícitamente
  por migrar datos o mostrar una ficha.
- Estado y secuencia: `mushrooms/mushroom-prediction-map-progress-es.md`.

## P1 — Mapa de predicción, desarrollo complementario

- [x] Consolidar objetivo, componentes, decisiones, pruebas y pendientes en
  `mushrooms/prediction-map-specification-es.md`, con anexos de detalle enlazados.
- [x] Revisar reutilización del visor meteorológico MapLibre y arquitectura
  HA–worker: diseño documentado; prototipo y conexión real se siguen por separado.
- [x] Concretar interacción inicial: botón entre las opciones de la derecha,
  modo predicción y toque/clic para resultado por especies de la zona.
- [x] Fijar posición inmediatamente debajo de IDW; preferencia del usuario por
  diana con dardo. Dibujo final pendiente de prototipo, distinguible del heatmap.
- [x] Revisar panel de Sporas y contrastar información reutilizable/faltante;
  propuesta central §4: hasta siete días, sin previsión meteorológica y viento
  solo si hay serie utilizable. Datos reales todavía sin conectar al popup demo.
- [x] Concretar presentación como popup anclado al punto, con flecha y estilo
  actuales de Rainmapper, en lugar de panel lateral. Contenido inspirado en Sporas.
- [x] Concretar modal inmediato «Calculando predicción…» durante la espera;
  resultado en popup al terminar, con cancelación y errores previstos.
- [x] Decisión revisada: clic y hover sobre estaciones conservan sus popups
  meteorológicos incluso en modo predicción; consultar predicción al clicar
  fuera de estaciones. Acceso inicial solo para administradores, con permiso
  individual preparado para habilitar otros usuarios posteriormente.
- [x] Primer prototipo local de dos rutas de un único visor, plantilla y núcleo compartidos:
  actual con predicción deshabilitada; nueva con módulo opcional por permisos
  e interruptor. Punto/panel con estados y respuesta simulada identificada.
  Implementado el 12/09/2026; contrato y límites en §5.1 central. Sin worker real.
  Aceptación visual del usuario pendiente; lectores y datasets siguen su fase.
- [ ] Validar regresión meteorológica en ambas rutas, permisos en UI/API,
  revocación y activación/desactivación sin eventos ni peticiones residuales.
  Primera batería local aislada superada (23 pruebas Python dirigidas y Chrome
  escritorio/móvil); faltan validación ampliada de estilos/gestos, Safari/iPhone
  y paridad local antes de una entrega HA. Evidencia y límites en §9.1 central.
- [ ] Conectar petición geográfica asíncrona al worker con estado JSON pequeño,
  cancelación y descarte de respuestas antiguas; sin recarga de página ni
  cálculo del punto en HA. Medir asignación, cola, cálculo, transporte y render.
- [ ] Concretar por separado una eventual superficie coloreada por zona visible;
  no confundirla con el marcador/informe del clic ni precalcular toda España.
- [x] Acordar nombre y separación del Predictor; analizar reutilización,
  literatura y limitaciones de transferencia geográfica.
- [x] Preparar IGN MDT25, ICGC cubiertas, MFE25 (17 comunidades), GEODE e
  ICGC geología local. README junto a las fuentes y evidencia en `docs/reports/`.
- [x] Cubrir la carencia GEODE Catalánides mediante paquete ICGC local,
  comprobado con controles positivos y negativos, sin integrar todavía.
- [ ] Auditar estaciones/IDW para elegir escala meteorológica útil y
  mostrar incertidumbre sin prometer precisión a metros.
- [ ] Preparar índice espacial GEODE, diccionarios MFE25 y consulta local
  homogénea de terreno; conservar límites de cobertura y procedencia.
- [ ] Convertir literatura en reglas de hábitat por especie y diferenciar
  temporada configurada de aprendida.
- [ ] Diseñar/implementar informe de terreno por clic antes de publicar
  probabilidades geográficas. Validar candidata con evidencia global de especie
  en lugares nuevos y horizonte inicial de siete días.
- Seguimiento: `mushrooms/mushroom-prediction-map-progress-es.md`.

## Pendientes conservados — Predictor y ciencia

- [ ] Auditar aplicabilidad multiespecie, empezando por Rovelló / Els Ports /
  2026-09-07; separar diferencia absoluta, desviación normalizada y dirección.
  No imponer tolerancia global. Caso y cifras en el archivo de contexto anterior.
- [ ] Diseñar probabilidad vetada solo diagnóstica, sin recomendación/ranking;
  diferenciar modelo ausente de modelo disponible pero vetado.
- [ ] Crear catálogo explícito de especies posibles por área.
- [ ] Sustituir `Historial` por evaluador persistido hold-out; el precálculo
  semanal no incluye `history`.
- [ ] Mejorar mensajes de incompatibilidad: reentrenamiento, precálculo,
  cobertura y corrupción deben distinguirse.
- [ ] Auditar Llanega negra, Marçot y Múrgola negra cuando sus hold-outs
  externos tengan ambas clases.
- Auditoría de días secos **cerrada**: conservar contador, umbrales y modelos.
  Reabrir solo con nuevos grupos independientes suficientes y un motivo nuevo.

## Pendientes conservados — Operación y Francia

- [ ] Evaluar posteriormente runner meteorológico externo y entrega segura de
  históricos/mapas a HA. El usuario observa ~1 min en M1 y ~6–7 min en RPi4;
  no es un benchmark ejecutado aquí ni autoriza migrar el runner en esta fase.
  Medir carga antes de decidir entre nube y servidor doméstico.

- [ ] Completar CLI del worker por `coordinator_id`, sin alterar los demás destinos.
- [ ] Medir transferencia/hash/escritura/fsync/promoción en RPi4 antes de
  implementar streaming; HA real no es el primer entorno de integración.
- [ ] Revisar GIS/DEM de microáreas francesas desde UI cuando se retome ese
  trabajo; revalidar primero la versión instalada de HA real.
- [ ] Decidir valor de Meteo-France frente a Wunderground antes de implementarlo.
- [ ] Confirmar si quedan por realizar controles visuales de contadores de
  filas y runner mensual Wunderground del TODO anterior. No repetir los ya
  acreditados por una prueba de la misma revisión.
- [x] HA real `0.2.303` instalado y funcionando, confirmado por el usuario el
  12/09/2026. Sin inspección remota nueva; no autoriza otra instalación o release.

## Cerrado anteriormente; no volver a implementar

- [x] Selección semanal de una familia `lag_event` h1–h7 con corte común;
  fallback diario auditado cuando no existe familia completa; fuera de
  temporada no equivale a avería. Precálculo lanzado por el usuario.
- [x] Meteorología observada, presentación compacta, ancho acordado y
  persistencia de desplegables al pulsar tarjetas diarias.
- [x] Publicación HA `0.2.303` y reconstrucción del worker privado `1.1.1`
  registradas históricamente; corrección de reentrega del aviso final incluida.
- [x] DEM francés, tuning inicial de especies, controles CDN Wunderground y
  limpieza auditada del worker documentados en sus especificaciones.
- Archivo de contexto y TODO anteriores:
  `reports/session-context-before-close-2026-09-11.md`.

````

## codex-start-here.md antes del cierre

````markdown
# Codex Start Here

Punto de entrada estable para una nueva sesión en RainmapperHA.

## Qué es el proyecto

RainmapperHA es una aplicación Python empaquetada como add-on de Home Assistant.
Ingiere históricos meteorológicos, genera mapas protegidos MapLibre y mantiene
el dominio micológico: observaciones y media, setales, GIS/DEM, reconstrucción de
artefactos, entrenamiento ML y Predictor de Floradas.

El cálculo pesado puede ejecutarse en HA o en workers externos emparejados. HA
conserva autoridad sobre usuarios, UI, jobs, datasets, promoción de artefactos,
resultados y Diagnostics; los workers son calculadoras sin UI pública.

## Arranque obligatorio

Trabajar únicamente en:

```text
/Users/carlosginebrosa/Developer/RainmapperHA
```

Antes de actuar:

```bash
pwd
git status --short
```

Leer siempre, en este orden:

1. `docs/codex-start-here.md`
2. `docs/active-context.md`
3. `docs/todo.md` solo si hacen falta prioridades más largas

`docs/active-context.md` es una ventana operativa, no un diario. El histórico
está en `docs/decisions.md`, `docs/project-archive.md` y los diseños temáticos.

## Estado general: actualización del 13/09/2026

La vista previa ya conecta el filtro ecológico: muestra candidatas del día con
«Predicción pendiente», sin curvas de ejemplo cuando recibe `ecology`. Los
campos pH están implementados en mantenimiento local, vacíos en las 21 fichas.
Pendiente: mappings nuevos de hábitat/suelo/litología, agrupación derivada Rovelló
e integración del motor compartido; comparación HA/worker después del cálculo completo.
El filtro último solo está activado en preview, no en contenedores ni HA real.
[Relevo del 13/09](reports/prediction-map-handoff-before-compaction-2026-09-13.md)
con estado revalidado y continuación. Los siguientes puntos conservan contexto
histórico y no sustituyen ese orden de trabajo.

- Trabajo activo: **Mapa de predicción**, nuevo módulo complementario al
  **Predictor** existente. Diseño central documentado y primer prototipo local
  implementado el 12/09: ruta nueva con extensión del MapLibre existente,
  modal y popup de ejemplos expresamente simulados. Ampliación posterior:
  municipio, altitud, pH y meteorología observada reales en la vista previa
  mediante lectores residentes; históricos de 7/15/30/60 días y viento opcional.
  Grupo Predicción con ejecución local/worker y tiempos. Canal de informes
  implementado y probado aisladamente, sin activación en el worker instalado
  ni instalación en HA. La vista previa conserva local operativo. Alcance y pruebas
  en §4.5/§6/§8/§9.1 de la especificación.
- Datos nuevos en `mushroom-map-GIS/`, separados de `mushroom-GIS` y excluidos
  de Git y Docker. Incluye fuentes, README, scripts y evidencia local: un clone
  del repositorio no recupera esa carpeta.
- SoilGrids nacional descargado: 54 capas de retención y nueve de pH;
  cobertura auditada y huecos aceptados por el usuario. **Siguiente paso:
  implementar por fases el diseño documentado de lectura para RPi4 y validar
  la migración controlada.** Hay lector candidato para puntos DEM/pH; el lector
  hídrico compatible y la migración siguen pendientes. Workers con
  copia local de los mapas para preparación pesada y nuevo mapa a demanda;
  HA conserva consultas pequeñas de edición. Ver el reparto HA–worker.
  No repetir descargas ni auditoría nacional sin motivo nuevo. La caché antigua
  sigue operativa; no borrar ni cambiar referencias antes de validar.
- HEAD, `origin/inicial` y remoto coinciden al cierre en
  `fce06dd24507a17071755763cb24fb7da1a4ce85`, release HA `0.2.303`.
  Ese es el estado histórico del cierre; el trabajo GIS/documental y el prototipo
  posterior quedan sin commit. Actualización del 12/09/2026:
  el usuario confirma HA `0.2.303` instalado y funcionando; pendiente de
  instalación cerrado, sin inspección remota nueva.
- `docker ps` confirma HA local en marcha y worker privado `1.1.1` healthy.
  No equivale a comprobar sus trabajos, código efectivo ni asociaciones.
  Revalidar esos detalles cuando una acción los necesite y preservar destinos.
- Se conservan selección semanal `lag_event` h1–h7, fallback diario auditado,
  meteorología observada y corrección del aviso final del worker. Los detalles
  de releases y pruebas previas están archivados; no repetir builds o trabajos
  por leer documentación. Auditoría de días secos cerrada: mantener contador.
- `mushroom-data/mushroom_observations.json` contiene cambios del usuario;
  no editar/restaurar ni incluir ciegamente. Datos vivos locales bajo
  `docker-data/mushroom-data/`.

`docs/active-context.md` contiene el estado suficiente para retomar, los riesgos
y el siguiente trabajo. Consultar los informes temáticos solo al profundizar.

## Mapa documental

- **Mapa de predicción — especificación central y punto de entrada al diseño:**
  [prediction-map-specification-es.md](mushrooms/prediction-map-specification-es.md).
  Reúne objetivo, componentes, visor, permisos, datos, HA–worker, integración,
  pruebas y decisiones abiertas. Los siguientes documentos del mapa son anexos
  técnicos, evidencia o seguimiento; no sustituyen esta referencia principal.
- GIS/DEM/SoilGrids, consumidores, copias locales y cálculo HA–worker:
  `docs/mushrooms/mushroom-map-compute-data-placement-es.md`
- SoilGrids, diseño del lector compartido, altas/cambios y pruebas de recursos:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-reader-design-es.md`
- SoilGrids, cobertura aceptada y condiciones de lectura en RPi4:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-coverage-es.md`
- SoilGrids, alcance nacional y migración controlada:
  `docs/mushrooms/mushroom-prediction-map-soilgrids-plan-es.md`

- Mapa de predicción, pasos completados y pendientes:
  `docs/mushrooms/mushroom-prediction-map-progress-es.md`
- Mapa de predicción: nuevo informe por coordenadas, complementario al Predictor;
  análisis sin implementación:
  `docs/mushrooms/mushroom-map-point-prediction-feasibility-es.md`
- Fuentes descargadas para ese módulo, separadas en `mushroom-map-GIS/` con
  README junto a los archivos: `docs/mushrooms/mushroom-map-gis-downloads-es.md`
- Release HA: `docs/release-flow.md`
- Arquitectura y entrypoints: `docs/architecture.md`
- Decisiones: `docs/decisions.md`
- Seguridad de históricos: `docs/history-safety.md`
- Caja negra y procedimiento RPi4: `docs/runtime-diagnostics.md`
- Diseño Predictor: `docs/mushrooms/mushroom-predictor-design-es.md`
- Predictor remoto/worker: `docs/mushrooms/mushroom-remote-predictor-design-es.md`
- Selección durante entrenamiento del candidato más fiable por
  especie/área/día:
  `docs/mushrooms/mushroom-predictor-reliability-selection-spec-es.md`
- Revisión exploratoria de Sporas.io, límites de sus datos visibles y conceptos
  pendientes para Rainmapper:
  `docs/mushrooms/literature/sporas_especies_informe_rainmapper.md`
- Auditoría P0 hídrica multiespecie y multiversión:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`
- Revisión y diseño experimental de la variable de racha seca:
  `docs/mushrooms/literature/prediction/rainmapper_dry_spell_variable_review.md`
- Pruebas aplazadas y batería Python reproducible:
  `docs/reports/mushroom-predictor-p0-pending-tests-and-python-audit-battery-2026-09-05.md`
- Pantalla futura de auditoría del selector:
  `docs/mushrooms/mushroom-predictor-reliability-screen-spec-es.md`
- Optimización acordada del camino frío del Predictor, caché semántica,
  workspace meteorológico común e inferencia por lotes:
  `docs/mushrooms/mushroom-predictor-cold-path-optimization-spec-es.md`
- Precálculo semanal distribuido de todas las especies, áreas y versiones,
  persistido en SQLite en HA y worker con fallback al Predictor vigente:
  `docs/mushrooms/mushroom-predictor-weekly-precompute-spec-es.md`
- Entrega local sellada entre trabajos encadenados del worker:
  `docs/mushrooms/mushroom-worker-chained-job-local-handoff-spec-es.md`
- Alcance y plan operativo únicos para local, HA y worker:
  `docs/mushrooms/mushroom-operational-training-scope-unification-spec-es.md`
- Plataforma de workers: `docs/mushrooms/mushroom-v0-external-worker-design-es.md`
- Diseño vigente del worker multicoordinador y administración CLI pendiente:
  `docs/mushrooms/mushroom-worker-multicoordinator-design-es.md`
- Auditoría y propuesta todavía no implementada para reducir copias, buffers y
  rehashes durante transferencias HA--worker sin debilitar integridad:
  `docs/mushrooms/mushroom-worker-streaming-integrity-performance-handoff-es.md`
- Entrenamiento ML/dataset: `docs/mushrooms/mushroom-ml-training-plan-es.md`
- Versiones canónicas de contratos ML:
  `docs/mushrooms/mushroom-ml-contract-versions-es.md`
- Ciclo de vida persistente y comparación de versiones ML:
  `docs/mushrooms/mushroom-ml-version-lifecycle-es.md`
- Runtime HA/worker y Predictor V2–V6:
  `docs/mushrooms/mushroom-ml-multiversion-runtime-spec-es.md`
- Retención permanente, caché TAR fuera de backups y limpieza segura de
  modelos/artefactos del worker:
  `docs/mushrooms/mushroom-ml-storage-retention-spec-es.md`
- Separación propuesta entre entrenamiento operativo, benchmark, informe y
  promoción:
  `docs/mushrooms/mushroom-ml-operational-benchmark-separation-design-es.md`
- Contrato genérico para perfiles actuales/futuros, candidatas, promoción y
  rollback:
  `docs/mushrooms/mushroom-ml-generic-profile-promotion-plan-es.md`
- Varias versiones ML instaladas a la vez, selector derivado del registro y
  preferida independiente, desplegado en HA `0.2.266`:
  `docs/mushrooms/mushroom-ml-multi-version-installation-design-es.md`
- Auditoría ML v3: `docs/mushrooms/mushroom-ml-v3-data-audit-es.md`
- Especificación ML v3: `docs/mushrooms/mushroom-ml-v3-implementation-spec-es.md`
- Especificación Biology V4, en implementación local por fases:
  `docs/mushrooms/mushroom-ml-biology-v4-implementation-spec-es.md`
- Contrato técnico de caché SoilGrids y persistencia por microárea para V4:
  `docs/mushrooms/biology-v4-soilgrids-cache-contract-es.md`
- Autocura SoilGrids, fase persistente previa al snapshot y degradación
  best-effort por microárea:
  `docs/mushrooms/mushroom-soilgrids-autocure-spec-es.md`
- Progreso por puntos de Biology V4:
  `docs/mushrooms/mushroom-ml-biology-v4-progress-es.md`. Es histórico técnico;
  la elegibilidad y el runtime vigentes se consultan en el registro y en
  `docs/active-context.md`, no se infieren de ese informe de progreso.
- Informe interpretativo y revisión meteorológica de V4:
  `docs/reports/V4_report001.md`.
- Informe canónico de comparación y consenso V2/V3/V4:
  `docs/reports/V2_V3_V4_consensus_report002.md`. El informe 001 queda
  histórico y no debe guiar decisiones.
- V5 raw y análisis de errores:
  `docs/reports/V2_V3_V4_V5_raw_weather_report001.md`.
- V6 suave y jerárquica:
  `docs/reports/V2_V3_V4_V5_V6_smooth_hierarchical_report001.md`.
- Auditoría científica P0 de la señal hídrica, multiespecie y multiversión,
  incluidos los ganadores operativos V2--V6 y las ablaciones por retardos:
  `docs/reports/mushroom-predictor-p0-multispecies-multiversion-hydric-audit-2026-09-05.md`.
- Backfill histórico y promoción:
  `docs/mushrooms/mushroom-weather-historical-backfill-handoff-es.md`
- Almacenamiento y retención meteorológica:
  `docs/weather-storage-retention-plan-es.md`
- Implementación del histórico meteorológico particionado:
  `docs/weather-history-partitioned-implementation-spec-es.md`
- Auditoría de reparación, compactación y corrección de la generación raíz del
  histórico meteorológico:
  `docs/reports/mushroom-weather-history-repair-audit-2026-08-23.md`
- Narrador LLM local opcional:
  `docs/mushrooms/mushroom-worker-local-llm-narrator-design-es.md`
- Contrato perfiles: `docs/mushrooms/mushroom-profiles-v0-operational-contract-es.md`
- Observaciones/schema: `docs/mushrooms/mushroom-observations-schema-es.md`
- GIS: `docs/mushrooms/gis-layer-inventory-es.md`
- Fuentes y GIS para la expansión Font-Romeu--Quérigut:
  `docs/mushrooms/france-sources/`
- Labels: `docs/mushrooms/mushroom-labels-reference-es.md`
- UI de parámetros: `docs/mushrooms/ui/profiles/mushroom-parameters-redesign-es.md`
- UI de observaciones: `docs/mushrooms/ui/profiles/mushroom-observations-ui-current-state-es.md`

## Reglas operativas críticas

- Conservar la cuota de tokens del usuario: las actualizaciones de proceso deben
  ser mínimas y limitarse a estado, resultado o bloqueo. No narrar pasos obvios,
  repetir contexto ni volcar salidas extensas de comandos; resumirlas y mostrar
  solo la evidencia necesaria. Ampliar detalles únicamente cuando el usuario
  los pida o sean imprescindibles para decidir o diagnosticar.
- Una tarea explícitamente encargada autoriza sus ediciones, consultas,
  pruebas, empaquetado y demás pasos no destructivos dentro del alcance. No
  pedir confirmación adicional por acciones inocuas, tampoco durante una
  release ya autorizada. Consultar el MCP Codebase es siempre lectura y no
  requiere permiso. Consultar únicamente antes de una acción destructiva, una
  escritura en HA que no esté expresamente autorizada o una ampliación material
  del alcance; ante una duda real sobre cualquiera de esos tres casos, preguntar.
- No hacer bump, build ni publicación HA sin petición explícita. Antes de una
  release, leer y seguir `docs/release-flow.md`.
- Todo cambio ejecutable destinado a HA real debe probarse primero construyendo
  HA local y, si interviene cálculo remoto, el worker desde el mismo source. La
  prueba debe recorrer el circuito funcional afectado; compilar por sí solo no
  constituye validación. Solo después de la aceptación se publica o instala HA
  real.
- Durante un build/push HA, vigilar la misma sesión cada 20–30 s e informar al
  usuario al menos cada minuto; no duplicar builds. Verificar tags, digest y
  manifests antes de cancelar un cliente que tarde en cerrar.
- HA y worker tienen versiones independientes. Compatibilidad significa
  capacidades y contratos, no números iguales.
- No borrar `docker-data/`, `tmp/`, `mushroom-GIS/`, backups, históricos,
  artefactos o imágenes sin autorización explícita.
- Codex no debe usar Tailscale ni abrir SMB mediante Tailscale. Esta restricción
  no autoriza a retirar la URL Tailscale persistida que el worker real necesita
  cuando opera fuera de la red local.
- No tocar CSV meteorológicos reales sin `docs/history-safety.md`.
- No inventar features, umbrales, pesos, ventanas o reglas micológicas.
- HA real corre en una Raspberry Pi 4 compartida. No usar fuerza bruta,
  expansiones cartesianas, validaciones repetidas, copias grandes ni aumentos de
  límites como sustituto de un diseño eficiente.
- Todo texto visible nuevo de setas debe existir en
  `mushroom-data/mushroom_labels.json` en inglés, español y catalán.
- Evitar ampliar `web_server.py` con dominio nuevo: preferir `rainmapper_core`
  y módulos UI especializados.
- Usar `.venv/bin/python` (Python 3.11) para desarrollo y validación local.
- Preservar el contexto de navegación y no crear versiones divergentes de un
  modal según su origen.
- No limpiar GHCR sin confirmar la versión activa ni crear copias, imágenes de
  reserva o mecanismos de reversión no solicitados. Conservar únicamente los
  manifests/attestations multi-arquitectura necesarios para las versiones que
  el usuario haya decidido mantener.

## Fuentes de verdad y rutas sensibles

- Setas en HA real: `/share/rainmapper/mushroom-data/`.
- Copia local de pruebas: `docker-data/mushroom-data/`; nunca sobrescribir HA
  desde ella sin una sincronización explícita y verificada.
- GIS/DEM pesado en HA: `/media/rainmapper/mushroom-GIS/`; no moverlo a `/share`
  porque inflaría backups.
- Media de observaciones:
  `/share/rainmapper/mushroom-data/media/observation-photos/`.
- Resolver canónico: `rainmapper_core/mushroom_paths.py`.
- `tmp/mushroom-lab/` es laboratorio, no fuente operativa.

## Validación habitual

```bash
PYTHON_BIN=.venv/bin/python ./scripts/smoke-test.sh
.venv/bin/python -m unittest discover -s tests
git diff --check
```

Para un cambio acotado pueden ejecutarse primero tests dirigidos, pero una
release requiere el flujo y validación completa definidos en
`docs/release-flow.md`.

La validación debe ser proporcional al cambio y no un ritual repetido:

- cambios solo documentales: revisión del diff y `git diff --check`;
- código acotado: pruebas dirigidas de los símbolos y contratos afectados;
- cambios transversales, de empaquetado o de alto riesgo: ampliar a la suite
  pertinente y, cuando corresponda, al smoke completo;
- release: un smoke completo sobre el código definitivo antes del bump; después
  del bump mecánico verificar únicamente versiones y cache-busters, salvo que se
  haya modificado código desde el smoke.

No repetir secuencias `smoke → commit/push → documentación → smoke → commit/push`
si los pasos intermedios no cambian código ni artefactos ejecutables. Documentar
el resultado ya obtenido y ejecutar de nuevo solo las comprobaciones que puedan
haber quedado invalidadas.

## Mantenimiento de continuidad

- Actualizar este documento solo si cambia el mapa general, las reglas o la
  arquitectura de alto nivel.
- Sustituir contexto obsoleto en `active-context.md`; no acumular sesiones.
- Registrar decisiones con `[VIGENTE]`, `[REEMPLAZADA]`, `[OBSOLETA]` o `[DUDA]`.
- Mover historia útil fuera de la ventana activa.
- La compactación de continuidad **no puede resumir hasta perder** una decisión
  operativa o científica. `active-context.md` puede conservar solo el estado y
  el enlace, pero `docs/decisions.md` y la especificación temática deben
  mantener fórmula/semántica, alternativas descartadas, motivo, evidencia,
  cifras de validación y condiciones para revisarla en el futuro.
- La genealogía de contratos ML se preserva en
  `docs/mushrooms/mushroom-ml-contract-versions-es.md`: nunca deducir V1/V2/V3
  únicamente del código ni eliminar versiones anteriores al compactar.

````
