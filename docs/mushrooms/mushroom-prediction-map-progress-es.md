# Mapa de predicción — pasos, estado y pendientes

**Seguimiento de la [especificación central del Mapa de predicción](prediction-map-specification-es.md).**
Objetivo, alcance, componentes y fases se mantienen allí. Este documento registra
avance y evidencia; no constituye una especificación alternativa.

Seguimiento iniciado el 11/09/2026. **Mapa de predicción** es el desarrollo nuevo
por coordenadas; **Predictor** es la herramienta actual. Las fuentes se preparan
en `mushroom-map-GIS/`, separadas de los datos operativos.

## Estado vigente — revisión documental 18/09/2026

El código HA 0.2.312 integra el mapa con ejecutores HA/worker, descartes por
fecha y territorio, IFF, suelo no determinado y búsqueda Photon con POI.
El reintento local ante rechazo 503 del worker está implementado en el cliente.
Usuario confirma el buscador corregido en iPhone y Safari del Mac; esto no
constituye validación científica ni prueba completa de todos los gestos móviles.
[Fuentes contrastadas](../reports/documentation-audit-2026-09-18.md) ·
[Estado operativo y pendientes](../active-context.md).

Las entradas siguientes son resultados históricos, no comprobaciones del entorno
actual. En particular, las especies fuera de temporada ahora sí aparecen en
los descartes y la integración ya no está limitada a preview.

## Histórico: temporada visible y filtrado temporal — 14/09/2026

Último ajuste de presentación terminado: tipos de suelo antes de árboles/hábitats
en la cabecera Terreno, usando etiquetas recibidas de los mappings. Descartadas
con nombre y cada motivo en líneas propias, separación entre filas y sin
desbordamiento horizontal en móvil. Sin cambiar suelo/pH ni modelos.

Validación del ajuste: salida `ok:true` de
`node tests/prediction_map_browser_check.mjs /private/tmp/rainmapper-maplibre-4.7.1.js /private/tmp/rainmapper-maplibre-4.7.1.css`.
Chrome escritorio/móvil, orden suelo→hábitat y posición vertical de motivos
comprobados; también fechas, cancelación, errores y ruta meteorológica original.
Captura `exclusions-mobile.png` inspeccionada en
`/var/folders/42/w270zmtn6q17nw__20m8kvsm0000gn/T/prediction-map-browser-gI2mPH`.
JS/CSS servidos por la preview coincidían byte a byte con los actuales.
Son resultados de la ejecución del ajuste, no pruebas relanzadas para documentar.
Safari/iPhone real sigue pendiente; emulación móvil de Chrome no lo acredita.

V6: decisión posterior del usuario, fuera de temporada no aparece ni invoca modelo.
Estado territorial independiente; fase diaria compartida con Predictor. Filas
visibles con «Temporada principal» o «Temporada secundaria», sin editar meses.
106 pruebas y Chrome correctos; API Cercs: marçot fuera, fredolic secundario sin
modelo, edulis principal. Preview recargada en 65517 con configuración conservada.
[Informe](../reports/prediction-map-season-visibility-2026-09-14.json).
Consulta GIS adicional: GEODE contiene unidades con calizas a veces descalcificadas,
confirmadas en copia local; no demuestra suelo superficial por punto.
[Evidencia](../reports/prediction-map-gis-decalcification-2026-09-14.json).

## Balance y próximos pasos — 14/09/2026

**Volumen de lectores actuales y paridad HA local–worker implementados y probados.**
El usuario aplaza revisión visual a fondo y árboles vecinos al TODO. Se ha usado
el worker existente y su asociación ya configurada con HA local; destinos intactos.
[Instalación reproducible y límites](prediction-map-local-worker-setup-es.md).

- Paquete público: 3.510 archivos / 14,54 GB lógicos compartidos por enlaces,
  sin copia adicional. Segunda instalación sin transferencia ni rehash. JSON,
  modelos y meteorología privados siguen en los datos locales, montados en lectura.
- HA local y worker reconstruidos; once archivos compartidos verificados dentro
  de ambos contenedores. La Vansa/Montclar: igualdad de resultados, repetición,
  concurrencia, cancelación y worker desconectado sin fallback. Linux ARM64 en
  el mismo Mac; no equivale a AMD64, otra máquina o rendimiento de RPi4.
