# Inventario completo de GIS Mappings

La pantalla de mantenimiento incluye los valores de las capas publicadas aunque
ninguna observación reconstruida los haya encontrado todavía. La presencia de
un valor en este inventario no equivale a una clasificación científica aceptada.

Inventario extraído el 16 de septiembre de 2026, exclusivamente de atributos:

| Producto | Campo | Valores distintos no vacíos |
| --- | --- | ---: |
| Geología ICGC 1:50.000, 2024-12 | Codi | 1055 |
| MVC50, noviembre de 2019 | LLFISCAT_t | 202 |
| MVC50, noviembre de 2019 | LLVA_niv2t | 62 |
| MVC50, noviembre de 2019 | LLVA_Subst | 13 |

Los valores originales y las descripciones geológicas se empaquetan en
`rainmapper_core/data/gis-value-inventory.json` (aproximadamente 120 kB). Este fichero
no contiene equivalencias con suelos, árboles ni especies. Las decisiones
editables siguen exclusivamente en `mushroom_gis_mappings.json`.

## Preparación y recursos

El inventario se prepara en el equipo de desarrollo cuando cambia una edición;
no se recorre ni se calcula el hash de los GIS al abrir la pantalla en HA:

```sh
.venv/bin/python scripts/build-gis-value-inventory.py \
  --geology mushroom-map-GIS/icgc-geologia-50000/source/geologia-territorial-50000-geologic-v3r0-202412.gpkg \
  --mvc50 docker-media/rainmapper/geography/mushroom-GIS/MVC50mil/extracted/MVC50mil_novembre2019.shp \
  --ogrinfo /opt/homebrew/bin/ogrinfo \
  --output rainmapper_core/data/gis-value-inventory.json
```

El generador está vinculado a estas ediciones: al incorporar otra edición hay
que actualizar sus identificadores y verificar sus fuentes. No basta con
cambiar el nombre de un fichero. La pantalla pagina de 100 en 100 y conserva
los filtros y la búsqueda. El inventario se carga una vez por proceso y no
forma parte de los trabajos ni de los mensajes del heartbeat.

## Revisión y guardado

- Los valores sin decisión aparecen pendientes y no se aceptan por existir.
- Las decisiones existentes conservan su estado y sus destinos.
- Las reglas agrupadas se muestran por código, con la edición efectiva.
- Al editar un código de un grupo, se separa únicamente ese código; sus
  vecinos, otras ediciones y metadatos conservados no cambian.
- Desmarcar un destino lo elimina del código editado.
- Para aceptar una regla con edición, el formulario exige una referencia.
  La existencia de una referencia no demuestra por sí sola su validez científica.
- El identificador se mantiene como `geology_50000`, tanto para el mapa como
  para reconstrucción y mantenimiento. MVC50 conserva `mvc50`.
- La edición `2024-12` sigue diferenciando las reglas de otras ediciones.
  Las decisiones sin edición se conservan como antecedentes; una decisión
  de la edición vigente, incluso pendiente, tiene prioridad.
- El lector de reconstrucción admite reglas individuales y agrupadas. Conserva
  la salida `layers.geology_50000` que ya consumen las fichas existentes.
- Las reglas del mapa que utilizaban `icgc_geologia_50000` se preparan con el
  nombre común en el JSON local, con copia previa. No se renombran GeoPackages,
  carpetas geográficas, modelos ni artefactos de precálculo.

La corrección de cobertura debe distinguirse de la revisión de las decisiones.
El registro local `gis-mapping-reviews/full-gis-review-2026-09-16.json` recoge
por separado la descripción original, los destinos, las fuentes y los límites
de cada decisión. No forma parte del payload operativo del worker.

## Revisión documental local, 16 de septiembre de 2026

| Fuente | Decisiones aceptadas | Pendientes |
| --- | ---: | ---: |
| Geología | 1038 | 17 |
| MVC50 | 236 | 41 |

Los cuatro mappings anteriores de cubiertas ICGC se conservan: el total del
mantenimiento es 1336 valores, 1278 aceptados y 58 pendientes. Aceptado significa
que se justifican **los destinos indicados**, no todas las propiedades del suelo.
De los 1038 códigos geológicos aceptados, 567 incluyen un componente parental
silíceo, carbonatado o yesífero; 471 solamente identifican materiales. En estos
últimos no se ha confirmado una tendencia de suelo. Las reglas pendientes no
intervienen en el cálculo.

No se infiere textura arenosa/franca, pH, drenaje ni humus a partir del nombre
de una roca. Los carbonatos identificados son componentes del sustrato; no
demuestran que toda la superficie sea caliza, ni descartan descarbonatación.
El campo de sustrato MVC50 describe la preferencia de una comunidad vegetal,
no una medición del suelo del punto.

