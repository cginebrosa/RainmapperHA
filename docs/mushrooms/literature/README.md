# Biblioteca local de literatura del predictor de setas

Esta carpeta guarda el material documental usado para disenar y revisar el futuro motor de prediccion de floradas.

Regla critica: un parametro del motor predictivo, un umbral por especie o un peso entre variables no puede fijarse por intuicion de Codex. Debe estar respaldado por una fuente documental verificable o por observaciones locales trazables en Rainmapper. Si la fuente solo permite una deduccion general, la documentacion debe decirlo explicitamente y no convertirla en valor numerico.

## Politica de copia local

- Guardar aqui solo PDFs o documentos que sean realmente articulos, versiones aceptadas, preprints o documentos publicos utiles.
- No guardar paginas de bloqueo, login, challenge anti-bot, paywall o landings genericas como si fueran papers.
- Si un articulo esta identificado como open access pero el servidor bloquea la descarga automatica desde terminal, registrar la URL y el bloqueo en la tabla.
- Si un articulo no es open access o no hay copia publica verificable, conservar DOI/enlace y marcarlo como `DOI-only`.
- Si el usuario descarga manualmente un PDF publico desde navegador, anadirlo aqui con un nombre estable y actualizar esta tabla.
- Los PDFs escaneados o fotografiados de libros/guias suministrados por el usuario se tratan como fuentes locales no versionadas si no son documentos publicos redistribuibles. Versionar el resumen derivado y documentar la ruta local esperada, no el binario.

## Estado de fuentes

| Fuente | DOI / URL | Estado local | Uso previsto |
| --- | --- | --- | --- |
| Kauserud et al. 2012, *Warming-induced shift in European mushroom fruiting phenology* | https://doi.org/10.1073/pnas.1200789109 | OA detectado por OpenAlex, pero descarga automatica bloqueada por Cloudflare/403 desde terminal. No hay PDF local. | Fenologia europea, temperatura y desplazamiento temporal de fructificacion. |
| Andrew et al. 2018, *Explaining European fungal fruiting phenology with climate variability* | https://doi.org/10.1002/ecy.2237 | OA detectado por OpenAlex, pero descarga automatica del PDF Wiley bloqueada por 403 desde terminal. No hay PDF local. | Fenologia fungica y variabilidad climatica. |
| Taye et al. 2016, *Meteorological conditions and site characteristics driving edible mushroom production in Pinus pinaster forests of Central Spain* | https://doi.org/10.1016/j.funeco.2016.05.008 / http://hdl.handle.net/10459.1/58592 | OA detectado por OpenAlex via repositorio UdL, pero el repositorio devuelve challenge Anubis desde terminal. No hay PDF local. | Meteorologia y caracteristicas de sitio en produccion de setas comestibles. |
| Nepote Valentin et al. 2023, *Modeling geographic distribution of arbuscular mycorrhizal fungi...* | https://doi.org/10.7717/peerj.14651 | OA detectado, pero PeerJ devuelve challenge Cloudflare desde terminal. No hay PDF local. | Justificacion de modelos de distribucion con clima, suelo, vegetacion y elevacion. |
| Marc Estevez, fichas divulgativas de especies fotografiadas/escaneadas por el usuario | `Marc_EstevezSpecies.pdf` | PDF local suministrado por el usuario y no versionado por tratarse de un escaneo local. No tenia texto seleccionable util; OCR local con Tesseract no fue fiable. Conclusiones extraidas por revision visual y resumidas en `marc-estevez-species-conclusions-es.md`, que si queda versionado. | Seed literario v0 en castellano para especies, usando senales amplias de habitat, vegetacion/host, suelo, altitud, temporada y meteorologia cualitativa. |
| Bonet et al. 2008, *Empirical models for predicting the production of wild mushrooms in Scots pine forests in the Central Pyrenees* | https://doi.org/10.1051/forest:2007089 | No OA en OpenAlex. La landing de Annals of Forest Science es accesible, pero no se ha verificado PDF publico descargable. DOI-only. | Modelos empiricos en pinares del Pirineo central. |
| Bonet et al. 2004, *The relationship between forest age and aspect on the production of sporocarps...* | https://doi.org/10.1016/j.foreco.2004.07.063 | No OA en OpenAlex. DOI-only. | Edad/orientacion del bosque y produccion de esporocarpos. |
| Bonet et al. 2010, *Modelling the production and species richness of wild mushrooms in pine forests...* | https://doi.org/10.1139/X09-198 | No OA en OpenAlex. DOI-only. | Produccion y riqueza de especies en pinares del Pirineo central. |
| Martinez-Pena et al. 2012, *Yield models for ectomycorrhizal mushrooms...* | https://doi.org/10.1016/j.foreco.2012.06.034 | No OA en OpenAlex. DOI-only. | Modelos de rendimiento para *Boletus edulis* y grupo *Lactarius deliciosus*. |
| Buentgen et al. 2015, *Drought-induced changes in the phenology, productivity and diversity of Spanish fungi* | https://doi.org/10.1016/j.funeco.2015.03.008 | No OA en OpenAlex. DOI-only. | Sequía, productividad y fenologia en hongos de Espana. |
| Krebs et al. 2008, *Mushroom crops in relation to weather in the southwestern Yukon* | https://doi.org/10.1139/b08-094 | No OA en OpenAlex. DOI-only. | Ejemplo de relacion entre clima, memoria hidrica y cosechas de setas. |
| CABI, *Cantharellus cibarius (golden chanterelle)* | https://doi.org/10.1079/cabicompendium.33373661 | No OA en OpenAlex. DOI-only. | Ficha monografica para revisar *Cantharellus cibarius* sensu lato. |

## Uso en Rainmapper

La biblioteca no es una tabla de parametros. Sirve para:

- justificar familias de variables candidatas;
- revisar perfiles de especie;
- decidir que evidencias faltan antes de crear nuevos umbrales;
- documentar que parte del modelo es literatura, que parte es heuristica y que parte sera calibracion local.

Antes de implementar el motor de prediccion, revisar esta carpeta y el documento `../mushroom-predictor-design-es.md`.