- En RPi4 el cálculo se hará mediante worker en principio. HA coordina y entrega;
  comparación local como control de paridad, no para decidir el ejecutor real.
- **Alcance nacional conservado.** GEODE y MFE fuera de Catalunya están descargados
  pero no integrados en el mapa ni en esta generación operativa. No reducir
  territorio ni anunciar 14,54 GB como instalación nacional completa.
- Para HA real falta conectar el mapa con las generaciones privadas de su propia
  asociación en el worker. La prueba comparte datos de HA local, no sincroniza ni
  sustituye los de RPi4. Fuentes públicas reutilizables; privados separados.
- Requisito confirmado: minimizar transporte durante el clic reutilizando
  meteorología del precálculo y fichas ya verificadas si coinciden con HA.
  Cuatro pruebas dirigidas de la caché existente pasan; falta conectar el mapa
  mediante referencias compactas y sincronización solo de cambios/ausencias.
  Los montajes locales no validan ese transporte. [Contrato y aceptación pendiente](prediction-map-local-worker-setup-es.md#sincronización-privada-y-caché-requisito-acordado-integración-pendiente).
- Preservada edición de UI en salmonicolor/quieticolor (`host_abies_spp`) anterior
  a preparar el volumen; catálogo/mappings coinciden con v5. No restaurar backups.

**Pendiente para cerrar la entrega nacional:** integrar GEODE/MFE, completar su
paquete operativo, recepción/reutilización de datos privados por coordinador y
prueba en destino independiente. Quedan además validación científica, medición
representativa de recursos/IO y posterior aceptación de release. Revisión visual
profunda/Safari y árboles vecinos siguen aplazados. No se ha publicado HA real,
entrenado, precalculado ni lanzado runner o nueva descarga.

[Resultados y huellas](../reports/prediction-map-local-worker-integration-2026-09-14.json).

## Estado histórico: dos niveles y cuatro reglas suelo/pH — 14/09/2026

Política `territorial_species_windows_v5`: la fecha no altera las candidatas.
El predictor conserva fenología y decide probabilidades temporales. Filtrado antes
del contexto hídrico y del modelo; sin candidatas, salida temprana; null distinto
de cero y filas sin cálculo al final. UI con motivos condicionados y descartes.
Cuatro fichas locales: aereus, edulis, pinophilus y cibarius; pH/altitudes/hosts y
resto de campos preservados. Caliza+pH admitido, condicionado; sin composición,
desconocido. No veto universal ni descalcificación inferida. Aereus máximo 6,8.
67 pruebas dirigidas, 369 de regresión (12 omitidas), Chrome escritorio/móvil,
nueve puntos con enero/septiembre y API real de preview en La Vansa correctos.
Preview recargada en 65517 con configuración y autenticación ficticia conservadas.
Sin runners, entrenamiento, precálculo, builds HA ni cambios en workers.
[Informe](../reports/prediction-map-two-levels-2026-09-14.json).
Pendiente: contraste científico, resto de fichas, criterio de árboles vecinos;
posteriormente portabilidad y paridad/aceptación local HA–worker.

## Estado histórico tras motor y corrección forestal — 13/09/2026

Motor real conectado en preview y ejecutor Python común. Compatibles por
probabilidad descendente del día; sin cálculo al final. Rovelló por ID/ficha,
sin grupo derivado ni préstamo de modelos: última decisión del usuario.
Geometría candidata MFE inválida reparada en memoria con área conservada;
los tres puntos de Fogars/Arbúcies recuperan árboles, sin modificar fuentes.
Edulis en Fogars 41.77528, 2.46480 compatible con haya y 33,3862 % el 13/09.
Pruebas dirigidas de motor/contrato/continuidad, regresión del Predictor, Chrome
y 12 forestales correctas. Sin HA/worker desplegados ni entrenamiento/precálculo.
Siguiente: validar setales, portabilidad/aceptación local HA–worker y comparación
entre ejecutores. [Informe](../reports/prediction-map-engine-integration-2026-09-13.json).

## Estado histórico tras mappings y Terreno — 13/09/2026

787 códigos ICGC con 77 combinaciones en mappings locales; revisión, backup y
pendientes explícitos. Catálogo/fichas/observaciones intactos. Mezclas con varios
materiales y posibles suelos; datos editables, sin equivalencias en Python.
Terreno une la presentación de árboles/hábitats; el usuario admite fichas de
prado/ribera sin árboles. Hosts concretos y abstención por falta de contexto
preservados. Huellas de catálogo coherentes entre lectores.
74 pruebas Python y Chrome correctos; cuatro puntos reales y POST de preview.
[Informe](../reports/prediction-map-mappings-2026-09-13.json).
Siguiente paso: Rovelló derivado → motor compartido → comparación posterior.
No jobs, descargas, entrenamiento, precálculo o publicación HA.

## Estado histórico al relevo inicial del 13/09/2026

Fichas locales con ventanas amplias y campos pH mantenibles; límites pH vacíos
en las 21 fichas. Filtro residente de hospedadores/meses/altitud y pH opcional
conectado a preview. Sin hospedadores identificados, ninguna candidata; padre
de género ↔ especie admitido, especies hermanas no equivalentes. Lista de
candidatas por día con «Predicción pendiente», sin curvas de ejemplo en esa rama.
42 pruebas Python dirigidas y navegador real completados en ese incremento.

Relevo solicitado por el usuario:
[prediction-map-handoff-before-compaction-2026-09-13.md](../reports/prediction-map-handoff-before-compaction-2026-09-13.md).
Incluye comando actual de preview, datos locales, restricciones y evidencia.
Pendientes: mappings nuevos de hábitat/suelo/litología, agrupación derivada Rovelló,
motor compartido local y después comparación con worker. No repetir descargas,
revisión bibliográfica completa o migración de fichas ya aplicada. No lanzar
trabajos ni publicar HA. Los apartados siguientes son evolución histórica.

## Inicio técnico local del 12/09/2026

El usuario autoriza documentar y comenzar el trabajo técnico. Primer prototipo
de la ruta `/protected/prediction-map/index.html`: misma plantilla/núcleo
MapLibre sin modificar sus archivos, diana bajo IDW, modal cancelable y popup
anclado con siete fechas y tres especies de ejemplo. Los datos están marcados
como simulados; terreno y meteorología todavía sin conectar. Se conservan clic
y hover meteorológicos en estaciones. Acceso administrativo en UI/API.

Veintitrés pruebas Python dirigidas y prueba Chrome aislada de escritorio/móvil superadas.
Código, contrato, tamaños y alcance de validación se mantienen en la
[especificación central, §5.1 y §9.1](prediction-map-specification-es.md#51-primera-entrega-técnica-local-visor-y-contrato-de-demostración).
No hay jobs geográficos, migración de lectores, reconstrucciones ni despliegues.
La conexión al worker y la validez científica siguen pendientes.

Ampliación del 12/09: municipio opcional con lector local residente e índice
R-tree, conectado a la vista previa; cinco pruebas geométricas y regresión de
navegador correctas. Capa IGN nacional preparada, sin instalar en HA/worker.
Por decisión del usuario, municipio francés aplazado y rendimiento inicial
mejorable aceptado para priorizar el mapa. Ver §4.5 de la especificación central.

Revisión posterior de capas francesas: DEM, retención SoilGrids y pH presentes
y legibles en cinco puntos de Font-Romeu/Quérigut y sus tres microáreas; faltan
vegetación/geología francesas preparadas. Alcance puntual, procedencia y límites
en §6 central. No se repitieron descargas/auditoría nacional ni se lanzaron jobs.

Continuación: altitud y pH reales conectados a Terreno en la vista previa.
Índice candidato 712.704 bytes, lector residente por ventanas y adaptador común
con municipio opcional. Siete pruebas nuevas del lector y regresión de contrato,
traducciones y navegador correctas. Medidas y alcance en §6 central e informe
`docs/reports/prediction-map-terrain-preview-2026-09-12.json`. Vegetación/ecología
francesas aplazadas explícitamente; curvas simuladas, sin cambios al Predictor.

Continuación aceptado el terreno: meteorología observada real en el mismo popup.
Lluvia, temperatura/humedad mínimas y máximas y viento de una estación identificada
si hay datos. Selector 7/15/30/60 días sin nuevas peticiones; histórico particionado
local leído mediante adaptador residente, sin escrituras ni reconstrucciones.
32 pruebas dirigidas y navegador escritorio/móvil correctos. Medidas y límites
en §8 central y `docs/reports/prediction-map-weather-preview-2026-09-12.json`.
Pendiente conectar consultas geográficas al worker y validar inferencia; las
curvas por especies continúan simuladas.

Nueva decisión y entrega: selector **Servidor local / Worker** en el grupo
**Predicción** del visor, con persistencia por usuario/navegador y tiempos en
el popup (persistencia inicial sustituida después por ajustes del dispositivo,
igual que los demás parámetros; ver §5 central). La vista previa mantiene sesión
ficticia y ajustes temporales aislados, sin autenticar ni registrar usuarios en HA.
Canal de informes pequeños implementado en coordinador/worker,
activación opcional mediante configuración de lectores; sin modificar destinos.
73 pruebas dirigidas correctas; tras acotar el ciclo del lector y la validación
de resultados, repetidas las 18 pruebas del broker/contrato/rutas correspondientes.
Navegador con pestañas, persistencia, local, remoto asíncrono y cancelación correcto.
La vista previa mantiene local real y worker indisponible; faltan construcción,
configuración y aceptación del circuito en contenedores antes de anunciarlo
operativo. No se ha instalado ni reiniciado HA o el worker existente. Ver §5 central.

## Revisión anterior del plan (antes de iniciar el prototipo)

Diseño acordado el 12/09/2026 antes de implementar: interacción inicial concretada por el usuario:
botón en las opciones de la derecha para entrar en modo predicción y toque/clic
en un punto para ver predicción por especies de esa zona. Recorrido acordado,
prototipo y contratos pendientes; detalle en la
[especificación central](prediction-map-specification-es.md#4-experiencia-de-consulta-e-informe).
Contenido inspirado en Sporas revisado en la misma fecha: matriz de datos y
propuesta documentadas, sin prototipo. Por aclaración del usuario se presenta
en popup anclado al punto, con flecha/estilo actuales de Rainmapper; se descarta
la propuesta de panel lateral. Hasta siete días; sin previsión
meteorológica futura. Modal «Calculando predicción…» desde el clic hasta recibir
resultado; luego popup anclado. Cancelación y errores previstos, sin recarga.
Viento opcional según disponibilidad. Reutilizar el visor MapLibre
actual en la ruta nueva, sin modificar su comportamiento en la ruta existente.
Última revisión de interacción: clic y hover sobre estaciones conservan los
popups meteorológicos, incluso en modo predicción. Solo el clic fuera de
estaciones inicia el modal y la consulta predictiva. Acceso inicial administrador.

Revisión del 11/09/2026 posterior al diseño del lector y al reparto HA–worker.
**Los datos están preparados para desarrollar; su integración sigue pendiente.**
No hay todavía nuevo mapa funcional ni incorporación del pH SoilGrids al
Predictor por estas tareas. La comparación se basa en código y documentos
actuales; no revalida la versión ejecutada en HA real.

| Elemento del plan anterior | Situación al revisar | Decisión o trabajo restante |
|---|---|---|
| Adquirir cartografía y ampliar SoilGrids | Fuentes recibidas; retención nacional y nueve capas pH descargadas, cobertura auditada y huecos aceptados. | No repetir adquisición ni auditoría. Preparar formatos/índices operativos. |
| Base SoilGrids común para Predictor y mapa | Alcance cerrado; lector eficiente diseñado, todavía sin código. | Implementar índice y ventanas manteniendo la vista de retención compatible. |
| Migrar la aplicación actual | No se cambiaron lectores, referencias ni contextos por este trabajo. | Pruebas de equivalencia, edición y recursos; migración posterior controlada. |
| Ubicación de mapas y cálculo | Reparto concretado tras la aclaración del usuario. | Réplicas locales en workers; lotes, preparación y mapa a demanda allí; HA para ediciones pequeñas y coordinación. Implementación pendiente. |
| pH y nuevos atributos en la aplicación actual | El plan anterior conservaba retención para el Predictor y proponía pH para el mapa; no concretaba una fase de enriquecimiento de Setales/observaciones. | Añadir explícitamente esa fase descriptiva como propuesta, separada de cualquier cambio de modelos. |
| Nuevo informe por coordenadas | Diseño de producto disponible; sin contrato geográfico integrado ni interfaz nueva. | Consulta de terreno en worker, reglas ecológicas, meteorología y panel por punto. |
| Visor del nuevo mapa | Revisado el MapLibre meteorológico; acordados un único visor y dos rutas iniciales, todavía sin implementar. | Misma plantilla y núcleo; meteorología actual con predicción deshabilitada y ruta nueva con módulo opcional según permisos. Selección/panel asíncrono conectado al worker. |
| Predicción geográfica | Propuesta inicial a siete días; sin validación de transferencia a puntos nuevos. | Constructor de entradas y evaluación por lugares separados antes de activar porcentajes. Sin malla precalculada nacional. |

El plan anterior sigue siendo válido en objetivo, fuentes y separación entre
informe de terreno y predicción. Se actualizan tareas que quedaron obsoletas
(descargar pH, proponer lector) y se hace explícita la distribución a workers.
La cobertura meteorológica y las reglas de especies siguen pendientes; disponer
de mapas no resuelve esos dos requisitos.

### Qué aportan los mapas nuevos a la aplicación actual

Hay que distinguir tres cambios con validaciones distintas:

1. **Migración técnica compatible.** El Predictor obtiene la misma retención de
   agua y conserva sus valores/contextos. Mejoran acceso y preparación remota;
   no se cambian porcentajes ni variables por sustituir el almacenamiento.
2. **Enriquecimiento descriptivo, propuesto y pendiente.** Reutilizar el futuro
   servicio de terreno en Setales y vistas de observaciones para consultar pH,
   cubierta, árboles, geología y relieve adicionales con fuente, edición,
   resolución y ausencias. No exige esperar a validar un modelo geográfico.
   Definir primero su contrato de persistencia, UI y agregación por polígono;
   no guardar como pH de toda la microárea el píxel del centroide sin explicarlo.
   Mantener profundidades e incertidumbre, sin inventar una media de pH ni un
   umbral ecológico. Conservar aparte observaciones de campo y datos derivados;
   no reemplazar automáticamente anotaciones o correspondencias aceptadas.
3. **Uso predictivo de información nueva, no implementado ni validado.** Si se
   decide usar pH u otros atributos para entrenar o modificar compatibilidades
   operativas, versionar features/reglas, reconstruir entradas con procedencia
   consistente y comparar modelos en worker. Tener un campo en la ficha no
   demuestra que el modelo lo use ni autoriza multiplicar su probabilidad.

Evidencia de código actual:

- `rainmapper_core/mushroom_soilgrids.py:49`: el lector enumera solo
  `wv0010`, `wv0033`, `wv1500`; no incorpora `phh2o`.
- `rainmapper-app/app/mushroom_catalogs_ui.py:560` y `web_server.py:11607`:
  existen `ph_min`/`ph_max` editables en **tipos de suelo**. Son rangos del
  catálogo, no una estimación geográfica leída de SoilGrids.
- `mushroom-data/mushroom_reference_catalogs.json:1100`: esas categorías tienen
  rangos que pueden solaparse; no constituyen una conversión automática única
  de pH a categoría de suelo.
- `rainmapper_core/mushroom_gis_lab.py:109`: las capas vectoriales vigentes son
  MVC50 y geología ICGC; las descargas nacionales no se seleccionan allí.
- `rainmapper_core/mushroom_observation_features.py:193`: se combinan atributos
  observados y GIS, entre ellos `soil_tendency_ids`; ese camino no calcula el
  pH numérico de los nuevos mapas.

### Orden de trabajo consolidado

La secuencia general vigente está en las
[fases de la especificación central](prediction-map-specification-es.md#10-secuencia-de-implementación).
La lista de abajo detalla dependencias técnicas; el prototipo de visor y los
estudios meteorológicos/ecológicos pueden avanzar en paralelo según esas fases.

El **visor es una fase explícita**, no un detalle que se deja para el final.
La [arquitectura MapLibre y entrega de resultados](mushroom-map-compute-data-placement-es.md#visor-maplibre-y-entrega-de-resultados-al-navegador)
establece un solo visor y código compartido, con dos rutas iniciales. La nueva
añade la función predictiva, autorizada por usuario y con interruptor; la actual
la mantiene deshabilitada. En el futuro podrá habilitarse en la ruta actual sin
reescribir el mapa. HA sirve la vista, MapLibre dibuja en navegador y el worker
calcula el punto. Primero puede prototiparse con una respuesta simulada
identificada, en paralelo a los lectores; después conectar terreno real e
inferencia validada. Primera propuesta: marcador/panel por clic. Una superficie
coloreada de probabilidades requiere un diseño posterior de lotes/teselas
acotados y no se obtiene del resultado de un único punto.

1. Implementar y validar lectores/índices y publicación de datasets compartidos;
   primero SoilGrids compatible, después adaptar DEM y vectores según sus formatos.
2. Preparar réplica del worker y preparación remota de contextos antes del
   snapshot. Probar conjuntamente edición pequeña HA y lotes remotos, sin
   trasladar carga pesada a la RPi4.
3. Migrar el acceso de la aplicación actual tras equivalencia y aceptación local;
   conservar datos, contratos y caché antigua. No activar a la vez nuevas
   variables científicas que impidan atribuir una diferencia a la migración.
4. Concretar e integrar el enriquecimiento descriptivo propuesto de la aplicación
   actual y el informe de terreno del nuevo mapa sobre el mismo servicio.
5. Completar estudio meteorológico y reglas ecológicas; pueden avanzar en
   paralelo al lector, sin reabrir la auditoría SoilGrids.
6. Implementar/evaluar predicción geográfica en worker, primero Catalunya y
   siete días. Ampliar territorio según cobertura de datos y evidencia del modelo,
   no simplemente por tener descargada España.

El [diseño del lector](mushroom-prediction-map-soilgrids-reader-design-es.md) y el
[reparto de consumidores](mushroom-map-compute-data-placement-es.md) detallan las
pruebas, recursos y puertas locales. Son planes: no han ejecutado estas fases.

## Punto en el que estamos

La adquisición de altitud IGN, MFE de las 17 comunidades, cubiertas ICGC 2024 y
las dos capas GEODE está documentada en el
[inventario de descargas](mushroom-map-gis-downloads-es.md).

**Paso 1 terminado en preparación de datos: geología ICGC disponible y comprobada.**
Se ha reutilizado y verificado el paquete local existente, conservando una copia
identificada en `mushroom-map-GIS/icgc-geologia-50000/source/`.
La capa contiene 61.437 polígonos e índice espacial. Responde correctamente en
16 controles catalanes y devuelve ausencia de cobertura en tres controles
exteriores. Nueve consultas de contraste a GEODE no devuelven geología en puntos
catalanes; Madrid y Valencia sirven de controles positivos de ese servicio.

[Evidencia de este paso](../reports/mushroom-prediction-map-geology-icgc-2026-09-11.json)
y [README junto a los archivos](../../mushroom-map-GIS/icgc-geologia-50000/source/README.md).
No se modifica el servicio GIS operativo ni se despliega una integración en HA.

## Secuencia de trabajo

| Paso | Estado | Resultado que debe quedar |
|---|---|---|
| Visor e interacción | Arquitectura propuesta; prototipo pendiente, puede avanzar junto a lectores | Reutilización MapLibre, clic, panel, estados/cancelación, autenticación y entrega asíncrona del worker. HA no calcula la predicción. |
| 1. Geología de Catalánides | Preparación terminada | Fuente ICGC identificada, íntegra y consultada localmente; controles frente al hueco GEODE y límites documentados. |
| 2. SoilGrids compartido | Descarga y cobertura comprobadas; diseño del lector documentado | Cobertura española utilizable 97,5675 %, huecos aceptados; implementación, mediciones y migración pendientes. |
| 3. Cobertura meteorológica | Pendiente | Saber en qué puntos tenemos estaciones y una historia suficiente para el modelo, empezando por Catalunya. |
| 4. Preparación de mapas | Pendiente | Normalizar CRS/campos/ediciones, índices para consultar por punto y tratamiento de límites, mosaicos y datos ausentes. |
| 5. Ecología por especie | Pendiente | Reglas trazables de árboles, hábitat, suelo y temporada a partir de las 21 revisiones. |
| 6. Informe del terreno | Pendiente | Prueba separada que explique qué hay en un punto, con fuentes y calidad. |
| 7. Predicción geográfica | Pendiente | Prueba aislada a siete días, selección por especie y evaluación en lugares separados del entrenamiento. |

La adquisición y auditoría de cobertura del paso 2 están terminadas. El usuario
acepta los huecos y no pide rellenarlos. El
[diseño del lector para RPi4](mushroom-prediction-map-soilgrids-reader-design-es.md)
concreta índice SQLite, ventanas, caché limitada, altas/cambios, autocura y
pruebas de compatibilidad y recursos. Es una propuesta documentada, todavía
sin implementación ni mediciones. Quedan normalización y migración controlada.
El [reparto de datos y cálculo HA–worker](mushroom-map-compute-data-placement-es.md)
precisa que el worker necesita copias locales de todos los mapas de su función
y ámbito para preparación, entrenamiento/precálculo y consultas del nuevo mapa.
HA conserva ediciones pequeñas y coordinación. La autocura pesada previa al
snapshot también debe delegarse; no precalcular todos los puntos de España.
No se inicia automáticamente el resto.
La adquisición de mapas no equivale a tener una
predicción validada. El salto a 15 días con previsiones meteorológicas queda
como ampliación posterior.

## Alcance de las comprobaciones

Los controles puntuales prueban que las consultas funcionan en esos lugares;
no certifican por sí solos ausencia de huecos en todo el territorio. La geología
describe rocas/unidades y no proporciona directamente pH del suelo ni presencia
de setas. Los resultados conservarán la fuente y la escala de origen.

## Funcionamiento local y estabilidad de las fuentes

Por indicación expresa del usuario, la geología del Mapa de predicción se
consultará en archivos locales, sin depender del formato o disponibilidad futura
de servidores ICGC/IGME. Las consultas online de este paso fueron diagnósticas.
Los 19 controles del ICGC se ejecutaron contra el GeoPackage local.

Se documenta la preferencia por ICGC donde sus polígonos cubran el punto en
Catalunya; GEODE local en los demás casos. Sin datos en ambas fuentes se devuelve
«sin cobertura», sin buscar el polígono más próximo ni recurrir silenciosamente
a un servicio online. No se fusionan códigos de leyendas distintas.

ICGC ya incluye índice de consulta. GEODE está descargado como bloques JSON
comprimidos: **queda preparar su almacenamiento e índice espacial local** en el
paso 4, sin necesidad de volver a descargar los polígonos. La aplicación nueva
todavía no está implementada. La [política de fuentes](../../mushroom-map-GIS/geology-source-policy.json)
registra esta distinción y el tratamiento de puntos en límites.

Cualquier nueva edición se descargará por separado, se comprobará y se adoptará
deliberadamente. No sustituirá automáticamente los datos en uso. Se conservan
originales, huellas, leyendas y metadatos para mantener consultas reproducibles.

## Paso 2: propuesta de una única base SoilGrids para ambas herramientas

El usuario plantea cubrir todo el territorio y evitar dos descargas independientes.
Se propone una base local común, con inventario por propiedad, profundidad,
estimación/incertidumbre y edición. El Predictor leería sus capas de retención;
el Mapa de predicción utilizaría además las propiedades ecológicas necesarias.
Los mismos archivos no se duplicarían por consumidor. La residencia y distribución
del catálogo se definirán para evitar cargar la base nacional completa en HA.

### Evidencia comprobada el 11/09/2026

- `mushroom-GIS/soilgrids/manifest.json`: 54 combinaciones de tres propiedades de
  retención, seis profundidades y tres estimaciones; 30 identificadores de tesela
  distintos, 1.355 entradas válidas. No es cobertura española completa.
- Los 1.410 archivos distintos referenciados por el manifiesto existen y suman
  394.292.523 bytes (originales y normalizados; no se han repetido sus hashes
  en esta comprobación). No incluyen pH, arena, arcilla, limo ni carbono orgánico.
- `rainmapper_core/mushroom_soilgrids.py`, `required_coverage_ids` y
  `validate_manifest`: el lector exige actualmente el conjunto exacto de capas
  de retención. No basta con añadir propiedades al manifiesto operativo.
- `default_cache_root` permite configurar la raíz, pero eso por sí solo no
  adapta el contrato de lectura ni los montajes/distribución.
- La [documentación ISRIC de acceso](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_02.html)
  describe descarga de recortes por WCS y mapas mediante WebDAV.
  La [lista de propiedades](https://docs.isric.org/globaldata/soilgrids/SoilGrids_faqs_01.html)
  incluye pH, textura, carbono orgánico y retención, con profundidades y medidas
  de incertidumbre. Consultar disponibilidad concreta por capa antes de adquirir.

### Secuencia acordada y avance

Los puntos 1–3 están completados. Del punto 5 se han comprobado cobertura y
conservación de archivos/contextos; falta validar el lector nuevo y sus
resultados. El punto 4 y la migración/retirada del punto 6 siguen pendientes.

1. Definir el territorio como España (Península, Baleares, Canarias, Ceuta y
   Melilla), conservando también las zonas ya utilizadas fuera de ese ámbito.
   Calcular las teselas necesarias y contrastarlas con las existentes.
2. Conservar las capas/profundidades/estimaciones de retención que necesita el
   Predictor. Añadir únicamente pH superficial con incertidumbre para el mapa.
   Textura, carbono y materia orgánica quedan fuera del alcance inicial por no
   haberse demostrado una necesidad concreta. No añadir precisión aparente al
   suelo para compensar la incertidumbre meteorológica.
3. Medir tamaño y número de archivos de la ampliación antes de iniciarla.
   Reutilizar archivos compatibles por edición, cuadrícula, unidades y huellas;
   descargar únicamente lo que falta. Las zonas sin estimación se conservarán
   como tales: cobertura territorial de adquisición no garantiza dato en cada píxel.
4. Preparar un catálogo común y lectores compatibles, manteniendo estable la
   vista de retención del Predictor. No sustituir silenciosamente valores o
   resolución por una nueva edición. Servir ambas herramientas desde esa base
   local, sin consultas online obligatorias por punto.
5. Contrastar cobertura, valores y contextos en los lugares actuales; verificar
   que la ampliación no cambia resultados del Predictor cuando las entradas
   se conservan. Validar el cambio operativo en local antes de una migración.
6. Tras validar la migración y cambiar controladamente los lectores, retirar las
   referencias antiguas conservando backup temporal. Propuesta: al menos 30 días
   y comprobación satisfactoria de creación/edición de microáreas antes de revisar
   su retirada definitiva. No se ejecuta ningún borrado en este paso.

El [plan y dimensionado](mushroom-prediction-map-soilgrids-plan-es.md) concretan
3,73 GB de píxeles sin comprimir para retención + pH, frente a 5,87 GB de la
propuesta inicial con textura/carbono; presupuesto de trabajo propuesto 12 GiB
incluyendo margen para originales, staging y rollback. No es una medida del
tráfico ni de la compresión final. Las 63 capas aparecen en los metadatos WCS.
Descarga nacional autorizada y terminada en la misma raíz de GIS/DEM:
`mushroom-map-GIS/soilgrids-shared/source/`. Los 1.410 archivos previos se han
copiado verificando hashes. Los 538 bloques nuevos pasan lectura GDAL completa,
cuadrícula y SHA-256; las referencias cubren 7.119 pares tesela/capa, sin `.part`.
Total rásteres: 795.522.040 bytes, incluidos 401.229.517 bytes nuevos comprimidos.
[Informe de adquisición](../reports/mushroom-prediction-map-soilgrids-acquisition-2026-09-11.json).
La integridad de los originales no demuestra dato válido en cada píxel:
normalización de CRS/NoData, identidad de ediciones y lectores pendientes; la
auditoría de cobertura y máscara posterior está enlazada abajo. No se
modifica el lector operativo ni se retiran sus archivos.

El diseño distingue terreno consultado según la cartografía de origen y
meteorología estimada para el entorno. El tamaño de las zonas meteorológicas
queda pendiente de auditar la red de estaciones. No se promete precisión de
predicción a escala de metros ni se ha confirmado el tamaño de teselas de Sporas.

### Cobertura aceptada y siguiente condición

[Auditoría de cobertura y lecturas en RPi4](mushroom-prediction-map-soilgrids-coverage-es.md):
97,5675 % de celdas españolas con valores utilizables en todas las capas;
Catalunya 95,4419 %. Límites GISCO aproximados y cuadrícula de 250 m. Ninguna
microárea actual pierde datos; 1.355 archivos normalizados iguales en ambas
raíces y 66 contextos con geometría/referencias coincidentes. No hay migración.

El mayor archivo de suelo ocupa 4,14 MB; los 796 MB son el total. Todos tienen
bloques internos 256×256. Antes de integrar, resolver por índice y leer ventanas
sin repetir hashes completos ni abrir un proceso por capa y clic. La auditoría
nacional no se ejecutará como parte de las consultas en la RPi4. No se han
medido aún latencia ni memoria reales allí.