### Componentes mixtos, revisión local del 16 de septiembre

Se conservan ambas etiquetas cuando la unidad tiene componentes silíceos y
carbonatados documentados. Hay 21 códigos con ambos: los 14 ya existentes y
`PEcgb`, `PEcgb1`, `PEcgb3`, `PEcgb4`, `PEcgb6`, `PEcgc` y `PEcc`.
`PEcgb2` recibe únicamente el componente carbonatado confirmado; su parte
silícea no queda demostrada por la descripción disponible.

El registro vigente incluye `mixed_component_review`, con los cambios exactos,
fuentes, localizadores y casos a los que no se extrapola la composición. Las
memorias IGME 255 y 257 y las descripciones cartográficas de Cistella, Llers y
Sant Jaume de Llierca complementan la memoria 256. No se deduce textura ni pH.
Las dos etiquetas expresan componentes posibles de una unidad heterogénea,
no una mezcla uniforme en todo su suelo superficial.

Comprobaciones de esta revisión: 1336 correspondencias conservadas, solo ocho
códigos modificados, 24 casos con el lector ecológico (incluidos los 21 mixtos),
28 pruebas del filtro y nueve pruebas de los datos locales. En la consulta
autenticada a HA local, Ripoll (42.20452, 2.21053) devuelve las dos etiquetas.
Los informes actuales están en `tmp/gis-review-20260916/mixed-substrates/`.
Esta revisión de datos no constituye validación de una nueva release.

La admisión condicionada por un componente deja de aplicarse cuando también
hay un componente expresamente admitido por la especie. Las exclusiones, el pH,
los hospedadores y la altitud mantienen sus comprobaciones independientes.
Validación posterior: 38 pruebas dirigidas, HA local y worker reconstruidos con
el mismo fichero ecológico efectivo. En 42.20397, 2.21020, Local devuelve
`boletus_edulis` compatible, admisión estándar y sin `soil_ph_conditional`.
La consulta por worker devuelve `worker_busy`; esa ruta en vivo queda pendiente,
aunque el código instalado coincide. Evidencia en `admission-validation.json`.

Fuentes principales:

- [Leyenda y vocabulario ICGC](https://app.icgc.cat/web/es/mapageol_atles_vocabllegenda_v2.php)
  y los atributos originales de la edición 2024-12.
- [IGME, hoja 217](https://info.igme.es/cartografiadigital/datos/magna50/memorias/MMagna0217.pdf):
  Jújols y Bellver. `EÇOrgl` admite componente silíceo; para `Cagl`, la sección
  2.1.5 documenta areniscas cuarzo-feldespáticas entre lutitas y microconglomerados.
  Esa evidencia no se extiende automáticamente a todas las facies de Bellver.
- [IGME, hoja 293](https://info.igme.es/cartografiadigital/datos/magna50/memorias/MMagna0293.pdf):
  predominio de clastos calizos en el nivel de brechas de Berga, `POb`.
- [Metadatos MVC50, Universitat de Barcelona](https://hdl.handle.net/2445/147059):
  significado de los tres campos inventariados y de los sustratos preferentes.
- [BGS, clasificación metamórfica](https://nora.nerc.ac.uk/id/eprint/3226/1/RR99002.pdf)
  y [clasificación ígnea](https://nora.nerc.ac.uk/id/eprint/3223/1/RR99006.pdf):
  alcance de los nombres de roca y de los protolitos identificados. «Básico»
  en una roca ígnea no significa pH alcalino.
- [IGME, hoja 256](https://info.igme.es/cartografiadigital/datos/magna50/memorias/MMagna0256.pdf)
  y [Generalitat, itinerario de Ribes](https://parcsnaturals.gencat.cat/ca/xarxa-de-parcs/ter-freser/gaudeix-del-parc/equipaments-i-itineraris/itineraris-interpretatius-del-parc-natural/ribes-de-freser-pla-derola/):
  identificación del granófiro y de sus componentes cuarzo/feldespato.
- [IGME, hoja 332](https://info.igme.es/cartografiadigital/datos/magna50/memorias/MMagna0332.pdf):
  Vespella. `PEalb` acepta solo las areniscas y limos expresos; no recibe
  margas por compartir el nombre de la formación.
- [Esteve et al., Geogaceta 60, pp. 99–102](https://sge.usal.es/archivos/geogacetas/geo60/Geogaceta_60_completa.pdf):
  heterogeneidad de Susqueda. Se conservan las litologías acreditadas,
  sin convertir todo el cuerpo en un mismo suelo.

La revisión no equivale a consultar un estudio petrográfico independiente de
cada uno de los 1055 códigos. La descripción oficial es la evidencia primaria
para las correspondencias literales; las consultas adicionales se identifican
por código. No se han medido suelos superficiales. El registro separa expresamente
los materiales confirmados, el componente parental y las propiedades desconocidas.

Se retiran las antiguas sugerencias geológicas por fragmentos de texto y la regla
derivada que añadía pH ácido. Además de inferencias injustificadas, la búsqueda
de `gres` coincidía con `negres`. Un código geológico nuevo queda sin propuesta
automática hasta revisarlo. Las propuestas MVC50 tampoco se autoaceptan.
El catálogo de litologías deja de proporcionar pH o textura por defecto;
los destinos operativos proceden de las decisiones exactas aceptadas.

`mc_Capl` queda pendiente por discrepancia entre la descripción actual y el
protolito. `mc_Capg` conserva la identificación de pizarra, sin atribuirle una
composición del suelo no comprobada. Esto puede dejar especies con información
insuficiente; no constituye evidencia de ausencia biológica.

## Comprobaciones locales

Se comprobaron los 1332 valores revisados en ambos lectores, incluida la
inactividad de las reglas pendientes y el guardado de un código sin alterar
sus vecinos. Los códigos geológicos distinguen mayúsculas: `KSCm` y `KScm`
son identidades distintas. La normalización de textos MVC50 se conserva.

HA local y el worker se reconstruyeron y recrearon; las huellas de los cuatro
módulos implicados se contrastaron dentro de los contenedores. Se conservó
exactamente la configuración de coordinadores del worker. Pasaron 89 pruebas
dirigidas y 9 pruebas con los JSON locales. Consultas autenticadas de Alp,
Bellver y Santa Maria de Merlès devolvieron las mismas decisiones y probabilidades
en Local y Worker. Los dos puntos de Bellver se repitieron después de corregir
`Cagl`; ambos devuelven silíceo y probabilidades de Edulis y Pinícola.

Tras activar la revisión documental final y el catálogo corregido, se repitieron
cinco puntos por ambos ejecutores (diez consultas autenticadas): Alp, los dos
puntos de Bellver, Santa Maria de Merlès y el punto `DCc` de Bellver. Se compararon
geología, pH, destinos, admisiones y todas las probabilidades: coincidieron.
Ambos ejecutores usaron la revisión ecológica `d95212a621f5eb5ff461` y la revisión
de catálogo `10327fed759091c662dd`. Las dos especies observadas por el usuario
en 42.01290, 1.97120 siguen admitidas. También pasó la pantalla de mantenimiento
con 1278 aceptados, 58 pendientes y paginación de 100 valores.

El validador general informa 0 errores y 89 avisos de identificadores no usados.
Ese recuento no debe interpretarse como 89 clasificaciones incorrectas: entre
ellos hay IDs usados por las reglas agrupadas que ese validador no contabiliza.
La comprobación específica recorrió las 1332 decisiones expandidas, contrastó
todos sus IDs con el catálogo y verificó ambos lectores y los pendientes inactivos.

Esta validación no es una ejecución completa de reconstrucción, entrenamiento
y precálculo ni una autorización de release. No se ha modificado HA real.
Los resultados antiguos de reconstrucción y los modelos existentes no se
reescriben al editar el JSON. Antes de una release sigue siendo aplicable
el circuito local de aceptación descrito en `AGENTS.md`.

## Cierre de release 0.2.307 y límite de la revisión

Los apartados de validación anteriores registran etapas previas. La cadena local
posterior terminó reconstrucción, entrenamiento base, multiversión (714/714
ajustes) y recepción/activación del precálculo semanal. El informe de release
registra los trabajos y las verificaciones finales de código y navegador.

Después de esa cadena se revisó exclusivamente `KMga4`: el estudio de Poch et al.
(2019), DOI `10.5281/zenodo.3420951`, documenta cuarzo y cemento calcítico en la
Formación Areny. La decisión conserva arenisca y añade componentes silíceo y
carbonatado, sin atribuir textura o pH medidos al punto de Coll de Nargó.
La evidencia y sus límites figuran en `formations-2026-09-16.json`.
Ahora hay 22 códigos con ambos componentes; los 21 del apartado histórico
anterior más `KMga4`. La verificación proporcional comprobó ambos lectores
(1336 correspondencias, incluidos 1055 códigos geológicos) y la consulta local.
No se repitió entrenamiento/precálculo por esa última decisión de datos.

Se entregan siete JSON congelados para instalación por el usuario; las
investigaciones pendientes quedan en pausa por su instrucción. Aceptar una
litología literal no significa haber justificado todas sus propiedades de suelo:
471 códigos aceptados aún carecen de tendencia de suelo y 17 siguen pendientes.
[Informe de release](../reports/ha-release-0.2.307.json).
